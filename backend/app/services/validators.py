"""Pure validation/normalization helpers used by onboarding (Chapter 6.2)."""
from __future__ import annotations

import re
import unicodedata

# letters (incl. Devanagari + combining marks), spaces, dot, apostrophe, hyphen
_NAME_RE = re.compile(r"^[^\W\d_]+(?:[ .'\-][^\W\d_]+)*$", re.UNICODE)


def valid_name(text: str) -> bool:
    text = text.strip()
    if not (3 <= len(text) <= 80):
        return False
    words = text.split()
    if len(words) < 2:
        return False
    # Allow letters, Unicode combining marks (Devanagari matras), space, dot, apostrophe, hyphen.
    for ch in text:
        category = unicodedata.category(ch)
        if ch in " .'-":
            continue
        if category.startswith("L") or category.startswith("M"):
            continue
        return False
    return True


def normalize_name(text: str) -> str:
    text = " ".join(text.strip().split())
    if re.fullmatch(r"[A-Za-z .'\-]+", text):
        return text.title()
    return text


def normalize_phone(raw: str) -> str:
    """Converts a phone number to +91XXXXXXXXXX form."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 13 and digits.startswith("091"):
        return f"+91{digits[3:]}"
    if raw.startswith("+"):
        return raw
    return f"+{digits}"
