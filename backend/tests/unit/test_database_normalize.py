"""Unit tests for app.database._normalize — the DATABASE_URL/APP_DATABASE_URL
rewrite applied before handing a connection string to asyncpg."""
from app.database import _normalize


def test_rewrites_postgres_scheme_to_asyncpg_dialect():
    assert _normalize("postgres://u:p@host/db").startswith("postgresql+asyncpg://")


def test_rewrites_postgresql_scheme_to_asyncpg_dialect():
    assert _normalize("postgresql://u:p@host/db").startswith("postgresql+asyncpg://")


def test_leaves_url_without_scheme_rewrite_untouched():
    assert _normalize("postgresql+asyncpg://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"


def test_translates_sslmode_to_ssl_for_asyncpg():
    # asyncpg's connect() has no `sslmode` kwarg — only `ssl` — and raises
    # TypeError if sslmode is passed through untranslated (e.g. Neon's
    # connection strings, which include `?sslmode=require` by default).
    result = _normalize("postgresql://u:p@host/db?sslmode=require")
    assert "sslmode=" not in result
    assert "ssl=require" in result


def test_no_sslmode_param_is_a_noop():
    assert _normalize("postgresql://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"
