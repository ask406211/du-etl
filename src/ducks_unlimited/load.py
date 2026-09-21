"""LOAD: write Chapters into Postgres."""

import logging

import psycopg

from .models import Chapter

logger = logging.getLogger(__name__)

UPSERT = """
INSERT INTO university_chapters
    (chapter_id, chapter_name, city, state, latitude, longitude)
VALUES
    (%(chapter_id)s, %(chapter_name)s, %(city)s, %(state)s,
     %(latitude)s, %(longitude)s)
ON CONFLICT (chapter_id) DO UPDATE SET
    chapter_name    = EXCLUDED.chapter_name,
    city            = EXCLUDED.city,
    state           = EXCLUDED.state,
    latitude        = EXCLUDED.latitude,
    longitude       = EXCLUDED.longitude,
    last_updated_at = now()
"""


def upsert_chapters(conn: psycopg.Connection, chapters: list[Chapter]) -> int:
    """Insert or update chapters, keyed on chapter_id.

    The job runs daily, so it will process the same chapters repeatedly.
    Upserting keeps the run idempotent: running it twice leaves the same
    rows as running it once. first_seen_at is deliberately not touched,
    so it records when each chapter first appeared.
    """
    if not chapters:
        logger.warning("no chapters to load")
        return 0

    with conn.cursor() as cur:
        cur.executemany(UPSERT, [c.model_dump() for c in chapters])

    logger.info("upserted %d chapters", len(chapters))
    return len(chapters)
