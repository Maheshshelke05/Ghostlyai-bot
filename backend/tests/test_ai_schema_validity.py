"""Regression test for a real production bug: the google-genai SDK's response_schema
converter hard-rejects any Pydantic field with a default value ("Default value is not
supported in the response schema for the Gemini API"). Every Pydantic model used as a
Gemini response_schema had Optional[...] = None / Field(default_factory=...) defaults,
which meant every single AI call (resume parsing, category matching, AI-paste job
extraction) silently failed in production - caught by our own try/except and logged, so
the bot just looked like it "wasn't accepting resumes" with no visible error anywhere.

This calls the exact SDK function our GenerateContentConfig(response_schema=...) uses
internally (not a mock), so it fails the same way the real bug did if a default is ever
reintroduced on any of these models.
"""
import pytest
from google import genai
from google.genai import _transformers as t

from app.services.ai import CategoryMatch, JobDraft, JobDraftList, ResumeData

_client = genai.Client(api_key="fake-key-schema-conversion-is-local-only")


@pytest.mark.parametrize("model", [ResumeData, CategoryMatch, JobDraft, JobDraftList])
def test_response_schema_has_no_defaults(model):
    # No network call - this is the same schema-conversion step generate_content() runs
    # before ever contacting the API. Raises ValueError if any field has a default.
    schema = t.t_schema(_client, model)
    assert schema is not None
