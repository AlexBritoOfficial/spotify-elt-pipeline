# Learning notes — Session 1 (2026-06-02)

A plain-language recap of everything set up on day one, plus things to review.

---

## What we did, in order

### 1. Couldn't install Docker Desktop → used Colima
- This Mac runs **macOS 13 (Ventura)** on an **Intel** chip. Current Docker Desktop needs macOS 14+, so it wouldn't install.
- Installed **Colima** instead — a free, open-source Docker engine that works on this OS. `docker` and `docker compose` work identically; there's just no GUI.
- Set it to **auto-start at login** so Docker is always ready.

### 2. Connected to the GitHub repo
- The repo's existing **README** (an ELT design) became the source of truth.
- Restructured to match it: `src/extract`, `src/load`, `src/transform`, `sql/ddl`, `tests/`.
- Switched the git remote from HTTPS to **SSH** (SSH key works; no saved HTTPS token).

### 3. A real security incident — and the fix
- A live **Spotify Client Secret** got committed into `.env.example` and reached GitHub via a merged pull request.
- Fix: removed it from files + history, **rotated** the secret in the Spotify dashboard (the step that actually closes the hole), force-pushed a clean `master`.
- Real credentials now live only in `.env`, which is **gitignored**.

### 4. Completed Phase 1
- Brought up **Postgres 15** in Docker; it auto-ran `sql/ddl` to create the `raw` + `analytics` schemas and `raw.plays` / `raw.artists` tables.
- Verified with `SELECT 1`, ticked the Phase 1 boxes in the README, pushed.

---

## Things to review on my own

### Docker & Colima
- A **container** vs. a normally-installed app (isolated, reproducible, disposable).
- **Image** (the blueprint) vs. **container** (a running instance).
- What `docker compose up -d` does; what `-d` (detached) means.
- `docker compose stop` vs `down` vs `down -v` — and why `-v` deletes data.
- Colima must be running for any `docker` command (`colima status`).

### Git & GitHub
- The flow: edit → `git add` → `git commit` → `git push`.
- **Branch**, **pull request**, and how **merging a PR changes the target branch** (how the secret reached `master`).
- **HTTPS vs SSH** remotes for authentication.
- What `.gitignore` does; why secrets must never be committed.
- What a **force-push** is (rewrites history) — powerful but risky.

### Secrets management (most important)
- `.env` = real secrets, gitignored, never committed. `.env.example` = placeholders only.
- Once a secret hits a remote, treat it as **permanently compromised** — deleting from git isn't enough; **rotating** is the only real fix.

### Postgres & the design
- What a **schema** is (`raw` vs `analytics`) and why separate them.
- **ELT vs ETL**: load raw first, transform inside the database; keep raw replayable.
- What **JSONB** is and why raw API responses land there.
- How files in `sql/ddl/` run automatically on first DB start (`docker-entrypoint-initdb.d`).

### Project structure
- `src/{extract,load,transform}` maps to the three pipeline stages.
- Where things live: `docker-compose.yml` (infra), `requirements.txt` (deps), `tests/` (checks).

---

## Next session
- **Phase 2: OAuth + Extract + Load** — the OAuth refresh-token step is the tricky one.
- Postgres data persists in its Docker volume, so nothing is lost between sessions.
- See `docs/RESUME.md` for exact resume commands.
