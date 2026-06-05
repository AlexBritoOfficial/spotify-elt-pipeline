# Where I left off / how to resume

_Last updated: 2026-06-04 — end of Phase 2._

## Status
- ✅ **Phase 1 complete.** Docker (Colima), repo scaffolded, Postgres 15 running, schemas + raw tables.
- ✅ **Phase 2 complete.**
  - OAuth refresh-token flow (`authorize.py`); token cached in `.cache`.
  - Recently-played → `raw.plays` (idempotent) — ~50 plays loaded.
  - **Genres via Last.fm** (Spotify removed `genres` for new apps): `artist.getTopTags` → `raw.artist_tags` (idempotent) — 53 artists enriched.
  - **Top tracks de-scoped on purpose** — `raw.plays` already supports top-N by play count. (Reflect this in the README Phase 2 line.)
- ⏭️ **Next: Phase 3 — dbt transforms (the resume priority).** Model `raw` → a clean star schema (`dim_track`, `dim_artist`, `fact_plays`) with tests. Clean the Last.fm folksonomy tags here (keep top-N by count, drop non-genre tags like `seen live`/`80s`, normalize case).

## Pick back up (start of session)
```bash
colima status                         # ensure "Running" (auto-starts at login)
cd ~/Documents/Development/SpotifyE2EPipeline
docker compose up -d                  # bring Postgres up
source .venv/bin/activate             # activate the virtualenv
docker compose exec postgres psql -U postgres -d spotify -c "SELECT COUNT(*) FROM raw.plays;"
```

## Current data state
- `raw.plays` — ~50 play events (raw JSONB).
- `raw.artist_tags` — 53 artists with Last.fm top tags (genre proxy), keyed by Spotify `artist_id` (joins back to `raw.plays`).
- Loader is idempotent — re-run anytime: `python -m src.load.load_to_postgres`.

## Key facts
- **Credentials** in `.env` (gitignored): Spotify Client ID / secret / refresh / redirect URI, and `LASTFM_API_KEY` (32 chars).
- **Deps** in `.venv`: spotipy, python-dotenv, psycopg2-binary, requests (`pip install -r requirements.txt` to rebuild).
- **Data persists** in Docker volume `spotifye2epipeline_postgres_data`. `docker compose down -v` WIPES it.
- **Git:** SSH remote, default branch `master`. `gh` CLI won't build on macOS 13 → create/merge PRs in the **browser**. Alex handles commits.
- **Uncommitted at wrap-up** — the Last.fm work (suggested branch `phase-2-lastfm-genres`): `src/extract/lastfm_client.py`, `load_artist_tags()` in `load_to_postgres.py`, `sql/ddl/02_artist_tags.sql`, `.env.example`, `requirements.txt`, and updated `docs/STAR-summary.md`.

## Docs
- `docs/STAR-summary.md` — interview STAR stories (incl. the Last.fm "routing around a constraint" story).
- `docs/phase-2-deep-dive.md` — self-study guide for Phase 2 topics.
- `docs/learning-notes.md` — session 1 recap.

## Useful commands
```bash
docker compose ps                     # is Postgres up?
docker compose stop                   # pause (keeps data)
python -m src.load.load_to_postgres   # re-run extract + load (idempotent)
```
