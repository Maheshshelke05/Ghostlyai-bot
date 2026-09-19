"""Student app browsable job feed (Phase B): GET /student/jobs, /student/jobs/{id}."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.db.models import JobDelivery, utcnow
from app.services.auth import create_token

from tests.conftest import make_job, make_user


async def _student_headers(user) -> dict:
    token = create_token(user.id, "student")
    return {"Authorization": f"Bearer {token}"}


async def test_browse_returns_matching_jobs(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"], job_types=[])
    await make_job(db, categories, category_slug="it-software", title="Backend Dev")
    await db.commit()

    resp = await client.get("/student/jobs", headers=await _student_headers(user))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Backend Dev"
    assert body["items"][0]["apply_url"].startswith("http")


async def test_browse_still_shows_already_delivered_jobs(client, db, categories):
    """Unlike the Telegram digest's matching_jobs_stmt, the browsable feed keeps showing a
    job the student has already seen/been sent - it's a feed, not a one-shot alert."""
    user = await make_user(db, category_slugs=["it-software"])
    job = await make_job(db, categories, category_slug="it-software")
    db.add(JobDelivery(job_id=job.id, user_id=user.id))
    await db.commit()

    resp = await client.get("/student/jobs", headers=await _student_headers(user))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


async def test_browse_respects_category_subscription_boundary(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"])
    await db.commit()

    other_id = categories["banking"].id
    resp = await client.get(
        "/student/jobs", params={"category_id": other_id}, headers=await _student_headers(user)
    )
    assert resp.status_code == 400


async def test_browse_job_type_filter(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"], job_types=[])
    await make_job(db, categories, category_slug="it-software", title="Govt role", job_type="govt")
    await make_job(db, categories, category_slug="it-software", title="Private role", job_type="private")
    await db.commit()

    resp = await client.get(
        "/student/jobs", params={"job_type": "govt"}, headers=await _student_headers(user)
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Govt role"

    resp = await client.get(
        "/student/jobs", params={"job_type": "not-a-type"}, headers=await _student_headers(user)
    )
    assert resp.status_code == 400


async def test_browse_search_query(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"], job_types=[])
    await make_job(db, categories, category_slug="it-software", title="React Native Developer", company="Acme")
    await make_job(db, categories, category_slug="it-software", title="Accountant", company="Beta Traders")
    await db.commit()

    resp = await client.get(
        "/student/jobs", params={"q": "react"}, headers=await _student_headers(user)
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "React Native Developer"


async def test_browse_pagination_cursor(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"], job_types=[])
    base = utcnow() - timedelta(hours=2)
    for i in range(3):
        await make_job(
            db, categories, category_slug="it-software", title=f"Job {i}",
            created_at=base + timedelta(minutes=i),
        )
    await db.commit()

    resp = await client.get(
        "/student/jobs", params={"limit": 2}, headers=await _student_headers(user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["title"] == "Job 2"  # newest first
    assert body["next_cursor"] is not None

    resp2 = await client.get(
        "/student/jobs", params={"limit": 2, "cursor": body["next_cursor"]},
        headers=await _student_headers(user),
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["title"] == "Job 0"
    assert body2["next_cursor"] is None


async def test_apply_click_tracking_via_redirect(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"])
    job = await make_job(db, categories, category_slug="it-software", apply_link="https://example.com/apply/xyz")
    await db.commit()

    resp = await client.get("/student/jobs", headers=await _student_headers(user))
    apply_url = resp.json()["items"][0]["apply_url"]
    token = apply_url.rsplit("/r/", 1)[1]

    redirect_resp = await client.get(f"/r/{token}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.com/apply/xyz"

    delivery = (
        await db.execute(select(JobDelivery).where(JobDelivery.job_id == job.id))
    ).scalar_one()
    assert delivery.clicked_at is not None


async def test_job_detail_not_found_outside_subscribed_categories(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"])
    job = await make_job(db, categories, category_slug="banking")
    await db.commit()

    resp = await client.get(f"/student/jobs/{job.id}", headers=await _student_headers(user))
    assert resp.status_code == 404


async def test_job_detail_ok(client, db, categories):
    user = await make_user(db, category_slugs=["it-software"])
    job = await make_job(db, categories, category_slug="it-software", title="QA Engineer")
    await db.commit()

    resp = await client.get(f"/student/jobs/{job.id}", headers=await _student_headers(user))
    assert resp.status_code == 200
    assert resp.json()["title"] == "QA Engineer"
