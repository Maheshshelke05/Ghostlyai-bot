"""Canonical Maharashtra district list, aliases and fuzzy matching (Chapter 9.2)."""
from __future__ import annotations

import difflib

DISTRICTS: list[str] = [
    "Ahilyanagar", "Akola", "Amravati", "Beed", "Bhandara", "Buldhana", "Chandrapur",
    "Chhatrapati Sambhajinagar", "Dharashiv", "Dhule", "Gadchiroli", "Gondia", "Hingoli",
    "Jalgaon", "Jalna", "Kolhapur", "Latur", "Mumbai", "Nagpur", "Nanded", "Nandurbar",
    "Nashik", "Palghar", "Parbhani", "Pune", "Raigad", "Ratnagiri", "Sangli", "Satara",
    "Sindhudurg", "Solapur", "Thane", "Wardha", "Washim", "Yavatmal",
]

TOP_DISTRICTS: list[str] = [
    "Pune", "Mumbai", "Nagpur", "Nashik", "Thane", "Chhatrapati Sambhajinagar",
    "Kolhapur", "Solapur", "Amravati", "Ahilyanagar", "Satara", "Sangli",
]

# lowercased alias -> canonical district name
ALIASES: dict[str, str] = {
    "aurangabad": "Chhatrapati Sambhajinagar",
    "sambhajinagar": "Chhatrapati Sambhajinagar",
    "chhatrapati sambhajinagar": "Chhatrapati Sambhajinagar",
    "ahmednagar": "Ahilyanagar",
    "nagar": "Ahilyanagar",
    "ahilyanagar": "Ahilyanagar",
    "osmanabad": "Dharashiv",
    "dharashiv": "Dharashiv",
    "bombay": "Mumbai",
    "mumbai city": "Mumbai",
    "mumbai suburban": "Mumbai",
    "mumbai": "Mumbai",
    "navi mumbai": "Thane",
    "पुणे": "Pune",
    "मुंबई": "Mumbai",
    "नागपूर": "Nagpur",
    "नागपुर": "Nagpur",
    "नाशिक": "Nashik",
    "ठाणे": "Thane",
    "कोल्हापूर": "Kolhapur",
    "सोलापूर": "Solapur",
    "अमरावती": "Amravati",
    "सातारा": "Satara",
    "सांगली": "Sangli",
    "औरंगाबाद": "Chhatrapati Sambhajinagar",
    "संभाजीनगर": "Chhatrapati Sambhajinagar",
    "अहमदनगर": "Ahilyanagar",
    "अहिल्यानगर": "Ahilyanagar",
    "लातूर": "Latur",
    "नांदेड": "Nanded",
    "जळगाव": "Jalgaon",
    "अकोला": "Akola",
    "वर्धा": "Wardha",
    "चंद्रपूर": "Chandrapur",
    "रत्नागिरी": "Ratnagiri",
    "रायगड": "Raigad",
    "बीड": "Beed",
    "यवतमाळ": "Yavatmal",
    "धुळे": "Dhule",
    "जालना": "Jalna",
    "परभणी": "Parbhani",
}

ANYWHERE_WORDS = {"any", "all", "remote", "wfh", "all maharashtra", "anywhere", "kuthehi", "कुठेही"}

_FUZZY_CUTOFF = 0.8


def canonical_district(text: str | None) -> str | None:
    """Normalize free text into a canonical district name, or None for "anywhere"/unmatched-but-outside.

    Returns the canonical name if it matches (exact, alias, or fuzzy >= 0.8 similarity to a known
    district). Returns None for "anywhere"/"remote"/etc. For text that looks like a real place but
    isn't a Maharashtra district (e.g. "Indore"), the caller should fall back to Title Case as-is —
    this function only resolves Maharashtra districts and anywhere-markers.
    """
    if not text:
        return None
    normalized = " ".join(text.strip().split()).lower()
    if not normalized:
        return None
    if normalized in ANYWHERE_WORDS:
        return None

    for district in DISTRICTS:
        if normalized == district.lower():
            return district

    if normalized in ALIASES:
        return ALIASES[normalized]

    candidates = [d.lower() for d in DISTRICTS] + list(ALIASES.keys())
    matches = difflib.get_close_matches(normalized, candidates, n=1, cutoff=_FUZZY_CUTOFF)
    if matches:
        match = matches[0]
        for district in DISTRICTS:
            if district.lower() == match:
                return district
        if match in ALIASES:
            return ALIASES[match]

    return None
