"""Entry point. Reads top to bottom like the README: extract, transform, load."""

import json
import logging
import sys
import time

from .config import get_settings
from .db import connection, init_schema
from .extract import fetch_chapters
from .load import upsert_chapters
from .transform import transform

logger = logging.getLogger("du_etl")


class JsonFormatter(logging.Formatter):
    """One JSON object per line, so Cloud Logging parses fields automatically."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)


def run() -> int:
    """Execute one pipeline run. Returns a process exit code."""
    settings = get_settings()
    configure_logging(settings.log_level)
    started = time.monotonic()

    logger.info("pipeline starting for states=%s", settings.states)
    try:
        features = fetch_chapters(settings.states)
        chapters = transform(features, settings.states)
        with connection() as conn:
            init_schema(conn)
            loaded = upsert_chapters(conn, chapters)
    except Exception:
        # Log the traceback and exit non-zero: Cloud Run Jobs treats a
        # non-zero exit as a failed execution, which is what alerts on.
        logger.exception("pipeline failed")
        return 1

    logger.info(
        "pipeline succeeded fetched=%d loaded=%d duration_s=%.2f",
        len(features),
        loaded,
        time.monotonic() - started,
    )
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
