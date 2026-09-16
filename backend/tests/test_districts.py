"""T4: canonical_district aliases, Devanagari, fuzzy match, anywhere markers (Chapter 21.1)."""
import pytest

from app.services.districts import canonical_district


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("aurangabad", "Chhatrapati Sambhajinagar"),
        ("Aurangabad", "Chhatrapati Sambhajinagar"),
        ("नागपूर", "Nagpur"),
        ("Kolhapure", "Kolhapur"),  # fuzzy match
        ("any", None),
        ("wfh", None),
        ("remote", None),
        ("Pune", "Pune"),
        ("pune", "Pune"),
        ("ahmednagar", "Ahilyanagar"),
        ("osmanabad", "Dharashiv"),
    ],
)
def test_canonical_district(raw, expected):
    assert canonical_district(raw) == expected


def test_canonical_district_none_for_empty():
    assert canonical_district(None) is None
    assert canonical_district("") is None
