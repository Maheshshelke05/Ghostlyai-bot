"""Account commands: /profile /jobs /category /subscribe /language /help (Chapter 6.4)."""
from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import language_kb, pay_kb, profile_kb, subscribe_cta_kb
from app.bot.states import Mode, Onboarding
from app.bot.texts import t
from app.config import settings
from app.db.models import User
from app.services.access import get_setting, has_access, status_line
from app.services.notifier import send_digest_to_user
from app.services.payments import PaymentError, get_or_create_payment_link

logger = logging.getLogger("app.bot.account")
router = Router(name="account")


def _support_line(lang: str) -> str:
    if settings.SUPPORT_USERNAME:
        return t(lang, "support_line", username=settings.SUPPORT_USERNAME)
    return ""


def require_profile(user: User) -> bool:
    return user.status == "active" and bool(user.category_links)


async def _send_finish_onboarding(message: Message, lang: str) -> None:
    await message.answer(t(lang, "finish_onboarding"))


@router.message(Command("help"))
async def cmd_help(message: Message, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await message.answer(t(lang, "help", support=_support_line(lang)))


@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await state.clear()
    await state.update_data(mode=Mode.LANGUAGE_ONLY)
    await state.set_state(Onboarding.language)
    await message.answer(t(lang, "choose_language"), reply_markup=language_kb())


@router.message(Command("profile"))
async def cmd_profile(message: Message, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    if not require_profile(user):
        await _send_finish_onboarding(message, lang)
        return
    await message.answer(_profile_text(user, lang), reply_markup=profile_kb(lang))


def _profile_text(user: User, lang: str) -> str:
    profile = user.profile
    categories = ", ".join(link.category.label(lang) for link in user.category_links) or "-"
    job_types_labels = {
        "govt": t(lang, "jt_govt"), "private": t(lang, "jt_private"),
        "internship": t(lang, "jt_internship"), "wfh": t(lang, "jt_wfh"),
    }
    job_types = ", ".join(job_types_labels.get(jt, jt) for jt in (user.job_types or [])) or "-"
    return t(
        lang, "profile_view",
        name=html.escape(user.full_name or "-"),
        phone=html.escape(user.phone or "-"),
        education=html.escape(profile.education if profile else "") or t(lang, "not_given"),
        course=html.escape(profile.course if profile and profile.course else t(lang, "not_given")),
        categories=html.escape(categories),
        job_types=html.escape(job_types),
        status=status_line(user, lang),
    )


@router.callback_query(F.data == "profile:edit")
async def on_profile_edit(callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await callback.answer()
    await state.clear()
    await state.update_data(mode=Mode.EDIT_PROFILE)
    await state.set_state(Onboarding.name)
    await callback.message.answer(t(lang, "ask_name"))


@router.callback_query(F.data == "profile:categories")
async def on_profile_categories(callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User) -> None:
    await callback.answer()
    await _start_edit_categories(callback.message, state, db, user)


@router.message(Command("category"))
async def cmd_category(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    if not require_profile(user):
        await _send_finish_onboarding(message, lang)
        return
    await _start_edit_categories(message, state, db, user)


async def _start_edit_categories(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    from app.bot.handlers.onboarding import _show_categories

    lang = user.language or "mr"
    await state.clear()
    await state.update_data(
        mode=Mode.EDIT_CATEGORIES,
        selected_category_ids=[link.category_id for link in user.category_links],
        selected_job_types=list(user.job_types or []),
    )
    await _show_categories(message, state, db, user, lang, edit=False)


@router.message(Command("jobs"))
async def cmd_jobs(message: Message, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    if not require_profile(user):
        await _send_finish_onboarding(message, lang)
        return

    if not has_access(user):
        price = await get_setting(db, "price_inr", 99)
        await message.answer(t(lang, "no_access"), reply_markup=subscribe_cta_kb(lang, int(price)))
        return

    sent = await send_digest_to_user(db, message.bot, user, limit=10)
    if sent == 0:
        await message.answer(t(lang, "no_jobs_now"))


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    if not require_profile(user):
        await _send_finish_onboarding(message, lang)
        return
    await _send_subscribe(message, db, user, lang)


@router.callback_query(F.data == "sub:pay")
async def on_sub_pay(callback: CallbackQuery, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await callback.answer()
    await _send_subscribe(callback.message, db, user, lang)


async def _send_subscribe(message: Message, db: AsyncSession, user: User, lang: str) -> None:
    price = int(await get_setting(db, "price_inr", 99))
    days = int(await get_setting(db, "subscription_days", 30))
    text = f"{status_line(user, lang)}\n\n{t(lang, 'subscribe_info', price=price, days=days)}"
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        payment = await get_or_create_payment_link(db, user)
    except PaymentError:
        await message.answer(f"{text}\n\n{t(lang, 'payment_error')}")
        return

    if not payment.short_url:
        await message.answer(f"{text}\n\n{t(lang, 'payment_error')}")
        return

    await message.answer(text, reply_markup=pay_kb(lang, price, payment.short_url))
