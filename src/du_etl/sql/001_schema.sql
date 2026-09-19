-- Idempotent schema bootstrap. Safe to run on every pipeline execution.
CREATE TABLE IF NOT EXISTS university_chapters (
    chapter_id      TEXT        PRIMARY KEY,           -- e.g. 'CA-0355', stable business key
    chapter_name    TEXT        NOT NULL,
    city            TEXT,
    state           CHAR(2)     NOT NULL,
    latitude        NUMERIC(9,6),                      -- geometry.y
    longitude       NUMERIC(9,6),                      -- geometry.x
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_university_chapters_state
    ON university_chapters (state);
