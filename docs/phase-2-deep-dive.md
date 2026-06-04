# Phase 2 — Deep-Dive Study Guide

What this iteration covered, with enough depth to study each topic on your own.
Each section: **WHAT we did → 
                HOW it works → 
                WHY it matters → 
                DIG DEEPER**
(questions to research). Code references point at the files in this repo.

---

## 1. Python virtual environments (`.venv`)

**WHAT** 

1) Created `.venv` with `python3 -m venv .venv`, activated it.
2) Installed `spotipy`, `python-dotenv`, `psycopg2-binary` into it.

**HOW** 
A venv is a self-contained directory with its own `python`,`pip`, and `site-packages`. 
Activating it (`source .venv/bin/activate`) just prepends `.venv/bin` to your `PATH`, so `python` resolves to the venv's
interpreter. Packages install into the venv, isolated from system Python.

**WHY** 
Reproducibility and isolation — this project's dependencies can't clash with another project's or with system tools.

**The bug we hit (worth understanding deeply):** `ModuleNotFoundError: psycopg2`
even though we'd installed it. Cause: the file was run by a *different* Python
(`/Library/Frameworks/.../python3`) than the venv. A venv only applies if you
activate it **or** call its python directly (`.venv/bin/python`). PyCharm's Run
button uses *its configured interpreter*, which must be pointed at `.venv`.

**Dig deeper.**
- What's the difference between `venv`, `virtualenv`, `conda`, and `pipenv`/`poetry`?
- What does `sys.executable` tell you, and why is `which python` useful?
- How does `PATH` resolution actually pick which `python` runs?

---

## 2. Environment variables & `python-dotenv`

**What we did.** Loaded secrets/config from `.env` with `load_dotenv()` +
`os.getenv("KEY")`. See `src/extract/authorize.py`, `spotify_client.py`.

**How it works.** `load_dotenv()` reads `.env` and injects the keys into the
process's environment; `os.getenv("X")` reads them back. Missing keys return
**`None`** — no error.

**Why it matters.** Secrets stay out of code (and out of git). Config differs per
environment without code changes.

**The bugs we hit:**
- `os.getenv("SECRET")` when the key was `SPOTIFY_CLIENT_SECRET` → returned
  `None` *silently*. Lesson: the **string** must match the `.env` key exactly.
- A guard typo (`x or not x`) and a missing `not` — logic bugs that either never
  fire or always fire. Lesson: write guards that **fail loud** when config is
  missing (`raise RuntimeError(...)`).

**Dig deeper.**
- Why are env vars preferred over a config file for secrets? (12-Factor App)
- What's the difference between process env vars and shell exports?
- How would this change in a container or CI (no `.env` file present)?

---

## 3. OAuth 2.0 — Authorization Code flow

**What we did.** Ran a one-time browser authorization (`authorize.py`) that
produced a cached token in `.cache`.

**How it works (the mental model).**
1. Your **app** has a Client ID + Secret and a registered **Redirect URI**.
2. The user is sent to Spotify to approve specific **scopes** (permissions).
3. Spotify redirects back to `127.0.0.1:8888/callback?code=...` with a one-time
   **authorization code**.
4. The app exchanges that code for an **access token** (short-lived, ~1 hr) and a
   **refresh token** (long-lived).
5. The refresh token silently mints new access tokens forever after — no browser.

**Why it matters.** This is *the* standard way apps act on a user's behalf
without ever seeing their password. The refresh token is what makes automation
(a daily pipeline) possible.

**Details we ran into:**
- **Redirect URI must match exactly** — we used `http://127.0.0.1:8888/callback`.
  Spotify is deprecating `localhost` in favor of the loopback IP `127.0.0.1`.
- **Scopes** = least privilege: we asked only for
  `user-read-recently-played user-top-read`.

**Dig deeper.**
- Access token vs refresh token vs ID token — what's each for?
- What is PKCE and when is it required (public vs confidential clients)?
- Why must the redirect URI be pre-registered? (open redirect attacks)
- Where is the refresh token stored here, and why must that file be gitignored?

---

## 4. `spotipy` (the Spotify client library)

**What we did.** Used `SpotifyOAuth` (auth manager) + `Spotify` (API client);
called `current_user_recently_played()` and `artists()`.

**How it works.** `SpotifyOAuth` handles the token lifecycle (cache, refresh).
`Spotify(auth_manager=...)` injects valid tokens into each request automatically.

**Dig deeper.**
- What does `cache_path` store, and what's `CacheFileHandler`?
- How does the client decide when to refresh a token?
- Read the spotipy source for `current_user_recently_played` — what endpoint and
  params does it hit?

---

## 5. Talking to Postgres from Python (`psycopg2`)

**What we did.** Opened a connection, used a cursor, ran parameterized inserts
inside a transaction. See `src/load/load_to_postgres.py`.

**How it works.**
- `psycopg2.connect(...)` → a **connection** (a session to the DB).
- `conn.cursor()` → a **cursor** you execute SQL through.
- `with conn:` → wraps statements in a **transaction**: commit on success, roll
  back on exception. (Note: it does *not* close the connection — we do that in
  `finally`.)
- **Parameterized queries** with `%s` placeholders: psycopg2 safely binds values,
  preventing **SQL injection**. Never f-string user/data values into SQL.
- `cur.rowcount` → how many rows the last statement affected.

