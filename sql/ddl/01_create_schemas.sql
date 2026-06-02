-- Runs automatically on first container start (mounted into
-- /docker-entrypoint-initdb.d by docker-compose.yml).
--
-- ELT raw layer: store Spotify API payloads as-is (JSONB) and transform them
-- later, inside the warehouse. Keeping raw immutable + replayable means any
-- transformation bug can be fixed and re-run without re-hitting the API.

CREATE SCHEMA IF NOT EXISTS raw;

-- One row per play event.
CREATE TABLE IF NOT EXISTS raw.plays (
    ingested_at timestamptz NOT NULL DEFAULT now(),
    played_at   timestamptz,            -- pulled out for cheap idempotent loads
    payload     jsonb NOT NULL
);

-- One row per artist you've played (genres live in the payload).
CREATE TABLE IF NOT EXISTS raw.artists (
    ingested_at timestamptz NOT NULL DEFAULT now(),
    artist_id   text,
    payload     jsonb NOT NULL
);

-- Transform layer (SQL/dbt) builds the star schema into this schema:
-- dim_track, dim_artist, fact_plays.
CREATE SCHEMA IF NOT EXISTS analytics;
