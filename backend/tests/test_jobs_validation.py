"""T18-T22: job row validation, fingerprinting, bulk CSV/XLSX upload (Chapter 21.1)."""
import io

import openpyxl
import pytest

from app.services.jobs import fingerprint, read_bulk_file, validate_job_row


def _categories():
    return {"accounts-finance": 1, "other": 2}


def test_invalid_apply_link_raises():
    row = {"title": "Clerk", "company": "ABC", "category_slug": "accounts-finance", "apply_link": "abc"}
    with pytest.raises(ValueError):
        validate_job_row(row, _categories())


def test_unknown_category_raises():
    row = {
        "title": "Clerk", "company": "ABC", "category_slug": "not-a-real-category",
        "apply_link": "https://example.com/x",
    }
    with pytest.raises(ValueError):
        validate_job_row(row, _categories())


def test_fingerprint_ignores_case_and_extra_spaces():
    a = fingerprint("Junior  Accountant", "Shree Traders", "https://x.com/1")
    b = fingerprint("junior accountant", "shree traders", "https://x.com/1")
    assert a == b


def _row(i: int, category="accounts-finance", link_ok=True, cat_ok=True):
    return {
        "title": f"Job {i}",
        "company": "Co",
        "category_slug": category if cat_ok else "nope",
        "apply_link": f"https://example.com/{i}" if link_ok else "not-a-link",
        "job_type": "private",
    }


def test_bulk_csv_created_duplicates_errors():
    rows = [_row(1), _row(2), _row(1), _row(4, link_ok=False), _row(5, cat_ok=False)]
    csv_lines = ["title,company,category_slug,apply_link,job_type"]
    for r in rows:
        csv_lines.append(f"{r['title']},{r['company']},{r['category_slug']},{r['apply_link']},{r['job_type']}")
    data = ("\n".join(csv_lines)).encode("utf-8-sig")

    parsed = read_bulk_file("jobs.csv", data)
    categories = _categories()

    created, duplicates, errors = 0, 0, []
    seen_fingerprints = set()
    for row_number, raw in parsed:
        try:
            kwargs = validate_job_row(raw, categories)
        except ValueError as exc:
            errors.append((row_number, str(exc)))
            continue
        if kwargs["fingerprint"] in seen_fingerprints:
            duplicates += 1
            continue
        seen_fingerprints.add(kwargs["fingerprint"])
        created += 1

    assert created == 2
    assert duplicates == 1
    assert len(errors) == 2
    assert errors[0][0] == 5  # row 1 is header, "Job 4" (invalid link) is row 5
    assert errors[1][0] == 6  # "Job 5" (invalid category) is row 6


def test_bulk_xlsx_same_result():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["title", "company", "category_slug", "apply_link", "job_type"])
    for r in [_row(1), _row(2), _row(1), _row(4, link_ok=False), _row(5, cat_ok=False)]:
        ws.append([r["title"], r["company"], r["category_slug"], r["apply_link"], r["job_type"]])
    buf = io.BytesIO()
    wb.save(buf)

    parsed = read_bulk_file("jobs.xlsx", buf.getvalue())
    categories = _categories()

    created, duplicates, errors = 0, 0, []
    seen_fingerprints = set()
    for row_number, raw in parsed:
        try:
            kwargs = validate_job_row(raw, categories)
        except ValueError as exc:
            errors.append((row_number, str(exc)))
            continue
        if kwargs["fingerprint"] in seen_fingerprints:
            duplicates += 1
            continue
        seen_fingerprints.add(kwargs["fingerprint"])
        created += 1

    assert created == 2
    assert duplicates == 1
    assert len(errors) == 2
