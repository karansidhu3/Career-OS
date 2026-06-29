"""
Root test configuration. Sets required env vars before any app module is imported.

All app modules import app.config at module level, which instantiates Settings().
Settings requires DATABASE_URL — set it here so unit tests import cleanly without
a real database connection.

Integration tests read TEST_DATABASE_URL and override DATABASE_URL dynamically.
"""
import os

_test_db = os.environ.get("TEST_DATABASE_URL")
if _test_db:
    os.environ["DATABASE_URL"] = _test_db
else:
    # Placeholder keeps Settings() happy during unit test collection.
    # Integration tests will be skipped when TEST_DATABASE_URL is absent.
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/careeros_test_placeholder")

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("API_KEY", "")  # auth disabled by default in tests


import pytest


def pytest_collection_modifyitems(config, items):
    """Skip integration tests when no test database is configured."""
    if not os.environ.get("TEST_DATABASE_URL"):
        skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set — run with a real Postgres to enable")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
