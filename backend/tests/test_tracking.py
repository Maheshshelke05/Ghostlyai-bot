"""T27: click-tracking redirect - valid signature 302s, invalid/missing 404s (Chapter 21.1)."""
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.seed import seed_all
from app.services.notifier import tracking_url

from tests.conftest import make_job, make_user


async def _seeded_session(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    session = session_factory()
    await seed_all(session)
    return session


async def test_valid_tracking_token_redirects(engine, client):
    from sqlalchemy import select

    from app.db.models import Category, JobDelivery

    session = await _seeded_session(engine)
    categories = {c.slug: c for c in (await session.execute(select(Category))).scalars().all()}
    user = await make_user(session, category_slugs=["accounts-finance"])
    job = await make_job(session, categories, apply_link="https://example.com/apply/42")
    delivery = JobDelivery(job_id=job.id, user_id=user.id)
    session.add(delivery)
    await session.commit()
    delivery_id = delivery.id
    await session.close()

    url = tracking_url(delivery_id)
    path = url.split("://", 1)[1].split("/", 1)[1]  # strip scheme+host, keep "/r/..."

    resp = await client.get(f"/{path}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/apply/42"


async def test_invalid_signature_returns_404(client):
    resp = await client.get("/r/1-deadbeef00", follow_redirects=False)
    assert resp.status_code == 404


async def test_unknown_delivery_id_returns_404(client):
    from app.services.notifier import tracking_url

    url = tracking_url(999999)
    path = url.split("://", 1)[1].split("/", 1)[1]
    resp = await client.get(f"/{path}", follow_redirects=False)
    assert resp.status_code == 404
