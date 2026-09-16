"""_prepare_asyncpg_url must make managed-Postgres connection strings (Neon, Supabase, ...)
safe for asyncpg, which understands neither `postgresql://` nor libpq-only query params."""
from app.db.session import _prepare_asyncpg_url


def test_neon_style_url_is_normalized():
    raw = (
        "postgresql://user:pass@ep-soft-glitter.us-east-2.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    cleaned, connect_args = _prepare_asyncpg_url(raw)

    assert cleaned.startswith("postgresql+asyncpg://")
    assert "sslmode" not in cleaned
    assert "channel_binding" not in cleaned
    assert connect_args == {"ssl": True}


def test_plain_local_url_passes_through_unchanged():
    raw = "postgresql+asyncpg://jobbot:jobbot@postgres:5432/jobbot"
    cleaned, connect_args = _prepare_asyncpg_url(raw)

    assert cleaned == raw
    assert connect_args == {}


def test_sslmode_disable_does_not_force_ssl():
    raw = "postgresql://user:pass@localhost/db?sslmode=disable"
    cleaned, connect_args = _prepare_asyncpg_url(raw)

    assert "sslmode" not in cleaned
    assert connect_args == {}


def test_other_query_params_are_preserved():
    raw = "postgresql://user:pass@host/db?sslmode=require&application_name=jobbot"
    cleaned, connect_args = _prepare_asyncpg_url(raw)

    assert "application_name=jobbot" in cleaned
    assert connect_args == {"ssl": True}
