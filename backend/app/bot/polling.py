"""Local development runner: long-polling instead of a webhook.

Usage: python -m app.bot.polling
"""
from __future__ import annotations

import asyncio
import logging

from app.bot.commands import set_my_commands
from app.bot.loader import get_bot, get_dispatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    bot = get_bot()
    dp = get_dispatcher()
    await bot.delete_webhook(drop_pending_updates=False)
    await set_my_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
