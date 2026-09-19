"""LOAD: write Chapters into Postgres.

Write:
    upsert_chapters(conn, chapters: list[Chapter]) -> int
        - INSERT ... ON CONFLICT (chapter_id) DO UPDATE
        - one transaction: all rows land or none do
        - returns rows written
"""
