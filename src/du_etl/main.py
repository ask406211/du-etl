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
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    logging.basicConfig(
        level=level.upper(),
        handlers=[handler],
        force=True,
    )


def run() -> int:
    
    settings = get_settings()
    configure_logging(settings.log_level)

    start_time = time.monotonic()

    logger.info(
        "pipeline starting for states=%s",
        settings.states,
    )

    try:
        # Extract
        features = fetch_chapters(settings.states)

        # Transform
        chapters = transform(
            features,
            settings.states,
        )

        # Load
        with connection() as conn:
            init_schema(conn)
            loaded = upsert_chapters(
                conn,
                chapters,
            )

    except Exception:
        # A non-zero exit code tells Cloud Run Jobs that the execution failed.
        logger.exception("pipeline failed")
        return 1

    duration = time.monotonic() - start_time

    logger.info(
        "pipeline succeeded fetched=%d loaded=%d duration_s=%.2f",
        len(features),
        loaded,
        duration,
    )

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()