# 14-Day Work Plan · Spotify Listening Data Pipeline

Assumes about 2 to 3 focused hours per day. You already know Python and SQL but are learning dbt and Airflow. If you know all four, compress this to 7 to 10 days.

Each day has a goal, the work, and a definition of done. Don't move on until the "done when" check passes — that's how you avoid debugging four tools at once on day 12.

---

## Week 1 · Build the pipeline

### Day 1 · Foundation
**Goal:** A working repo and a running Postgres container.

- [ ] Install Docker Desktop, verify with `docker run hello-world`
- [ ] Create the GitHub repo, clone it locally
- [ ] Register a Spotify developer app at https://developer.spotify.com/dashboard
- [ ] Save Client ID and Secret in a local `.env` file (gitignored)
- [ ] Write a minimal `docker-compose.yml` with one service: Postgres 15
- [ ] Run `docker compose up -d`, connect with `psql` or DBeaver to confirm

**Done when:** you can `SELECT 1` against the Postgres container from your host machine.

---

### Day 2 · First extraction
**Goal:** Pull your real listening history into a Python script.

- [ ] `pip install spotipy python-dotenv psycopg2-binary`
- [ ] Write `extract/authorize.py` — runs the OAuth flow once, caches refresh token
- [ ] Write `extract/spotify_client.py` — wraps `spotipy.current_user_recently_played()`
- [ ] Print the last 50 tracks to console as JSON
- [ ] Save one batch to a local `samples/recent_plays.json` for inspection

**Done when:** running the script prints real play history from your account.

---

### Day 3 · Load to Postgres
**Goal:** Land raw JSON into the warehouse.

- [ ] Design raw schema: one table `raw.plays` with columns `(ingested_at, payload jsonb)`
- [ ] Write a SQL init script that creates the schema on first container start
- [ ] Write `extract/load_to_postgres.py` — inserts each play as a JSONB row
- [ ] Add deduplication: skip plays where `played_at` already exists
- [ ] Run the full extract + load, verify rows land

**Done when:** `SELECT COUNT(*) FROM raw.plays` returns more than zero.

---

### Day 4 · Enrich with artists and genres
**Goal:** The Spotify "recently played" endpoint doesn't return genres, so call the artist endpoint.

- [ ] Add `get_artists_batch(ids)` to the client — batches up to 50 IDs per call
- [ ] Create `raw.artists` landing table, also JSONB
- [ ] Update the extract script: collect distinct artist IDs from plays, fetch any new ones
- [ ] Add basic rate limit handling — sleep on 429, retry once

**Done when:** `raw.artists` has one row per artist you've played, each with a `genres` array in the payload.

---

### Day 5 · dbt setup and first model
**Goal:** dbt initialized and connected to Postgres.

- [ ] `pip install dbt-postgres`
- [ ] `dbt init dbt` inside the project, choose Postgres
- [ ] Configure `profiles.yml` to point at the Docker Postgres
- [ ] `dbt debug` should pass
- [ ] Write `models/staging/stg_plays.sql` — flattens `raw.plays` JSON into typed columns: `played_at`, `track_id`, `track_name`, `artist_id`, `duration_ms`
- [ ] `dbt run --select stg_plays`

**Done when:** `SELECT * FROM analytics.stg_plays LIMIT 10` shows clean tabular data.

---

### Day 6 · Finish staging, add tests
**Goal:** All raw data flattened, with quality tests.

- [ ] Write `stg_artists.sql` and `stg_tracks.sql`
- [ ] Create `models/staging/schema.yml` with tests:
  - `stg_plays.played_at` — not_null
  - `stg_plays.track_id` — not_null
  - `stg_artists.artist_id` — unique, not_null
- [ ] `dbt build` (runs all models + tests)

**Done when:** `dbt build` passes with zero failures.

---

### Day 7 · Mart layer · star schema
**Goal:** Clean fact and dimension tables.

- [ ] Write `models/marts/dim_artists.sql` — one row per artist, latest genre array
- [ ] Write `models/marts/dim_tracks.sql` — one row per track
- [ ] Write `models/marts/dim_dates.sql` — date spine from first play to today
- [ ] Write `models/marts/fct_plays.sql` — one row per play event, foreign keys to dims
- [ ] Add `relationships` tests between fact and dims in `marts/schema.yml`
- [ ] `dbt build` passes

**Done when:** you can write a single SQL query joining fact and dims to answer "what artist did I play most last month?"

---

## Week 2 · Automate, visualize, polish

### Day 8 · Incremental loading
**Goal:** `fct_plays` only processes new rows, not the whole table.

