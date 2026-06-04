# Where I left off / how to resume

_Last updated: 2026-06-02 — end of Phase 1._

## Status
- ✅ **Phase 1 complete.** Docker (via Colima) installed, repo scaffolded, Postgres 15 running, `SELECT 1` passes, schemas + raw tables created.
- ⏭️ **Next: Phase 2 — Extract & Load** (Spotify OAuth → recently-played → land in `raw.plays`). The trickiest part is the OAuth refresh-token step; go slow there.

## How to pick back up (start of a work session)
```bash
# 1. Colima auto-starts at login, but if Docker commands fail, start it:
colima status        # should say "Running"
colima start         # if it isn't

# 2. Go to the project and bring Postgres up
cd ~/Documents/Development/SpotifyE2EPipeline
docker compose up -d

# 3. Sanity check the database
docker compose exec postgres psql -U postgres -d spotify -c "SELECT 1;"
```

## Key facts to remember
- **Credentials** live in `.env` (gitignored — never committed). Client ID + rotated secret are already filled in.
- **Data persists** in a Docker volume (`spotifye2epipeline_postgres_data`) between sessions. `docker compose stop` is safe; `docker compose down -v` WIPES the data.
- **Git remote uses SSH** (`git@github.com:AlexBritoOfficial/spotify-elt-pipeline.git`). Default branch is `master`.
- **Structure source of truth = the README** (ELT, `src/{extract,load,transform}`). The `PLAN.md` 14-day plan is kept local only.

## Phase 2 starting points (stubs already in place)
- `src/extract/authorize.py` — one-time OAuth flow, caches a refresh token.
- `src/extract/spotify_client.py` — wrappers for recently-played + artists.
- `src/load/load_to_postgres.py` — insert payloads into `raw.plays` / `raw.artists` (idempotent).

## Useful commands
```bash
docker compose ps                 # is Postgres up?
docker compose logs postgres      # database logs
docker compose stop               # pause (keeps data)
docker compose down               # remove container (data persists in volume)
```
