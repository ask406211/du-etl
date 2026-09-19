"""Transform raw ArcGIS features into Chapter models.

Pure functions: no HTTP, no database. Everything here is unit-testable
against a saved API response in milliseconds.
"""

import logging

from pydantic import ValidationError

from .models import Chapter

logger = logging.getLogger(__name__)


def to_chapter(feature: dict) -> Chapter:
    """Convert one ArcGIS feature into a Chapter.

    Raises KeyError or ValidationError if the feature does not match the
    contract; callers decide whether that aborts the run.
    """
    attributes = feature["attributes"]
    geometry = feature.get("geometry") or {}

    return Chapter(
        chapter_id=str(attributes["ChapterID"]),
        chapter_name=attributes["University_Chapter"],
        city=attributes.get("City"),
        state=attributes["State"],
        latitude=geometry.get("y"),  # ArcGIS y = latitude
        longitude=geometry.get("x"),  # ArcGIS x = longitude
    )


def transform(features: list[dict], states: list[str]) -> list[Chapter]:
    """Convert and filter raw features, skipping any record that is malformed.

    A single bad record must not sink the daily run, but it must be visible
    in the logs rather than silently dropped.
    """
    wanted = {state.upper() for state in states}
    chapters: list[Chapter] = []
    skipped = 0

    for feature in features:
        try:
            chapter = to_chapter(feature)
        except (KeyError, ValidationError, TypeError):
            skipped += 1
            logger.warning("skipping malformed feature: %s", feature, exc_info=True)
            continue

        if chapter.state.upper() in wanted:
            chapters.append(chapter)

    logger.info(
        "transform complete: received=%d kept=%d skipped=%d states=%s",
        len(features),
        len(chapters),
        skipped,
        sorted(wanted),
    )
    return chapters
