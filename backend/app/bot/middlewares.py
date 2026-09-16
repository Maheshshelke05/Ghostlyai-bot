"""Middleware that loads/creates the DB user and injects db+user into handler data."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from sqlalchemy import select

from app.bot.texts import t
from app.db.models import User
from app.db.session import session_scope


class DbUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        message: Message | None = event if isinstance(event, Message) else None
        callback: CallbackQuery | None = event if isinstance(event, CallbackQuery) else None

        from_user = None
        chat_type = "private"
        if message is not None:
            from_user = message.from_user
            chat_type = message.chat.type
        elif callback is not None:
            from_user = callback.from_user
            if callback.message is not None:
                chat_type = callback.message.chat.type

        if from_user is None or from_user.is_bot:
            return None
        if chat_type != "private":
            # Bot only operates in 1:1 chats; ignore group/channel messages entirely.
            return None

        async with session_scope() as db:
            user = (
                await db.execute(select(User).where(User.telegram_id == from_user.id))
            ).scalar_one_or_none()

            if user is None:
                user = User(
                    telegram_id=from_user.id,
                    username=from_user.username,
                    status="onboarding",
                )
                db.add(user)
                await db.flush()
            else:
                if user.username != from_user.username:
                    user.username = from_user.username
                if user.status == "bot_blocked":
                    user.status = "active" if user.category_links else "onboarding"

            if user.status == "blocked":
                lang = user.language or "mr"
                if message is not None:
                    await message.answer(t(lang, "blocked"))
                elif callback is not None:
                    await callback.answer(t(lang, "blocked"), show_alert=True)
                return None

            data["db"] = db
            data["user"] = user
            return await handler(event, data)
