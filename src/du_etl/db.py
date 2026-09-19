"""Connection handling and schema bootstrap.

Write:
    connection() -> contextmanager yielding a psycopg connection
        - local: host/port from settings
        - Cloud Run: host is the unix socket path /cloudsql/<connection_name>
    init_schema(conn) -> None   # executes sql/001_schema.sql, idempotent
"""
