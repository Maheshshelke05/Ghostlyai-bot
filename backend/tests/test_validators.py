"""T1-T3: name validation and phone normalization (Chapter 21.1)."""
import pytest

from app.services.validators import normalize_phone, valid_name


@pytest.mark.parametrize("name", ["Rahul Patil", "राहुल पाटील", "Mary O'Brien-Singh", "  Anita   Kumar "])
def test_valid_name_accepts_good_names(name):
    assert valid_name(name) is True


@pytest.mark.parametrize("name", ["Rahul", "R2D2 X", "@@ ##", "", "A", "1234 5678"])
def test_valid_name_rejects_bad_names(name):
    assert valid_name(name) is False


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9876543210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("+919876543210", "+919876543210"),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected
