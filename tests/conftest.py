"""Shared test setup: give every test a complete, fake environment.

Settings are read from the environment, so tests must supply one rather than
depending on a developer's local .env file.
"""

import os

import pytest

from du_etl.config import get_settings

API_URL = "https://example.test/query"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DU_FEATURE_SERVICE_URL", API_URL)
    # Integration tests need a real database; unit tests never connect,
    # so a placeholder is enough for them.
    monkeypatch.setenv(
        "DATABASE_URL",
        os.getenv("TEST_DATABASE_URL", "postgresql://user:pw@localhost:5432/du"),
    )
    monkeypatch.setenv("TARGET_STATES", "CA")
    get_settings.cache_clear()  # lru_cache would otherwise leak between tests
    yield
    get_settings.cache_clear()
