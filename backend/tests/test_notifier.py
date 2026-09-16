"""format_job_card should never leave a dangling emoji/line for missing optional fields."""
from datetime import date

from app.db.models import Job
from app.services.notifier import format_job_card


def _job(**overrides) -> Job:
    defaults = dict(
        id=1, category_id=1, title="Junior Accountant", company="Shree Traders",
        district="Nagpur", location_text=None, job_type="private", salary=None,
        qualification=None, apply_link="https://example.com/1", last_date=None, status="active",
        fingerprint="x",
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_job_card_with_all_optional_fields_present():
    job = _job(qualification="B.Com, Tally", salary="Rs 12,000", last_date=date(2026, 9, 30))
    text = format_job_card(job, 1, "en")
    assert "🎓 B.Com, Tally" in text
    assert "💰 Rs 12,000" in text
    assert "Last date: 30-09-2026" in text


def test_job_card_omits_missing_optional_fields_cleanly():
    job = _job()  # qualification, salary, last_date all None
    text = format_job_card(job, 1, "en")
    assert "🎓" not in text
    assert "💰" not in text
    assert "Last date" not in text
    # No stray blank/dangling lines from the omitted parts.
    assert "\n\n" not in text
    assert not text.endswith("\n")
