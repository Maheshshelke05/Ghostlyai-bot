"""Regression tests for the bugs found in the external code review (one test per real bug)."""
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Payment, User, utcnow
from app.db.seed import seed_all
from app.services.access import format_date_ist
from app.services.notifier import safe_send
from app.services.payments import mark_link_paid

from tests.conftest import make_user

JOB = {
    "title": "Junior Accountant",
    "company": "Acme Traders",
    "category_slug": "accounts-finance",
    "apply_link": "https://acme.example/jobs/1",
    "job_type": "private",
    "description": "2 openings, Saturday half day",
}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def _seed_categories(engine):
    async with _factory(engine)() as s:
        await seed_all(s)
        await s.commit()


# 1 - editing a job must not wipe its description
async def test_editing_a_job_keeps_its_description(client, owner_token, engine):
    await _seed_categories(engine)
    h = _auth(owner_token)
    created = await client.post("/admin/jobs", json=JOB, headers=h)
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]

    fetched = (await client.get(f"/admin/jobs/{job_id}", headers=h)).json()
    assert fetched["description"] == JOB["description"]

    # what the edit screen now sends: the loaded description goes back with the change
    edit = {**JOB, "salary": "15,000", "description": fetched["description"]}
    assert (await client.put(f"/admin/jobs/{job_id}", json=edit, headers=h)).status_code == 200

    after = (await client.get(f"/admin/jobs/{job_id}", headers=h)).json()
    assert after["salary"] == "15,000"
    assert after["description"] == JOB["description"]


# 2 - the same job twice in one batch / one CSV used to 500 on the unique constraint
async def test_batch_with_a_repeated_job_saves_one_and_counts_a_duplicate(client, owner_token, engine):
    await _seed_categories(engine)
    other = {**JOB, "apply_link": "https://acme.example/jobs/2"}
    resp = await client.post("/admin/jobs/batch", json={"jobs": [JOB, JOB, other]}, headers=_auth(owner_token))
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"created": 2, "duplicates": 1, "errors": []}


