"""Catch-all handler: registered last so specific handlers always take priority (Chapter 6.3)."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.account import _support_line, require_profile
from app.bot.texts import t
from app.db.models import User

router = Router(name="fallback")


@router.message()
async def on_fallback(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    lang = user.language or "mr"
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer(t(lang, "use_button"))
        return
    if not require_profile(user):
        await message.answer(t(lang, "finish_onboarding"))
        return
    await message.answer(t(lang, "help", support=_support_line(lang)))
