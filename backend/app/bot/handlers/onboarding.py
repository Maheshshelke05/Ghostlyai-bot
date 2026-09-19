"""Onboarding FSM: language -> name -> phone -> district -> resume -> categories -> job types
(Chapter 6). Also used for /profile edit and /category edit re-entry."""
from __future__ import annotations

import html
import logging
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    categories_kb,
    confirm_kb,
    job_types_kb,
    language_kb,
    phone_kb,
    remove_kb,
    resume_kb,
)
from app.bot.states import Mode, Onboarding
from app.bot.texts import LANGUAGES, t
from app.config import settings
from app.db.models import Category, Profile, User
from app.services import ai, storage
from app.services.access import start_trial
from app.services.districts import canonical_district
from app.services.notifier import send_digest_to_user
from app.services.push import send_push_to_admins
from app.services.validators import normalize_name, normalize_phone, valid_name

logger = logging.getLogger("app.bot.onboarding")
router = Router(name="onboarding")

_RESUME_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_SUPPORTED_RESUME_MIMES = set(_RESUME_MIME_BY_EXT.values())


async def _active_categories(db: AsyncSession) -> list[Category]:
    rows = (
        await db.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        )
    ).scalars().all()
    return list(rows)


async def _categories_by_slug(db: AsyncSession) -> dict[str, Category]:
    return {c.slug: c for c in await _active_categories(db)}


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    payload = (message.text or "").split(maxsplit=1)
    # ref_xxxx deep-link payloads are accepted but not yet used (Phase 3 referrals).

    if user.status == "active" and user.category_links:
        lang = user.language or "mr"
        await state.clear()
        from app.services.access import status_line

        await message.answer(f"{status_line(user, lang)}\n\n{t(lang, 'help', support=_support_line(lang))}")
        return

    await state.clear()
    await state.set_state(Onboarding.language)
    await state.update_data(mode=Mode.ONBOARDING)
    await message.answer(t(user.language or "mr", "choose_language"), reply_markup=language_kb())


def _support_line(lang: str) -> str:
    if settings.SUPPORT_USERNAME:
        return t(lang, "support_line", username=settings.SUPPORT_USERNAME)
    return ""


@router.callback_query(F.data.startswith("lang:"))
async def on_language(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
) -> None:
    code = callback.data.split(":", 1)[1]
    if code not in LANGUAGES:
        await callback.answer()
        return
    user.language = code
    await db.flush()
    await callback.answer()

    data = await state.get_data()
    mode = data.get("mode", Mode.ONBOARDING)

    if mode == Mode.LANGUAGE_ONLY:
        profile_done = user.status == "active" and bool(user.category_links)
        await state.clear()
        text = t(code, "profile_done_no_trial") if profile_done else t(code, "language_changed")
        if not profile_done:
            text = f"{text}\n\n{t(code, 'finish_onboarding')}"
        await callback.message.edit_text(text)
        return

    await state.set_state(Onboarding.name)
    await callback.message.edit_text(t(code, "ask_name"))


