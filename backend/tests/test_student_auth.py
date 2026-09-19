"""Student app authentication: resume-first identity, then a real password.

Flow under test: POST /resume (extract identity, no token) -> POST /set-password (using the
short-lived signup_token) -> POST /login (phone/email + password, issues the real access_token)."""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import User
from app.services import ratelimit
from app.services.ai import ResumeData
from app.services.auth import create_token

from tests.conftest import make_user


def _resume(
    *,
    is_resume: bool = True,
    full_name: str | None = "Rahul Sharma",
    phone: str | None = "9876500001",
    email: str | None = "rahul@example.com",
    highest_education: str | None = "B.Com",
    course: str | None = None,
    skills: list[str] | None = None,
    experience_years: float = 0,
    city_or_district: str | None = None,
    summary: str | None = "Fresher, good with numbers.",
    suggested_category_slugs: list[str] | None = None,
) -> ResumeData:
    return ResumeData(
        is_resume=is_resume,
        full_name=full_name,
        phone=phone,
        email=email,
        highest_education=highest_education,
        course=course,
        skills=skills or [],
        experience_years=experience_years,
        city_or_district=city_or_district,
        summary=summary,
        suggested_category_slugs=suggested_category_slugs or [],
    )


def _fake_parse_resume(result: ResumeData):
    async def _parse(data: bytes, mime: str, categories: dict[str, str]) -> ResumeData:
        return result

    return _parse


def _resume_file(name: str = "resume.pdf") -> dict:
    return {"file": (name, b"%PDF-1.4 fake resume bytes", "application/pdf")}


async def _fake_save_resume(*args, **kwargs) -> str:
    return "local/resume.pdf"


async def _student_headers(user) -> dict:
    token = create_token(user.id, "student")
    return {"Authorization": f"Bearer {token}"}


async def _upload_resume(client, monkeypatch, resume: ResumeData, full_name: str | None = None):
    monkeypatch.setattr("app.services.resume_intake.ai.parse_resume", _fake_parse_resume(resume))
    monkeypatch.setattr("app.services.resume_intake.storage.save_resume", _fake_save_resume)
    data = {"full_name": full_name} if full_name else {}
    return await client.post("/student/auth/resume", data=data, files=_resume_file())


