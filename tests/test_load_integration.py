"""Integration tests: these talk to a real Postgres.

Excluded from the default run (see addopts in pyproject.toml). Enable with:

    docker compose up -d postgres
    TEST_DATABASE_URL=postgresql://du:du_local_only@localhost:5432/du \
        pytest -m integration
"""

import pytest

from ducks_unlimited.db import connection, init_schema
from ducks_unlimited.load import upsert_chapters
from ducks_unlimited.models import Chapter

pytestmark = pytest.mark.integration

CHAPTER = Chapter(
    chapter_id="CA-TEST",
    chapter_name="Test University",
    city="Testville",
    state="CA",
    latitude=35.0,
    longitude=-120.0,
)


@pytest.fixture
def conn():
    with connection() as c:
        init_schema(c)
        c.execute("DELETE FROM university_chapters WHERE chapter_id = 'CA-TEST'")
        yield c
        c.execute("DELETE FROM university_chapters WHERE chapter_id = 'CA-TEST'")


def test_upsert_inserts_a_new_chapter(conn):
    assert upsert_chapters(conn, [CHAPTER]) == 1
    row = conn.execute(
        "SELECT chapter_name, state FROM university_chapters WHERE chapter_id = 'CA-TEST'"
    ).fetchone()
    assert row == ("Test University", "CA")


def test_running_twice_does_not_duplicate(conn):
    """The job runs daily, so re-processing the same chapter must be a no-op."""
    upsert_chapters(conn, [CHAPTER])
    upsert_chapters(conn, [CHAPTER])
    count = conn.execute(
        "SELECT count(*) FROM university_chapters WHERE chapter_id = 'CA-TEST'"
    ).fetchone()[0]
    assert count == 1


def test_changed_values_are_updated_and_first_seen_is_preserved(conn):
    upsert_chapters(conn, [CHAPTER])
    original = conn.execute(
        "SELECT first_seen_at FROM university_chapters WHERE chapter_id = 'CA-TEST'"
    ).fetchone()[0]

    renamed = CHAPTER.model_copy(update={"chapter_name": "Renamed University"})
    upsert_chapters(conn, [renamed])

    name, first_seen = conn.execute(
        "SELECT chapter_name, first_seen_at FROM university_chapters "
        "WHERE chapter_id = 'CA-TEST'"
    ).fetchone()
    assert name == "Renamed University"
    assert first_seen == original, "first_seen_at must survive an update"


def test_empty_input_is_handled(conn):
    assert upsert_chapters(conn, []) == 0