# ---------------------------------------------------------------------------
# Name
# ---------------------------------------------------------------------------
@router.message(Onboarding.name, F.text)
async def on_name(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    text = (message.text or "").strip()
    if not valid_name(text):
        await message.answer(t(lang, "bad_name"))
        return

    user.full_name = normalize_name(text)
    await db.flush()

    if user.phone:
        await state.set_state(Onboarding.resume)
        await _ask_resume(message, lang)
        return

    await state.set_state(Onboarding.phone)
    await message.answer(t(lang, "ask_phone"), reply_markup=phone_kb(lang))


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------
@router.message(Onboarding.phone, F.contact)
async def on_phone(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(t(lang, "phone_not_own"), reply_markup=phone_kb(lang))
        return

    user.phone = normalize_phone(contact.phone_number)
    await db.flush()

    await message.answer(t(lang, "use_button"), reply_markup=remove_kb())
    await state.set_state(Onboarding.resume)
    await _ask_resume(message, lang)


@router.message(Onboarding.phone)
async def on_phone_invalid(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await message.answer(t(lang, "phone_not_own"), reply_markup=phone_kb(lang))


async def _ask_resume(message: Message, lang: str) -> None:
    await message.answer(t(lang, "ask_resume"), reply_markup=resume_kb(lang))


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------
@router.callback_query(Onboarding.resume, F.data == "resume:none")
async def on_resume_none(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
) -> None:
    lang = user.language or "mr"
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.education)
    await callback.message.answer(t(lang, "ask_education"))


def _extract_file_info(message: Message) -> Optional[tuple[str, str, int, str]]:
    """Returns (file_id, mime, file_size, filename) for a supported document/photo, else None."""
    if message.document:
        doc = message.document
        mime = doc.mime_type or ""
        filename = doc.file_name or ""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if mime not in _SUPPORTED_RESUME_MIMES and ext not in _RESUME_MIME_BY_EXT:
            return None
        resolved_mime = mime if mime in _SUPPORTED_RESUME_MIMES else _RESUME_MIME_BY_EXT.get(ext, mime)
        return doc.file_id, resolved_mime, doc.file_size or 0, filename
    if message.photo:
        largest = message.photo[-1]
        return largest.file_id, "image/jpeg", largest.file_size or 0, "photo.jpg"
    return None


@router.message(Onboarding.resume, F.document | F.photo)
async def on_resume_file(
    message: Message, state: FSMContext, db: AsyncSession, user: User
) -> None:
    lang = user.language or "mr"
    info = _extract_file_info(message)
    if info is None:
        await message.answer(t(lang, "resume_bad_file", mb=settings.MAX_RESUME_MB))
        return

    file_id, mime, file_size, filename = info
    max_bytes = settings.MAX_RESUME_MB * 1024 * 1024
    if file_size and file_size > max_bytes:
        await message.answer(t(lang, "resume_bad_file", mb=settings.MAX_RESUME_MB))
        return

    checking_msg = await message.answer(t(lang, "resume_checking"))
    await message.bot.send_chat_action(message.chat.id, "upload_document")

    try:
        buffer = await message.bot.download(file_id)
        data = buffer.read()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to download resume file for user %s", user.id)
        await checking_msg.edit_text(t(lang, "resume_failed"))
        return

    categories = {c.slug: c.name for c in await _active_categories(db)}
    result = await ai.parse_resume(data, mime, categories)

    if result is None:
        await checking_msg.edit_text(t(lang, "resume_failed"))
        return
    if not result.is_resume:
        await checking_msg.edit_text(t(lang, "resume_not_resume"))
        return

    profile = user.profile
    path = await storage.save_resume(
        user.id, data, mime, filename,
        previous_resume_path=profile.resume_path if profile else None,
    )

    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        user.profile = profile

    profile.education = result.highest_education
    profile.course = result.course
    profile.skills = result.skills
    profile.experience_years = result.experience_years or 0
    profile.summary = result.summary
    profile.resume_path = path
    profile.resume_mime = mime
    profile.parsed_json = result.model_dump()
    await db.flush()

    if not user.district and result.city_or_district:
        canon = canonical_district(result.city_or_district)
        user.district = canon if canon else result.city_or_district.title()
        await db.flush()

    await state.update_data(suggested_slugs=result.suggested_category_slugs)
    await state.set_state(Onboarding.confirm_resume)
    await checking_msg.edit_text(
        _resume_summary_text(lang, profile), reply_markup=confirm_kb(lang)
    )


@router.message(Onboarding.resume)
async def on_resume_other(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await message.answer(t(lang, "resume_bad_file", mb=settings.MAX_RESUME_MB))


def _resume_summary_text(lang: str, profile: Profile) -> str:
    skills = ", ".join(profile.skills) if profile.skills else t(lang, "not_given")
    return t(
        lang, "resume_summary",
        education=html.escape(profile.education or t(lang, "not_given")),
        course=html.escape(profile.course or t(lang, "not_given")),
        skills=html.escape(skills),
        experience=profile.experience_years or 0,
    )


@router.callback_query(Onboarding.confirm_resume, F.data == "conf:yes")
async def on_confirm_resume_yes(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
) -> None:
    lang = user.language or "mr"
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _after_details(callback.message, state, db, user, lang)


@router.callback_query(Onboarding.confirm_resume, F.data == "conf:edit")
async def on_confirm_resume_edit(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
) -> None:
    lang = user.language or "mr"
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.education)
    await callback.message.answer(t(lang, "ask_education"))


# ---------------------------------------------------------------------------
# Manual education / course / skills
# ---------------------------------------------------------------------------
@router.message(Onboarding.education, F.text)
async def on_education(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    profile = user.profile
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        user.profile = profile
    profile.education = (message.text or "").strip()[:160]
    await db.flush()

    await state.set_state(Onboarding.course)
    await message.answer(t(lang, "ask_course"))


@router.message(Onboarding.course, F.text)
async def on_course(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    text = (message.text or "").strip()
    user.profile.course = None if text == "-" else text[:160]
    await db.flush()

    await state.set_state(Onboarding.skills)
    await message.answer(t(lang, "ask_skills"))


@router.message(Onboarding.skills, F.text)
async def on_skills(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    text = (message.text or "").strip()
    if text == "-":
        skills: list[str] = []
    else:
        skills = [s.strip() for s in text.split(",") if s.strip()][:12]
    user.profile.skills = skills
    await db.flush()

    await _after_details(message, state, db, user, lang)


async def _after_details(
    message: Message, state: FSMContext, db: AsyncSession, user: User, lang: str
) -> None:
    data = await state.get_data()
    mode = data.get("mode", Mode.ONBOARDING)
    if mode == Mode.EDIT_PROFILE:
        await state.clear()
        await message.answer(t(lang, "profile_done_no_trial"))
        return
    # job type first, then categories: "government or private?" is an easier first choice
    # than a category list, and it frames the categories that follow
    await _show_job_types(message, state, db, user, lang)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
async def _show_categories(
    target: Message, state: FSMContext, db: AsyncSession, user: User, lang: str, edit: bool
) -> None:
    data = await state.get_data()
    selected_ids: list[int] = data.get("selected_category_ids", [])
    suggested_slugs: list[str] = data.get("suggested_slugs", [])

    all_categories = await _active_categories(db)
    show_all = not suggested_slugs

    if show_all:
        shown = all_categories
    else:
        shown = [c for c in all_categories if c.slug in suggested_slugs]
        selected_extra = [c for c in all_categories if c.id in selected_ids and c not in shown]
        shown = shown + selected_extra

    await state.update_data(
        shown_category_ids=[c.id for c in shown], show_all=show_all
    )

    max_categories = 3
    text = t(lang, "ask_categories", max=max_categories)
    markup = categories_kb(lang, shown, set(selected_ids), show_all_button=not show_all)

    await state.set_state(Onboarding.categories)
    if edit and isinstance(target, Message):
        try:
            await target.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest:
            pass
    await target.answer(text, reply_markup=markup)


async def _rerender_categories_markup(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, lang: str
) -> None:
    data = await state.get_data()
    shown_ids: list[int] = data.get("shown_category_ids", [])
    selected_ids: list[int] = data.get("selected_category_ids", [])
    show_all = data.get("show_all", False)

    if shown_ids:
        rows = (
            await db.execute(select(Category).where(Category.id.in_(shown_ids)))
        ).scalars().all()
        by_id = {c.id: c for c in rows}
        shown = [by_id[i] for i in shown_ids if i in by_id]
    else:
        shown = []

    markup = categories_kb(lang, shown, set(selected_ids), show_all_button=not show_all)
    try:
        await callback.message.edit_reply_markup(reply_markup=markup)
    except TelegramBadRequest:
        pass


@router.callback_query(Onboarding.categories, F.data.startswith("cat:"))
async def on_category_action(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
) -> None:
    lang = user.language or "mr"
    action = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected_ids: list[int] = list(data.get("selected_category_ids", []))
    max_categories = 3

    if action == "type":
        await callback.answer()
        await state.set_state(Onboarding.category_text)
        await callback.message.answer(t(lang, "type_category"))
        return

    if action == "all":
        await callback.answer()
        all_categories = await _active_categories(db)
        await state.update_data(
            shown_category_ids=[c.id for c in all_categories], show_all=True
        )
        markup = categories_kb(lang, all_categories, set(selected_ids), show_all_button=False)
        try:
            await callback.message.edit_reply_markup(reply_markup=markup)
        except TelegramBadRequest:
            pass
        return

    if action == "next":
        if not selected_ids:
            await callback.answer(t(lang, "pick_one_category"), show_alert=True)
            return
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)
        await _finish_onboarding(callback.message, state, db, user, lang)
        return

    # toggle a category id
    try:
        cat_id = int(action)
    except ValueError:
        await callback.answer()
        return

    if cat_id in selected_ids:
        selected_ids.remove(cat_id)
    else:
        if len(selected_ids) >= max_categories:
            await callback.answer(t(lang, "max_categories", max=max_categories), show_alert=True)
            return
        selected_ids.append(cat_id)

    await state.update_data(selected_category_ids=selected_ids)
    await callback.answer()
    await _rerender_categories_markup(callback, state, db, lang)


@router.message(Onboarding.category_text, F.text)
async def on_category_text(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    text = (message.text or "").strip()
    all_categories = await _active_categories(db)

    match: Optional[Category] = None
    lowered = text.lower()
    for cat in all_categories:
        names = [cat.name, cat.name_mr or "", cat.name_hi or ""]
        if any(lowered in n.lower() or n.lower() in lowered for n in names if n):
            match = cat
            break

    if match is None:
        await message.bot.send_chat_action(message.chat.id, "typing")
        categories = {c.slug: c.name for c in all_categories}
        slug = await ai.map_category(text, categories)
        if slug:
            match = next((c for c in all_categories if c.slug == slug), None)

    data = await state.get_data()
    selected_ids: list[int] = list(data.get("selected_category_ids", []))
    max_categories = 3

    if match is None:
        await message.answer(t(lang, "category_not_found"))
        await _show_categories(message, state, db, user, lang, edit=False)
        return

    if match.id not in selected_ids:
        if len(selected_ids) >= max_categories:
            await message.answer(t(lang, "max_categories", max=max_categories))
        else:
            selected_ids.append(match.id)
            await state.update_data(selected_category_ids=selected_ids)
            await message.answer(t(lang, "category_added", name=html.escape(match.label(lang))))

    await _show_categories(message, state, db, user, lang, edit=False)


# ---------------------------------------------------------------------------
# Job types
# ---------------------------------------------------------------------------
async def _show_job_types(
    message: Message, state: FSMContext, db: AsyncSession, user: User, lang: str
) -> None:
    data = await state.get_data()
    selected: list[str] = data.get("selected_job_types", [])
    await state.set_state(Onboarding.job_types)
    await message.answer(t(lang, "ask_job_types"), reply_markup=job_types_kb(lang, set(selected)))


@router.callback_query(Onboarding.job_types, F.data.startswith("jt:"))
async def on_job_type(callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    action = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected: list[str] = list(data.get("selected_job_types", []))

    if action == "next":
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.update_data(selected_job_types=selected)
        await _show_categories(callback.message, state, db, user, lang, edit=False)
        return

    if action in selected:
        selected.remove(action)
    else:
        selected.append(action)
    await state.update_data(selected_job_types=selected)
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=job_types_kb(lang, set(selected)))
    except TelegramBadRequest:
        pass


# ---------------------------------------------------------------------------
# Finish
# ---------------------------------------------------------------------------
async def _finish_onboarding(
    message: Message, state: FSMContext, db: AsyncSession, user: User, lang: str
) -> None:
    from app.db.models import UserCategory

    data = await state.get_data()
    selected_category_ids: list[int] = data.get("selected_category_ids", [])
    selected_job_types: list[str] = data.get("selected_job_types", [])

    for link in list(user.category_links):
        await db.delete(link)
    await db.flush()
    for cat_id in selected_category_ids:
        db.add(UserCategory(user_id=user.id, category_id=cat_id))

    user.job_types = selected_job_types
    user.status = "active"
    await db.flush()
    await db.refresh(user, attribute_names=["category_links"])

    is_first_completion = user.trial_ends_at is None
    await start_trial(db, user)
    await state.clear()

    if is_first_completion:
        from app.config import settings as app_settings
        from app.services.access import get_setting

        trial_days = await get_setting(db, "trial_days", 3)
        await message.answer(
            t(
                lang, "profile_done_trial",
                name=html.escape(user.full_name or ""),
                days=trial_days,
            )
        )
        sent = await send_digest_to_user(db, message.bot, user, limit=10)
        if sent == 0:
            await message.answer(t(lang, "no_jobs_now"))

        await send_push_to_admins(
            db, "New student signed up", user.full_name or "A student", {"type": "new_user"}
        )
    else:
        await message.answer(t(lang, "profile_done_no_trial"))
