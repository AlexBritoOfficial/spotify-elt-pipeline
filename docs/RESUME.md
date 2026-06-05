# Where I left off / how to resume

_Last updated: 2026-06-05 — v1 complete (Phases 1–4)._

## Status
- ✅ **Phase 1 complete.** Docker (Colima), repo scaffolded, Postgres 15 running, schemas + raw tables.
- ✅ **Phase 2 complete.**
  - OAuth refresh-token flow (`authorize.py`); token cached in `.cache`.
  - Recently-played → `raw.plays` (idempotent) — ~50 plays loaded.
  - **Genres via Last.fm** (Spotify removed `genres` for new apps): `artist.getTopTags` → `raw.artist_tags` (idempotent) — 53 artists enriched.
  - **Top tracks de-scoped on purpose** — `raw.plays` already supports top-N by play count. (Reflect this in the README Phase 2 line.)
- ✅ **Phase 3 complete — dbt transforms.** dbt project at top-level `dbt/` models `raw` → the `analytics` star schema with **33 passing tests**.
  - Layers: `stg_plays` / `stg_artist_tags` (views) → `int_artist_genres` (folksonomy cleanup) → marts `dim_artist`, `dim_track`, `dim_genre`, `dim_date`, `bridge_artist_genre`, `fact_plays`.
  - **Genre cleaning** (`int_artist_genres`): normalize case/punct → dedupe (max count) → denylist seed + regex (drop decades/numbers/own-name) → top-N (`max_genres_per_artist`, default 3).
  - **Genres modeled as a bridge** (many-to-many): `dim_artist` ⋈ `bridge_artist_genre` ⋈ `dim_genre`.
  - `dim_artist` is the **union** of play-artists + tag-artists (53 tagged > 50 plays = featured/album artists), so the bridge never orphans — relationship tests prove it.
  - Surrogate keys via plain `md5()` (no `dbt_utils` — avoids `dbt deps` network installs on this SSL-finicky machine).
  - Full walkthrough: **`docs/phase-3-deep-dive.md`**.
- ✅ **Phase 4 complete — Operate & Present.**
  - `run_pipeline.sh` — one-command, idempotent: Postgres up → extract+load → `dbt build` (run + test). PATH-hardened + Colima auto-start guard for cron.
  - **Scheduled live**: cron entry `0 8 * * * cd <repo> && ./run_pipeline.sh >> pipeline.log 2>&1` (`crontab -l` to view). NOTE: macOS may need Full Disk Access for `cron`, and the Mac must be awake at run time.
  - **Real pytest suite** (replaced the placeholder): `tests/test_lastfm_client.py` (mocked units, incl. key-leak check) + `tests/test_load_idempotency.py` (DB integration). `pip install -r requirements.txt` to get pytest in the venv.
  - `dbt docs generate` lineage; sample analytics in `sql/analysis/insights.sql` → `docs/insights.md`.
  - `dim_date` added (365 rows) with `fact_plays.date_key` FK + relationship test.
  - **Metabase BI** added to `docker-compose.yml` (port 3000, H2 app db in `metabase_data` volume) → `http://localhost:3000`. Dashboard built in-browser; connect to Postgres with host **`postgres`** (compose service name, not localhost). Guide: `docs/metabase-setup.md`. TODO: build charts + screenshot into README.
- 🎉 **v1 complete.** Stretch ideas: hosted dashboard; backfill more history; orchestrator (Airflow/Dagster); incremental models.

## Pick back up (start of session)
```bash
colima status                         # ensure "Running" (auto-starts at login)
cd ~/Documents/Development/SpotifyE2EPipeline
docker compose up -d                  # bring Postgres up
source .venv/bin/activate             # activate the virtualenv
docker compose exec postgres psql -U postgres -d spotify -c "SELECT COUNT(*) FROM raw.plays;"

# Rebuild the analytics layer (Phase 3, idempotent):
cd dbt
export DBT_SEND_ANONYMOUS_USAGE_STATS=False   # avoids telemetry SSL noise
dbt seed --profiles-dir . && dbt run --profiles-dir . && dbt test --profiles-dir .
```

## Current data state
- `raw.plays` — ~50 play events (raw JSONB).
- `raw.artist_tags` — 53 artists with Last.fm top tags (genre proxy), keyed by Spotify `artist_id` (joins back to `raw.plays`).
- Loader is idempotent — re-run anytime: `python -m src.load.load_to_postgres`.
- **`analytics` star schema** (built by dbt, rebuilds idempotently): `fact_plays` (50), `dim_track` (49), `dim_artist` (51), `dim_genre` (41), `dim_date` (365), `bridge_artist_genre` (147), plus the `stg_*` / `int_*` views.

## Key facts
- **Credentials** in `.env` (gitignored): Spotify Client ID / secret / refresh / redirect URI, and `LASTFM_API_KEY` (32 chars).
- **Deps** in `.venv`: spotipy, python-dotenv, psycopg2-binary, requests, **dbt-core/dbt-postgres pinned to `1.10.*`** (bare `dbt-postgres` pulls a dbt-core 2.0 alpha — keep the pin). `pip install -r requirements.txt` to rebuild.
- **Data persists** in Docker volume `spotifye2epipeline_postgres_data`. `docker compose down -v` WIPES it.
- **Git:** SSH remote, default branch `master`. `gh` CLI won't build on macOS 13 → create/merge PRs in the **browser**. Alex handles commits.
- **Uncommitted at wrap-up** — Phase 3 + 4 (suggested branch `phase-3-dbt-transforms`): the whole `dbt/` project, `run_pipeline.sh`, `sql/analysis/insights.sql`, `tests/test_lastfm_client.py` + `tests/test_load_idempotency.py` (deleted `tests/test_smoke.py`), `docs/{phase-3-deep-dive,insights,metabase-setup}.md`, Metabase service in `docker-compose.yml`, updated `README.md` / `STAR-summary.md` / `src/transform/README.md`, pinned `requirements.txt`, and this `docs/RESUME.md`. (Cron entry lives in `crontab`, not the repo.)

## Docs
- `docs/STAR-summary.md` — interview STAR stories (incl. the Last.fm "routing around a constraint" story).
- `docs/phase-2-deep-dive.md` — self-study guide for Phase 2 topics.
- `docs/phase-3-deep-dive.md` — full Phase 3 (dbt / star schema) walkthrough + every-file reference.
- `docs/learning-notes.md` — session 1 recap.

## Useful commands
```bash
docker compose ps                     # is Postgres up?
docker compose stop                   # pause (keeps data)
python -m src.load.load_to_postgres   # re-run extract + load (idempotent)
```
