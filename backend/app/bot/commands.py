"""Registers the bot command list shown in Telegram's menu, per language."""
from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand

_COMMANDS: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("start", "Start / profile status"),
        ("jobs", "Jobs available right now"),
        ("profile", "View or edit your profile"),
        ("category", "Change job categories"),
        ("subscribe", "Subscription status & payment"),
        ("language", "Change language"),
        ("support", "Ask a question / report a problem"),
        ("help", "All commands"),
    ],
    "mr": [
        ("start", "सुरुवात / प्रोफाइल स्टेटस"),
        ("jobs", "आत्ताचे jobs"),
        ("profile", "प्रोफाइल पाहा / बदला"),
        ("category", "Category बदला"),
        ("subscribe", "Subscription स्टेटस व पेमेंट"),
        ("language", "भाषा बदला"),
        ("support", "तक्रार / प्रश्न विचारा"),
        ("help", "सर्व commands"),
    ],
    "hi": [
        ("start", "शुरुआत / प्रोफाइल स्टेटस"),
        ("jobs", "अभी की jobs"),
        ("profile", "प्रोफाइल देखें / बदलें"),
        ("category", "Category बदलें"),
        ("subscribe", "Subscription स्टेटस व पेमेंट"),
        ("language", "भाषा बदलें"),
        ("support", "शिकायत / सवाल पूछें"),
        ("help", "सभी commands"),
    ],
}


async def set_my_commands(bot: Bot) -> None:
    for lang, commands in _COMMANDS.items():
        bot_commands = [BotCommand(command=c, description=d) for c, d in commands]
        if lang == "en":
            await bot.set_my_commands(bot_commands)
        else:
            await bot.set_my_commands(bot_commands, language_code=lang)
