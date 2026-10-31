-- game_ddl.sql - Game state persistence (SF-PERSIST, ASR-1)
-- PostgreSQL schema; mirrors model.Game.to_dict() JSON payload.

CREATE TABLE IF NOT EXISTS games (
    id          TEXT PRIMARY KEY,
    game_state  JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger to keep updated_at current.
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_games_updated_at ON games;
CREATE TRIGGER trg_games_updated_at
    BEFORE UPDATE ON games
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