async def _signup_and_login(
    client, monkeypatch, phone: str | None, password: str = "testpass123", identifier: str | None = None
) -> str:
    """Full happy path: upload resume -> set password -> log in. Returns the access_token."""
    resp = await _upload_resume(client, monkeypatch, _resume(phone=phone))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["needs_login"] is False

    resp = await client.post(
        "/student/auth/set-password",
        json={"password": password},
        headers={"Authorization": f"Bearer {body['signup_token']}"},
    )
    assert resp.status_code == 200, resp.text
    set_pw = resp.json()

    resp = await client.post(
        "/student/auth/login",
        json={"identifier": identifier or set_pw["phone"] or set_pw["email"], "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def test_signup_new_user_extracts_identity_and_issues_signup_token(client, categories, monkeypatch):
    resp = await _upload_resume(
        client, monkeypatch, _resume(phone="9876500001", suggested_category_slugs=["it-software"])
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_new_user"] is True
    assert body["needs_login"] is False
    assert body["signup_token"]
    assert body["phone"] == "+919876500001"
    assert body["full_name"] == "Rahul Sharma"
    assert body["email"] == "rahul@example.com"
    assert body["suggested_category_slugs"] == ["it-software"]


async def test_signup_sets_app_seen_at_for_admin_visibility(client, db, categories, monkeypatch):
    """app_seen_at is the only reliable "used the app" signal for admin - it must be set on
    both brand-new signups and existing Telegram users recognized by phone, and once set,
    never cleared by a later signup."""
    telegram_user = await make_user(db, phone="+919876500013", status="active", category_slugs=["it-software"])
    from app.services.access import start_trial

    await start_trial(db, telegram_user)
    await db.commit()
    assert telegram_user.app_seen_at is None

    resp = await _upload_resume(client, monkeypatch, _resume(phone="9876500013"))
    assert resp.status_code == 200, resp.text

    await db.refresh(telegram_user)
    assert telegram_user.app_seen_at is not None
    assert telegram_user.telegram_id is not None  # still a Telegram user too - both true now


async def test_signup_prefers_app_typed_name_over_resume_extraction(client, categories, monkeypatch):
    resp = await _upload_resume(
        client, monkeypatch, _resume(phone="9876500011", full_name="Resume Name"), full_name="Typed Name"
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Typed Name"


async def test_signup_fills_missing_name_for_recognized_telegram_user(client, db, categories, monkeypatch):
    user = await make_user(db, phone="+919876500012", status="active", full_name=None, category_slugs=["it-software"])
    from app.services.access import start_trial

    await start_trial(db, user)
    await db.commit()

    resp = await _upload_resume(
        client, monkeypatch, _resume(phone="9876500012"), full_name="Filled In Name"
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Filled In Name"


async def test_signup_existing_telegram_user_is_recognized_instantly(client, db, categories, monkeypatch):
    user = await make_user(db, phone="+919876500002", status="active", category_slugs=["it-software"])
    from app.services.access import start_trial

    await start_trial(db, user)
    await db.commit()

    resp = await _upload_resume(
        client, monkeypatch, _resume(phone="9876500002", full_name="Different Name On Resume")
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_new_user"] is False
    assert body["needs_login"] is False  # no password yet - first time using the app

    # Logging in lands them straight on "done" - categories/job-types already set via Telegram.
    resp = await client.post(
        "/student/auth/set-password",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {body['signup_token']}"},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/student/auth/login", json={"identifier": "+919876500002", "password": "testpass123"}
    )
    assert resp.status_code == 200, resp.text
    login_body = resp.json()
    assert login_body["user"]["id"] == user.id
    assert login_body["next_step"] == "done"


async def test_signup_already_has_password_returns_needs_login(client, categories, monkeypatch):
    token = await _signup_and_login(client, monkeypatch, "9876500014")

    # Re-uploading the resume must not silently offer a fresh signup_token (that would let
    # anyone with the resume "sign up again" and get a new signup path) - it should point back
    # to Login instead.
    resp = await _upload_resume(client, monkeypatch, _resume(phone="9876500014"))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["needs_login"] is True
    assert body.get("signup_token") is None
    assert token  # sanity: the original login token is unaffected


async def test_signup_rejects_non_resume_file(client, categories, monkeypatch):
    resp = await _upload_resume(client, monkeypatch, _resume(is_resume=False))
    assert resp.status_code == 422


async def test_signup_rejects_unsupported_file_type(client, categories):
    resp = await client.post(
        "/student/auth/resume", files={"file": ("resume.exe", b"not a resume", "application/octet-stream")}
    )
    assert resp.status_code == 400


async def test_signup_with_no_phone_in_resume_still_creates_account(client, categories, monkeypatch):
    resp = await _upload_resume(client, monkeypatch, _resume(phone=None, email=None))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_new_user"] is True
    assert body["phone"] is None
    assert body["email"] is None


async def test_signup_blocked_user_is_refused(client, db, monkeypatch):
    user = await make_user(db, phone="+919876500003", status="blocked")
    await db.commit()

    resp = await _upload_resume(client, monkeypatch, _resume(phone="9876500003"))
    assert resp.status_code == 403


async def test_set_password_requires_phone_when_resume_had_neither(client, categories, monkeypatch):
    resp = await _upload_resume(client, monkeypatch, _resume(phone=None, email=None))
    assert resp.status_code == 200, resp.text
    signup_token = resp.json()["signup_token"]
    headers = {"Authorization": f"Bearer {signup_token}"}

    resp = await client.post("/student/auth/set-password", json={"password": "testpass123"}, headers=headers)
    assert resp.status_code == 400  # nothing to log in with afterward

    resp = await client.post(
        "/student/auth/set-password",
        json={"password": "testpass123", "phone": "9876500020"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["phone"] == "+919876500020"


async def test_set_password_rejects_short_password(client, categories, monkeypatch):
    resp = await _upload_resume(client, monkeypatch, _resume(phone="9876500021"))
    signup_token = resp.json()["signup_token"]
    resp = await client.post(
        "/student/auth/set-password",
        json={"password": "short"},
        headers={"Authorization": f"Bearer {signup_token}"},
    )
    assert resp.status_code == 422


async def test_set_password_rejects_a_full_access_token(client, categories, monkeypatch):
    """The signup_token role check must be exact - a real (post-login) access_token must not
    also work here, since that would let anyone with a normal session silently reset their own
    password without re-proving identity via a fresh resume upload."""
    token = await _signup_and_login(client, monkeypatch, "9876500022")
    resp = await client.post(
        "/student/auth/set-password",
        json={"password": "newpassword1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_login_with_phone_and_correct_password(client, categories, monkeypatch):
    token = await _signup_and_login(client, monkeypatch, "9876500023", password="correcthorse")
    assert token


async def test_login_with_email_identifier(client, categories, monkeypatch):
    resp = await _upload_resume(client, monkeypatch, _resume(phone="9876500024", email="Student.Email@Example.com"))
    signup_token = resp.json()["signup_token"]
    await client.post(
        "/student/auth/set-password",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {signup_token}"},
    )
    # Case-insensitive on purpose - Gemini extracts the email exactly as written in the resume.
    resp = await client.post(
        "/student/auth/login",
        json={"identifier": "STUDENT.EMAIL@EXAMPLE.COM", "password": "testpass123"},
    )
    assert resp.status_code == 200, resp.text


async def test_login_wrong_password_is_rejected(client, categories, monkeypatch):
    ratelimit.reset_all()
    await _signup_and_login(client, monkeypatch, "9876500025", password="correctpassword")
    resp = await client.post(
        "/student/auth/login", json={"identifier": "+919876500025", "password": "wrongpassword"}
    )
    assert resp.status_code == 401


async def test_login_unknown_identifier_is_rejected(client, categories):
    ratelimit.reset_all()
    resp = await client.post(
        "/student/auth/login", json={"identifier": "+919999999999", "password": "whatever1"}
    )
    assert resp.status_code == 401


async def test_login_rate_limited_after_repeated_failures(client, categories, monkeypatch):
    ratelimit.reset_all()
    await _signup_and_login(client, monkeypatch, "9876500026", password="correctpassword")
    for _ in range(ratelimit.MAX_FAILURES):
        resp = await client.post(
            "/student/auth/login", json={"identifier": "+919876500026", "password": "wrongpassword"}
        )
        assert resp.status_code == 401
    resp = await client.post(
        "/student/auth/login", json={"identifier": "+919876500026", "password": "wrongpassword"}
    )
    assert resp.status_code == 429


async def test_login_blocked_user_is_refused(client, db, monkeypatch):
    ratelimit.reset_all()
    token = await _signup_and_login(client, monkeypatch, "9876500027", password="testpass123")
    assert token
    user = (await db.execute(select(User).where(User.phone == "+919876500027"))).scalar_one()
    user.status = "blocked"
    await db.commit()

    resp = await client.post(
        "/student/auth/login", json={"identifier": "+919876500027", "password": "testpass123"}
    )
    assert resp.status_code == 403


async def _signup(client, monkeypatch, phone: str | None) -> str:
    """Back-compat helper for tests below that just need a logged-in student token."""
    return await _signup_and_login(client, monkeypatch, phone)


async def test_onboarding_straight_to_complete_no_district(client, categories, monkeypatch):
    token = await _signup(client, monkeypatch, "9876500004")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/student/auth/me", headers=headers)
    assert resp.json()["next_step"] == "profile"  # name already came from the resume, no district step

    cat_id = categories["it-software"].id
    resp = await client.post(
        "/student/me/complete",
        json={"category_ids": [cat_id], "job_types": ["private", "wfh"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["next_step"] == "done"
    assert body["user"]["status"] == "active"


async def test_set_name_used_when_resume_had_none(client, categories, monkeypatch):
    token = await _signup(client, monkeypatch, "9876500005")
    headers = {"Authorization": f"Bearer {token}"}
    # simulate a resume with no usable name: re-signup wouldn't apply here since token already
    # exists, so exercise PUT /student/me/name directly instead.
    resp = await client.put("/student/me/name", json={"full_name": "Solo"}, headers=headers)
    assert resp.status_code == 400  # valid_name() requires first + last name

    resp = await client.put("/student/me/name", json={"full_name": "Anita Patil"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["user"]["full_name"] == "Anita Patil"


async def test_set_phone_manual_fallback(client, categories, monkeypatch):
    # phone was None in the resume and set-password required one there - PUT /student/me/phone
    # is the separate, already-logged-in path for changing it again afterward.
    resp = await _upload_resume(client, monkeypatch, _resume(phone=None, email=None))
    signup_token = resp.json()["signup_token"]
    resp = await client.post(
        "/student/auth/set-password",
        json={"password": "testpass123", "phone": "9876500006"},
        headers={"Authorization": f"Bearer {signup_token}"},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/student/auth/login", json={"identifier": "+919876500006", "password": "testpass123"}
    )
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.put("/student/me/phone", json={"phone": "9876500028"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["phone"] == "+919876500028"


async def test_set_phone_rejects_number_already_taken(client, db, categories, monkeypatch):
    other = await make_user(db, phone="+919876500007")
    await db.commit()

    token = await _signup(client, monkeypatch, "9876500029")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put("/student/me/phone", json={"phone": "9876500007"}, headers=headers)
    assert resp.status_code == 400


async def test_complete_onboarding_requires_name_first(client, monkeypatch):
    resp = await _upload_resume(client, monkeypatch, _resume(full_name=None, phone="9876500008"))
    signup_token = resp.json()["signup_token"]
    await client.post(
        "/student/auth/set-password",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {signup_token}"},
    )
    resp = await client.post(
        "/student/auth/login", json={"identifier": "+919876500008", "password": "testpass123"}
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.post(
        "/student/me/complete", json={"category_ids": [1], "job_types": []}, headers=headers
    )
    assert resp.status_code == 400  # name still missing


async def test_complete_onboarding_enforces_max_categories(client, categories, monkeypatch):
    token = await _signup(client, monkeypatch, "9876500009")
    headers = {"Authorization": f"Bearer {token}"}

    all_ids = [c.id for c in categories.values()][:4]
    resp = await client.post(
        "/student/me/complete", json={"category_ids": all_ids, "job_types": []}, headers=headers
    )
    assert resp.status_code == 400
    assert "Pick 1 to 3" in resp.json()["detail"]


async def test_push_token_set_and_clear(client, categories, monkeypatch):
    token = await _signup(client, monkeypatch, "9876500010")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put("/student/me/push-token", json={"token": "ExponentPushToken[abc]"}, headers=headers)
    assert resp.status_code == 200
    resp = await client.put("/student/me/push-token", json={"token": None}, headers=headers)
    assert resp.status_code == 200


async def test_unauthenticated_request_is_rejected(client):
    resp = await client.get("/student/auth/me")
    assert resp.status_code == 401
    resp = await client.put("/student/me/name", json={"full_name": "X Y"})
    assert resp.status_code == 401


async def test_admin_token_cannot_be_used_as_student_token(client, owner_token):
    resp = await client.get("/student/auth/me", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 401


async def test_public_meta_endpoints(client, categories):
    resp = await client.get("/student/categories")
    assert resp.status_code == 200
    assert len(resp.json()) == len(categories)

    resp = await client.get("/student/settings")
    assert resp.status_code == 200
    assert resp.json()["price_inr"] == 99
