"""FSM states for the onboarding / profile-edit conversation (Chapter 6.1)."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    language = State()
    name = State()
    phone = State()
    resume = State()
    confirm_resume = State()
    education = State()
    course = State()
    skills = State()
    categories = State()
    category_text = State()
    job_types = State()


class Mode:
    """Why the user is currently walking through (parts of) the onboarding flow."""

    ONBOARDING = "onboarding"
    EDIT_PROFILE = "edit_profile"
    EDIT_CATEGORIES = "edit_categories"
    LANGUAGE_ONLY = "language_only"
