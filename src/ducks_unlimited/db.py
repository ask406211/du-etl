"""Database connections and schema bootstrap.

The connection string carries the difference between environments, so no
code here branches on "local vs cloud":

    local      postgresql://du:pw@localhost:5432/du
    Cloud SQL  postgresql://du:pw@/du?host=/cloudsql/PROJECT:REGION:INSTANCE

The second form is a unix socket opened by Cloud Run's built-in Cloud SQL
connector, which avoids needing a VPC connector or a public database IP.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import files

import psycopg

from .config import get_settings

logger = logging.getLogger(__name__)

# Shipped as package data so it resolves the same way in an installed image.
SCHEMA_FILE = files("ducks_unlimited") / "sql" / "001_schema.sql"


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Yield a connection that commits on success and rolls back on error."""
    with psycopg.connect(get_settings().database_url) as conn:
        logger.debug("database connection opened")
        yield conn


def init_schema(conn: psycopg.Connection) -> None:
    """Apply the schema. Idempotent, so it is safe on every run."""
    conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
    logger.debug("schema applied")