**Why it matters.** Connections/cursors/transactions are the universal model for
relational DB access; parameterization is a security non-negotiable.

**Dig deeper.**
- What's the difference between a connection and a cursor?
- What does a transaction's ACID guarantee actually give you?
- `psycopg2` vs `psycopg` (v3) vs SQLAlchemy — when use which?
- Why is string-formatting SQL dangerous? Try to articulate an injection example.

---

## 6. JSONB in Postgres

**What we did.** Stored each raw API payload in a `jsonb` column (`raw.plays`,
`raw.artists`), then queried *into* it.

**How it works.**
- `->` returns a JSON object/element; `->>` returns it as **text**.
  e.g. `payload->'track'->>'name'`.
- `jsonb_array_elements(...)` expands a JSON array into rows; combined with
  `LATERAL`, you can unnest arrays (we used it to pull artist IDs out of each
  play's `track.artists` array).

**Why it matters.** JSONB lets you land schema-flexible raw data now and impose
structure later — the core of the **ELT** approach.

**Dig deeper.**
- `json` vs `jsonb` — storage, indexing, and performance differences.
- How would you index a field inside JSONB (GIN indexes, expression indexes)?
- What does `LATERAL` mean in a join?

---

## 7. Idempotency (safe re-runs)

**What we did.** Inserted a play only if its `played_at` wasn't already present:
`INSERT ... SELECT ... WHERE NOT EXISTS (...)`. Re-running inserts 0 rows.

**Why it matters.** Pipelines re-run (retries, schedules, backfills). An
idempotent load means re-running is always safe — no duplicates.

**Dig deeper.**
- Compare `WHERE NOT EXISTS` vs a `UNIQUE` constraint + `ON CONFLICT DO NOTHING`
  vs `MERGE`. Which is more robust and why?
- What is a "natural key" vs a "surrogate key"? Is `played_at` a good natural key?
- How does idempotency relate to "exactly-once" vs "at-least-once" processing?

---

## 8. ELT design & separation of concerns

**What we did.** `spotify_client.py` (extract) and `load_to_postgres.py` (load)
are separate modules; the loader imports the client.

**Why it matters.** Each module has one job, so you can test/change one without
the other. ELT (load raw, transform in-warehouse) keeps extraction "dumb" and
replayable.

**Dig deeper.**
- ELT vs ETL — why has the industry shifted toward ELT?
- What belongs in extract vs load vs transform layers?
- How would dbt fit on top of `raw.*` (Phase 3)?

---

## 9. Rate limiting & batching (429 handling)

**What we did (later reverted, but worth studying).** Batched artist IDs 50 at a
time and, on HTTP **429**, slept for the `Retry-After` seconds and retried once.

**Why it matters.** Public APIs throttle you. Respecting `Retry-After` and
batching requests is basic good-citizen API behavior.

**Dig deeper.**
- What does HTTP 429 mean, and what's the `Retry-After` header?
- Exponential backoff vs fixed retry — tradeoffs.
- Does spotipy already retry internally? (it does — when re-implement vs rely on
  the library?)

---

## 10. Git workflow: branches, PRs, remotes

**What we did.** Created a feature branch (`phase-2-extract-load`), committed,
pushed over **SSH**, and set up a browser **pull request** to merge.

**How it works.**
- A **branch** isolates work; a **PR** proposes merging it; **merging** brings it
  into `master`.
- **SSH vs HTTPS remotes**: SSH uses your key for `git push`; HTTPS needs a token.
  The GitHub **API** (PRs via `gh`) needs separate auth from `git push`.

**Why it matters.** PR-based flow is how teams review and ship code.

**Dig deeper.**
- What's the difference between `git push` auth and GitHub API auth?
- `git merge` vs `rebase`; what does `--force-with-lease` protect against?
- Why are feature branches + PRs better than committing to `master` directly?

---

## 11. The Spotify API restriction (a real-world constraint)

**What we did.** Hit a **403 Forbidden** on the batch artists endpoint, and saw
`genres: null` on single artists. Traced it to **Spotify's Nov 2024 Web API
changes**, which removed several catalog endpoints/fields for new apps in
development mode.

**Why it matters.** Platforms change their rules; part of engineering is
diagnosing external constraints and re-scoping rather than fighting them.

**Dig deeper.**
- Read Spotify's 2024 Web API deprecation notice — which endpoints/fields changed?
- Where could genres come from instead? (MusicBrainz, Last.fm tags)
- What's "development mode" vs "extended quota mode" for a Spotify app?

---

## 12. Debugging methodology (meta-skill)

Patterns we used that generalize:
- **Isolate the variable**: single-artist call vs batch call to localize a 403.
- **Read the traceback bottom-up**: the real error is usually the last line.
- **Confirm the environment, not just the code**: `sys.executable`, `which`,
  `pip list` — the `psycopg2` "bug" was an interpreter issue, not a code issue.
- **Verify assumptions cheaply**: `SELECT 1`, `py_compile`, printing names-only.

**Dig deeper.**
- Practice: next error you hit, write down your hypothesis *before* testing it.

---

## Suggested order for your deep dive
1. Virtual environments + how `PATH`/interpreters resolve (foundational).
2. OAuth 2.0 authorization-code flow (conceptually the densest).
3. psycopg2 transactions + parameterized queries (security-critical).
4. JSONB querying + idempotency (the data-engineering core).
5. ELT vs ETL and where dbt fits (sets up Phase 3).
