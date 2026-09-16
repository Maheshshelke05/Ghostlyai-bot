"""T10-T17: job matching rules (Chapter 10.1, 21.1)."""
from datetime import date, timedelta

from app.db.models import JobDelivery, utcnow
from app.services.jobs import matching_jobs

from tests.conftest import make_job, make_user


async def test_category_and_district_match(db, categories):
    user = await make_user(db, district="Nagpur", category_slugs=["accounts-finance"])
    await make_job(db, categories, category_slug="accounts-finance", district="Nagpur")
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 1


async def test_other_district_but_job_district_null_matches(db, categories):
    user = await make_user(db, district="Pune", category_slugs=["accounts-finance"])
    await make_job(db, categories, category_slug="accounts-finance", district=None)
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 1


async def test_other_district_office_job_does_not_match(db, categories):
    user = await make_user(db, district="Pune", category_slugs=["accounts-finance"])
    await make_job(db, categories, category_slug="accounts-finance", district="Nagpur", job_type="private")
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 0


async def test_wfh_job_matches_regardless_of_district(db, categories):
    user = await make_user(db, district="Pune", category_slugs=["accounts-finance"])
    await make_job(db, categories, category_slug="accounts-finance", district="Nagpur", job_type="wfh")
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 1


async def test_last_date_in_past_does_not_match(db, categories):
    user = await make_user(db, category_slugs=["accounts-finance"])
    yesterday = date.today() - timedelta(days=1)
    await make_job(db, categories, category_slug="accounts-finance", last_date=yesterday)
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 0


async def test_already_delivered_job_does_not_match_again(db, categories):
    user = await make_user(db, category_slugs=["accounts-finance"])
    job = await make_job(db, categories, category_slug="accounts-finance")
    db.add(JobDelivery(job_id=job.id, user_id=user.id))
    await db.flush()
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 0


async def test_empty_job_types_matches_all_types(db, categories):
    user = await make_user(db, category_slugs=["accounts-finance"], job_types=[])
    await make_job(db, categories, category_slug="accounts-finance", job_type="govt")
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 1


async def test_job_older_than_7_days_does_not_match(db, categories):
    user = await make_user(db, category_slugs=["accounts-finance"])
    old = utcnow() - timedelta(days=8)
    await make_job(db, categories, category_slug="accounts-finance", created_at=old)
    jobs = await matching_jobs(db, user, limit=10)
    assert len(jobs) == 0
