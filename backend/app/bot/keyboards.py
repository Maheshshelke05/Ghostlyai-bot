"""All inline / reply keyboards used by the bot (Chapter 6/7)."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.texts import LANGUAGES, t
from app.db.models import Category
from app.services.districts import TOP_DISTRICTS

OTHER_DISTRICT = "__other__"


def language_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    flags = {"mr": "🇮🇳", "hi": "🇮🇳", "en": "🇬🇧"}
    for code, label in LANGUAGES.items():
        builder.button(text=f"{flags.get(code, '')} {label}", callback_data=f"lang:{code}")
    builder.adjust(3)
    return builder.as_markup()


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "share_phone_btn"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def district_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name in TOP_DISTRICTS:
        builder.button(text=name, callback_data=f"dist:{name}")
    builder.button(text=t(lang, "other_district_btn"), callback_data=f"dist:{OTHER_DISTRICT}")
    builder.adjust(2)
    return builder.as_markup()


def resume_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "no_resume_btn"), callback_data="resume:none")
    builder.adjust(1)
    return builder.as_markup()


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "confirm_btn"), callback_data="conf:yes")
    builder.button(text=t(lang, "edit_btn"), callback_data="conf:edit")
    builder.adjust(2)
    return builder.as_markup()


def categories_kb(
    lang: str,
    shown: list[Category],
    selected_ids: set[int],
    show_all_button: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in shown:
        mark = "✅ " if cat.id in selected_ids else ""
        builder.button(text=f"{mark}{cat.label(lang)}", callback_data=f"cat:{cat.id}")
    builder.adjust(1)
    if show_all_button:
        builder.row(
            InlineKeyboardButton(text=t(lang, "more_categories_btn"), callback_data="cat:all")
        )
    builder.row(
        InlineKeyboardButton(text=t(lang, "type_category_btn"), callback_data="cat:type"),
        InlineKeyboardButton(text=t(lang, "next_btn"), callback_data="cat:next"),
    )
    return builder.as_markup()


def job_types_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    labels = {
        "govt": t(lang, "jt_govt"),
        "private": t(lang, "jt_private"),
        "internship": t(lang, "jt_internship"),
        "wfh": t(lang, "jt_wfh"),
    }
    builder = InlineKeyboardBuilder()
    for code, label in labels.items():
        mark = "✅ " if code in selected else ""
        builder.button(text=f"{mark}{label}", callback_data=f"jt:{code}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t(lang, "next_btn"), callback_data="jt:next"))
    return builder.as_markup()


def pay_kb(lang: str, price: int, url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "pay_btn", price=price), url=url)
    return builder.as_markup()


def renew_kb(lang: str, price: int, url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "renew_btn", price=price), url=url)
    return builder.as_markup()


def subscribe_cta_kb(lang: str, price: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "pay_btn", price=price), callback_data="sub:pay")
    return builder.as_markup()


def profile_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "edit_profile_btn"), callback_data="profile:edit")
    builder.button(text=t(lang, "edit_categories_btn"), callback_data="profile:categories")
    builder.adjust(1)
    return builder.as_markup()


def apply_kb(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """items: list of (position_in_digest, tracking_url)."""
    builder = InlineKeyboardBuilder()
    for n, url in items:
        builder.button(text=f"{n}. Apply", url=url)
    builder.adjust(min(len(items), 5) or 1)
    return builder.as_markup()
