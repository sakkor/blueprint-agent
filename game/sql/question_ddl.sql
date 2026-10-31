-- question_ddl.sql - Question persistence (SF-PERSIST, ASR-1)
-- PostgreSQL schema aligned with model.Question fields.

CREATE TABLE IF NOT EXISTS questions (
    id              TEXT PRIMARY KEY,
    prompt          TEXT NOT NULL,
    options         TEXT[] NOT NULL,
    correct_answer  TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_questions_updated_at ON questions;
CREATE TRIGGER trg_questions_updated_at
    BEFORE UPDATE ON questions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
