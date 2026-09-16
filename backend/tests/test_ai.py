"""Gemini service: mocked client covering success, invalid JSON and exception paths."""
import json

from app.services import ai


class _FakeResponse:
    def __init__(self, parsed=None, text=""):
        self.parsed = parsed
        self.text = text


class _FakeModels:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    async def generate_content(self, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


class _FakeAio:
    def __init__(self, models):
        self.models = models


class _FakeClient:
    def __init__(self, models):
        self.aio = _FakeAio(models)


async def test_parse_resume_returns_none_on_exception(monkeypatch):
    monkeypatch.setattr(ai, "_get_client", lambda: _FakeClient(_FakeModels(exc=RuntimeError("boom"))))
    monkeypatch.setattr(ai.settings, "GEMINI_API_KEY", "fake-key")

    result = await ai.parse_resume(b"%PDF-1.4 fake", "application/pdf", {"other": "Other"})
    assert result is None


async def test_parse_resume_uses_parsed_when_available(monkeypatch):
    data = ai.ResumeData(is_resume=True, highest_education="B.Com", suggested_category_slugs=["accounts-finance", "other", "unknown-slug"])
    monkeypatch.setattr(ai, "_get_client", lambda: _FakeClient(_FakeModels(response=_FakeResponse(parsed=data))))
    monkeypatch.setattr(ai.settings, "GEMINI_API_KEY", "fake-key")

    result = await ai.parse_resume(b"%PDF-1.4 fake", "application/pdf", {"accounts-finance": "Accounts", "other": "Other"})
    assert result is not None
    assert result.highest_education == "B.Com"
    assert result.suggested_category_slugs == ["accounts-finance", "other"]  # unknown slug filtered out


async def test_parse_resume_falls_back_to_json_text(monkeypatch):
    payload = {"is_resume": True, "highest_education": "12th", "suggested_category_slugs": []}
    monkeypatch.setattr(
        ai, "_get_client",
        lambda: _FakeClient(_FakeModels(response=_FakeResponse(parsed=None, text=json.dumps(payload)))),
    )
    monkeypatch.setattr(ai.settings, "GEMINI_API_KEY", "fake-key")

    result = await ai.parse_resume(b"%PDF-1.4 fake", "application/pdf", {"other": "Other"})
    assert result is not None
    assert result.highest_education == "12th"


async def test_parse_resume_skipped_without_api_key(monkeypatch):
    monkeypatch.setattr(ai.settings, "GEMINI_API_KEY", "")
    result = await ai.parse_resume(b"data", "application/pdf", {"other": "Other"})
    assert result is None


async def test_map_category_rejects_unknown_slug(monkeypatch):
    monkeypatch.setattr(
        ai, "_get_client",
        lambda: _FakeClient(_FakeModels(response=_FakeResponse(parsed=ai.CategoryMatch(slug="not-real")))),
    )
    monkeypatch.setattr(ai.settings, "GEMINI_API_KEY", "fake-key")

    result = await ai.map_category("bank job", {"banking": "Banking"})
    assert result is None
