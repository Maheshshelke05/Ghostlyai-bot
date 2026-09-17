"""/support: a student writes to the admins, and admin replies come back here."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import support_kb
from app.bot.states import Support
from app.bot.texts import t
from app.db.models import SupportMessage, User
from app.services.push import send_push_to_admins

logger = logging.getLogger("app.bot.support")
router = Router(name="support")

MAX_SUPPORT_TEXT = 1000


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await state.set_state(Support.message)
    await message.answer(t(lang, "support_ask"), reply_markup=support_kb(lang))


@router.callback_query(F.data == "support:start")
async def on_support_button(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
) -> None:
    lang = user.language or "mr"
    await callback.answer()
    await state.set_state(Support.message)
    await callback.message.answer(t(lang, "support_ask"), reply_markup=support_kb(lang))


@router.callback_query(Support.message, F.data == "support:cancel")
async def on_support_cancel(
    callback: CallbackQuery, state: FSMContext, db: AsyncSession, user: User
) -> None:
    lang = user.language or "mr"
    await callback.answer()
    await state.clear()
    await callback.message.answer(t(lang, "support_cancelled"))


@router.message(Support.message, F.text)
async def on_support_text(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer(t(lang, "support_too_short"))
        return

    db.add(SupportMessage(user_id=user.id, direction="in", text=text[:MAX_SUPPORT_TEXT]))
    await db.flush()
    await state.clear()
    await message.answer(t(lang, "support_sent"))

    preview = text if len(text) <= 120 else text[:117] + "..."
    await send_push_to_admins(
        db, f"New support message — {user.full_name or 'a student'}", preview, {"type": "support"}
    )


@router.message(Support.message)
async def on_support_wrong_type(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    await message.answer(t(lang, "support_text_only"))