async def test_csv_upload_with_a_repeated_row_saves_one_and_counts_a_duplicate(client, owner_token, engine):
    await _seed_categories(engine)
    csv = (
        "title,company,category_slug,apply_link\n"
        "Office Clerk,Acme,accounts-finance,https://acme.example/clerk\n"
        "Office Clerk,Acme,accounts-finance,https://acme.example/clerk\n"
    )
    resp = await client.post(
        "/admin/jobs/bulk", files={"file": ("jobs.csv", csv.encode(), "text/csv")}, headers=_auth(owner_token)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 1
    assert resp.json()["duplicates"] == 1


# 5 - "&" / "<" in admin text used to fail the whole send under the HTML parse mode
class _HtmlStrictBot:
    def __init__(self):
        self.calls = []

    async def send_message(self, chat_id, text, reply_markup=None, disable_web_page_preview=None, **kwargs):
        self.calls.append(kwargs)
        if "parse_mode" not in kwargs:
            raise TelegramBadRequest(
                method=SendMessage(chat_id=chat_id, text=text),
                message="Bad Request: can't parse entities: Unsupported start tag",
            )
        return object()


async def test_message_with_bare_ampersand_falls_back_to_plain_text():
    bot = _HtmlStrictBot()
    assert await safe_send(bot, 42, "TCS & Infosys hiring <freshers>") == "ok"
    assert bot.calls == [{}, {"parse_mode": None}]


# 6 - dates shown to students were formatted in server (UTC) time
def test_user_facing_dates_are_ist_not_utc():
    just_after_ist_midnight = datetime(2026, 9, 29, 19, 0, tzinfo=timezone.utc)  # 00:30 IST, 30 Sep
    assert format_date_ist(just_after_ist_midnight) == "30-09-2026"


# 7 - paying from a reminder link never touches the bot, so a stale bot_blocked stuck
async def test_payment_clears_stale_bot_blocked_but_never_an_admin_ban(db):
    stale = await make_user(db, status="bot_blocked", category_slugs=["accounts-finance"])
    banned = await make_user(db, status="blocked", category_slugs=["accounts-finance"])
    for i, user in enumerate((stale, banned)):
        db.add(Payment(
            user_id=user.id, reference_id=f"rb{i}", razorpay_link_id=f"plink_rb{i}",
            amount_paise=9900, status="created", expires_at=utcnow() + timedelta(hours=1),
        ))
    await db.flush()

    await mark_link_paid(db, "plink_rb0", "pay_rb0", 9900)
    await mark_link_paid(db, "plink_rb1", "pay_rb1", 9900)

    assert stale.status == "active"
    assert banned.status == "blocked"


# 9 - two concurrent updates from a brand-new user both tried to insert them
async def test_concurrent_first_contact_resolves_to_the_existing_user(db, monkeypatch):
    from app.bot import middlewares

    winner = User(telegram_id=555001, username="fast", status="onboarding")
    db.add(winner)
    await db.flush()

    real_execute = db.execute
    calls = {"n": 0}

    class _NotFoundYet:
        def scalar_one_or_none(self):
            return None

    async def lookup_misses_once(stmt, *args, **kwargs):
        # simulates this task's lookup running just before the other task's insert landed
        calls["n"] += 1
        if calls["n"] == 1:
            return _NotFoundYet()
        return await real_execute(stmt, *args, **kwargs)

    monkeypatch.setattr(db, "execute", lookup_misses_once)
    user = await middlewares._get_or_create_user(db, 555001, "fast")
    assert user.id == winner.id


# 10 - the user list used to load every user into memory and filter in Python
async def test_user_list_filters_and_paginates_in_sql_matching_the_access_rules(client, owner_token, engine):
    now = utcnow()
    async with _factory(engine)() as s:
        await make_user(s, full_name="Paid Long", paid_until=now + timedelta(days=10))
        await make_user(s, full_name="Paid Soon", paid_until=now + timedelta(days=2))
        await make_user(s, full_name="Trial Soon", trial_ends_at=now + timedelta(days=2))
        await make_user(s, full_name="Expired", trial_ends_at=now - timedelta(days=1))
        # live paid access takes precedence over a later trial end
        await make_user(
            s, full_name="Paid Over Trial",
            paid_until=now + timedelta(days=5), trial_ends_at=now + timedelta(days=20),
        )
        await s.commit()

    h = _auth(owner_token)

    async def names(**params):
        resp = await client.get("/admin/users", params=params, headers=h)
        assert resp.status_code == 200, resp.text
        return {item["full_name"] for item in resp.json()["items"]}

    assert await names(access="paid") == {"Paid Long", "Paid Soon", "Paid Over Trial"}
    assert await names(access="trial") == {"Trial Soon"}
    assert await names(access="none") == {"Expired"}
    assert await names(expiring=3) == {"Paid Soon", "Trial Soon"}

    page = (await client.get("/admin/users", params={"size": 2, "page": 2}, headers=h)).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2


# 11 - dashboard counts via SQL and one range query per series instead of 14
async def test_dashboard_counts_and_week_series(client, owner_token, engine):
    now = utcnow()
    async with _factory(engine)() as s:
        await make_user(s, paid_until=now + timedelta(days=2))        # paid, expiring in 3 days
        await make_user(s, paid_until=now + timedelta(days=20))       # paid
        await make_user(s, trial_ends_at=now + timedelta(days=1))     # trial
        await make_user(s, status="onboarding", paid_until=now + timedelta(days=9))  # not active
        payer = await make_user(s)
        for ref, paid_at in (("today", now), ("old", now - timedelta(days=10))):
            s.add(Payment(
                user_id=payer.id, reference_id=f"dash_{ref}", razorpay_link_id=f"plink_dash_{ref}",
                amount_paise=9900, status="paid", paid_at=paid_at, expires_at=now,
            ))
        await s.commit()

    body = (await client.get("/admin/dashboard", headers=_auth(owner_token))).json()
    assert body["subscriptions"] == {"paid": 2, "trial": 1, "expiring_3_days": 1}
    week = body["last_7_days"]
    assert len(week) == 7
    assert week[-1]["revenue_inr"] == 99.0
    assert sum(day["revenue_inr"] for day in week) == 99.0  # the 10-day-old payment is excluded
    assert week[-1]["signups"] == 5