- [ ] Convert `fct_plays` to `materialized='incremental'` in the model config
- [ ] Add the `{% if is_incremental() %}` guard filtering on `played_at > (SELECT MAX(played_at) FROM {{ this }})`
- [ ] Test by running twice — second run should process zero rows
- [ ] Test backfill: `dbt run --select fct_plays --full-refresh`

**Done when:** consecutive `dbt run` calls show "0 rows affected" on the second one.

---

### Day 9 · Airflow setup
**Goal:** Airflow is running and can see your project.

- [ ] Add Airflow services to `docker-compose.yml` (webserver, scheduler, postgres for metadata)
- [ ] Use the official `apache/airflow:2.8.0` image
- [ ] Mount `./airflow/dags` and `./extract` and `./dbt` as volumes
- [ ] Bring it up: `docker compose up -d`
- [ ] Log in to http://localhost:8080 with `admin` / `admin`

**Done when:** the Airflow UI loads and shows the example DAGs.

---

### Day 10 · The DAG
**Goal:** Daily automated pipeline end-to-end.

- [ ] Create `airflow/dags/spotify_daily_ingestion.py` with four tasks:
  1. `extract_plays` — calls your Python script
  2. `extract_artists` — fetches any new artist metadata
  3. `dbt_run` — `BashOperator` running `dbt run`
  4. `dbt_test` — `BashOperator` running `dbt test`
- [ ] Wire dependencies: `extract_plays >> extract_artists >> dbt_run >> dbt_test`
- [ ] Set `schedule_interval='0 6 * * *'` (daily at 6am)
- [ ] Set `retries=2`, `retry_delay=timedelta(minutes=5)`
- [ ] Trigger manually, watch all four tasks turn green

**Done when:** a manual DAG run completes successfully end-to-end.

---

### Day 11 · Metabase + first two questions
**Goal:** Dashboard infrastructure and two of three analytical views.

- [ ] Add Metabase service to `docker-compose.yml`, port 3000
- [ ] First-run setup: connect to Postgres, database `spotify`
- [ ] Build question 1: **Top artists by month** — use `ROW_NUMBER() OVER (PARTITION BY month ORDER BY play_count DESC)`, filter to top 5
- [ ] Build question 2: **Listening trends** — heatmap, hour of day × day of week, value = play count

**Done when:** both saved questions render real charts from your data.

---

### Day 12 · Third question + dashboard
**Goal:** Genre analysis and a unified dashboard.

- [ ] Build question 3: **Genre analysis** — unnest the genres array, group by month and genre, stacked area chart of top 8 genres
- [ ] Create a new Metabase dashboard, add all three questions
- [ ] Add a date range filter at the dashboard level
- [ ] Take screenshots for the README

**Done when:** the dashboard loads in under 2 seconds and tells a coherent story about your listening.

---

### Day 13 · Polish and document
**Goal:** Project looks professional to a reviewer.

- [ ] Write the README (use the scaffold provided)
- [ ] Create an architecture diagram in [excalidraw.com](https://excalidraw.com) or draw.io, export as PNG
- [ ] Save dashboard screenshots to `docs/`
- [ ] Add docstrings to every Python function
- [ ] Add inline comments to non-obvious dbt models
- [ ] Create `.env.example` with placeholder values, ensure real `.env` is in `.gitignore`
- [ ] Verify nothing sensitive is committed: `git log -p | grep -i secret` should be empty

**Done when:** a stranger could read the README and know what the project does in 60 seconds.

---

### Day 14 · Ship it
**Goal:** Reproducible on someone else's machine, published.

- [ ] On a clean directory, run `git clone` followed by `docker compose up -d` — does everything come up?
- [ ] Fix any setup issues that came up (missing volume, wrong env var name, etc.)
- [ ] Push final commits to GitHub
- [ ] Pin the repo on your GitHub profile
- [ ] Write a short LinkedIn post: what you built, what you learned, link to repo
- [ ] (Optional) Write a longer blog post on Medium or your own site

**Done when:** the LinkedIn post is live and you can hand the repo URL to any data engineer for code review.

---

## Buffer days

If a day's work spills over, that's normal. Build in 2 to 3 buffer days across the 2 weeks. Most people get stuck on:

- **Day 2:** Spotify OAuth flow on the first try (give yourself extra time)
- **Day 8:** Incremental dbt models (the syntax is unintuitive)
- **Day 10:** Airflow task dependencies and volume mounting (paths inside the container vs your host)

If you're truly stuck more than 90 minutes, post in r/dataengineering or the dbt Slack — these communities are friendly and your question is almost certainly common.

## What to do once shipped

- Add the project to your resume under a "Projects" section with two bullets: what you built, what skill it demonstrates
- Reference it in interviews when asked about ETL, orchestration, or dbt
- Use it as your "tell me about a project you're proud of" answer
