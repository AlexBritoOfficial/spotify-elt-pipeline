# Phase 3 deep dive — Transform (dbt + the star schema)

A plain-language walkthrough of everything we built in Phase 3: **what** we did,
**why** each step matters in real data engineering, and **what every file does**.
If you've never done analytics engineering before, read this top to bottom — the
concepts are introduced before they're used.

_Written: 2026-06-05._

---

## 0. The one-sentence summary

We took the messy raw JSON we'd already loaded into Postgres (Phase 2) and used
**dbt** to reshape it — with version-controlled, tested SQL — into a clean
**star schema** (`dim_artist`, `dim_track`, `dim_genre`, `bridge_artist_genre`,
`fact_plays`) that's easy and fast to query for analytics.

That is the **"T" in ELT**, and it's the single most important skill in the
modern analytics-engineering job.

---

## 1. Concepts first (so the rest makes sense)

### ELT, and where Phase 3 sits
- **ETL** = Extract → Transform → Load. You clean data *before* it lands in the
  warehouse.
- **ELT** = Extract → Load → **Transform**. You land raw data first, then
  transform it *inside* the warehouse with SQL. This is the modern default
  because storage is cheap, warehouses are powerful, and keeping raw data means
  any transformation bug can be fixed and **re-run** without re-hitting the API.
- Phase 1 = the warehouse (Postgres). Phase 2 = Extract + Load (raw JSON →
  `raw.plays` / `raw.artist_tags`). **Phase 3 = Transform.**

### The "warehouse" layers (raw → staging → marts)
Almost every real dbt project organizes models into layers. We follow the
standard:

| Layer | Our models | Job |
|---|---|---|
| **source / raw** | `raw.plays`, `raw.artist_tags` | Untouched API payloads (JSONB). Never edited. |
| **staging** | `stg_plays`, `stg_artist_tags` | Light cleanup: flatten JSON, rename, cast types. One staging model per source table. |
| **intermediate** | `int_artist_genres` | Reusable business logic that's too complex for staging but isn't a final table (our genre-cleaning lives here). |
| **marts** | `dim_*`, `fact_plays`, `bridge_*` | The final, business-facing star schema people actually query. |

**Why layer at all?** Each layer has one job, so models stay small and
debuggable, logic is written once and reused, and a change low down flows
predictably upward. This is the difference between a pile of SQL scripts and a
*maintainable* transformation codebase.

### Dimensional modeling & the star schema
Raw event data is awkward to analyze directly. **Dimensional modeling** (Kimball)
reshapes it into two kinds of tables:

- **Fact table** — the *events/measurements*, at a defined **grain** (level of
  detail). Ours is `fact_plays`: **one row per play event**. Facts hold
  *measures* (numbers you aggregate: `duration_ms`, `play_count`) and *foreign
  keys* pointing at dimensions.
- **Dimension tables** — the *descriptive context* you slice and filter by:
  `dim_artist`, `dim_track`, `dim_genre`. One row per thing, lots of attributes.

Drawn out, the fact sits in the middle with dimensions around it like a **star**
— hence "star schema." It's the industry-standard shape because it makes queries
like *"total listening minutes by genre this month"* a simple, fast join +
group-by that any analyst (or BI tool) can write.

```
   dim_date   dim_genre   dim_track
          \       |        /
           dim_artist — bridge — fact_plays
```

### Grain — the most important word in modeling
The **grain** is the precise meaning of one row. We chose: *"one row in
`fact_plays` = one play of one track at one timestamp."* Pin the grain down
**first**; every other decision (which keys, which measures, what "unique" means)
follows from it. Getting the grain wrong is the classic beginner mistake — it
silently double-counts everything.

### Surrogate keys
A **natural key** is the real-world id (`track_id` from Spotify). A **surrogate
key** is a system-generated stand-in. We generate ours with `md5(natural_key)` —
e.g. `artist_key = md5(artist_id)`. Why bother?
- Stable, uniform join keys across the whole schema (every table joins on
  `*_key`).
- Insulates the model from messy/missing/changing natural keys.
- It's the standard dimensional pattern — interviewers expect to see it.

We used plain `md5()` instead of the popular `dbt_utils.generate_surrogate_key`
macro **on purpose**: that macro needs `dbt deps` to download a package, and this
machine has SSL/cert quirks that make network installs flaky. Dependency-free is
more robust here.

### Idempotency
A step is **idempotent** if running it twice gives the same result as running it
once. Phase 2's loader is idempotent (it skips plays it already has). dbt is
idempotent by design: `dbt run` **drops and rebuilds** the models every time, so
the output is a pure function of the inputs. This is huge operationally — you can
re-run safely after any failure or code change.

### Tests as a first-class citizen
In dbt, **data tests** are assertions about your data that run as SQL. We use:
- `not_null`, `unique` — integrity of keys.
- `relationships` — *referential integrity*: every `fact_plays.artist_key` must
  exist in `dim_artist`. (This is what catches "orphan" rows.)

A passing `dbt test` is your proof the model is internally consistent. Shipping
transforms without tests is like shipping code without unit tests.

### Folksonomy (the genre problem)
Spotify stopped giving genres to new apps, so Phase 2 enriched artists with
**Last.fm tags** — crowd-sourced free-text labels. A crowd-tagged vocabulary is
called a **folksonomy**, and it's gloriously messy: for "Diddy" we got real
genres (`Hip-Hop`, `rap`, `rnb`) *plus* case/punctuation duplicates (`hip hop`,
`hip+hop`), decade tags (`00s`, `90s`), a nationality (`american`), and the
artist's own name (`diddy`). Cleaning this into usable genres was the most
interesting transform in Phase 3 (see §4).

---

## 2. What is dbt, concretely?

**dbt (data build tool)** lets you write each transformation as a `SELECT`
statement in a `.sql` file (a **model**). dbt then:
- wraps your `SELECT` in the right `CREATE VIEW`/`CREATE TABLE` boilerplate
  (you choose per model — a **materialization**),
- figures out the **dependency order** automatically from the `{{ ref(...) }}`
  and `{{ source(...) }}` functions you use to reference other models,
- builds everything in that order, and
- runs your tests.

Two template functions do the heavy lifting (this is **Jinja** templating inside
SQL):
- `{{ source('raw', 'plays') }}` → compiles to `raw.plays`. Declaring sources in
  YAML means dbt knows where raw data enters the graph.
- `{{ ref('stg_plays') }}` → compiles to the real table/view name for that model,
  *and* tells dbt "this model depends on `stg_plays`, build it first."

That dependency graph (a **DAG** — directed acyclic graph) is dbt's superpower:
you never manually order your SQL again.

---

## 3. The step-by-step process we followed (and the thinking)

### Step 1 — Install dbt (and a real-world gotcha)
First attempt was `pip install dbt` — which **failed**. Two lessons:
1. The PyPI package literally named `dbt` is a **deprecated placeholder**. Since
   dbt 1.0 you install an **adapter** package for your database: for Postgres
   that's **`dbt-postgres`**, which pulls in `dbt-core` automatically.
2. Bare `dbt-postgres` resolved `dbt-core` to a **2.0 alpha pre-release**,
   because its dependency spec contains an `rc` marker which flips pip into
   "pre-releases allowed" mode. We don't want an unstable alpha under a learning
   project, so we **pinned** to the stable line: `dbt-core==1.10.*` and
   `dbt-postgres==1.10.*` (recorded in `requirements.txt`).

**Field lesson:** dependency pinning isn't bureaucracy — it's what makes a
pipeline reproducible six months from now.

### Step 2 — Inspect reality before modeling
Before writing a single model, we looked at the actual data: row counts and the
real JSONB shape of `raw.plays` and `raw.artist_tags`. **Never model against what
you assume the data looks like — model against what it actually is.** This is
where we discovered the nested `track.album.*`, the `track.artists[]` array, and
the folksonomy mess.

### Step 3 — Decide the structure (three deliberate forks)
We made three design choices up front:
1. **dbt project location** → a top-level `dbt/` directory, kept out of the
   `src/` Python package tree (cleaner separation).
2. **Genre modeling** → a **bridge table** (many-to-many) rather than a single
   genre column, so an artist can have several genres. This is "proper"
   dimensional modeling.
3. **Tag cleaning** → an engineered approach: a **seed denylist** + **regex**,
   not just a quick normalize. More work, but a far better story and result.

### Step 4 — Scaffold the project
Created `dbt_project.yml` (project config), `profiles.yml` (connection), a
`seeds/` file, and the `models/` tree (`staging/`, `intermediate/`, `marts/`).

### Step 5 — Build bottom-up: staging → intermediate → marts
- **Staging** flattens the JSON (`stg_plays`, `stg_artist_tags`).
- **Intermediate** cleans the tags (`int_artist_genres`).
- **Marts** assemble the star schema (`dim_*`, `bridge_*`, `fact_plays`).

### Step 6 — Verify with `seed`, `run`, `test`
- `dbt seed` loaded the denylist CSV into the warehouse.
- `dbt run` built all 8 models (50 plays → `fact_plays`, etc.).
- `dbt test` ran **33** assertions — all green.
- We sanity-checked the *actual output* (Diddy's cleaned genres, a genre rollup)
  — because "the tests pass" and "the data is correct" are not the same claim.

### Step 7 — Fix a deprecation, future-proof
dbt 1.10 warned that `relationships` tests should nest their arguments under an
`arguments:` key. We updated the YAML and re-tested (still 33/33). Treating
warnings as future errors keeps the project from rotting.

---

## 4. The hard/interesting parts, explained

### 4a. The genre-cleaning pipeline (`int_artist_genres.sql`)
This is a multi-stage CTE pipeline (each `with ... as (...)` is one named step):

1. **normalize** — `lower()` the tag, turn `-`, `+`, `/` into spaces, collapse
   repeated whitespace. So `Hip-Hop`, `hip hop`, and `hip+hop` all become the
   single string `hip hop`.
2. **deduped** — group by `(artist_id, genre)` and keep `max(tag_count)`. This
   merges the now-identical variants and keeps the strongest signal (Diddy's
   `Hip-Hop`=100 and `hip hop`=34 collapse to `hip hop`=100).
3. **cleaned** — drop the noise:
   - anything in the **denylist seed** (`seen live`, `american`, nationalities…),
   - the artist's **own name** used as a tag (`genre <> lower(artist_name)`),
   - **decade/number** tags via regex (`^[0-9]{2,4}s$`, `^[0-9]+$`),
   - single-character junk.
4. **ranked** — `row_number()` per artist ordered by tag count, then keep the
   **top-N** (N=3, set by the `max_genres_per_artist` variable in
   `dbt_project.yml`).

Result for Diddy: `hip hop`, `rap`, `rnb` — exactly the real genres, nothing
else. This is a great **STAR interview story**: *routing around a vendor
constraint (no Spotify genres) and turning a noisy crowd-sourced source into
clean, ranked dimensions.*

### 4b. The non-obvious `dim_artist` bug we avoided
There are **53** artists with Last.fm tags but only **50** plays — so the tag set
includes *featured/album* artists, not just each play's *primary* artist. (Phase
2's loader unnests the **whole** `track.artists[]` array, which is why.)

If we'd built `dim_artist` from primary artists only, the `bridge_artist_genre`
table would reference artists that don't exist in `dim_artist` — and the
`relationships` test would (correctly) fail. So `dim_artist` is the **union** of
every artist seen as a play's artist *and* every artist carrying tags (51 rows
total). **Lesson:** referential integrity isn't automatic — you design for it,
and the relationship tests are what *prove* you got it right.

### 4c. Materializations: views vs tables
We configured (in `dbt_project.yml`):
- **staging + intermediate → views** — cheap, always reflect the latest raw data,
  no storage duplication. Good for light, frequently-changing logic.
- **marts → tables** — physically built, so analytical queries against the star
  schema are fast and stable.

This view/table trade-off (speed & stability vs freshness & cost) is a constant
real-world judgment call.

### 4d. The date dimension (`dim_date`)
A **date dimension** is a table with one row per calendar day and lots of
pre-computed attributes (year, quarter, month, weekday name, `is_weekend`…). Why
build one instead of just calling SQL date functions on `played_at`?
- **Reusable, consistent** date logic — "is this a weekend?" is defined once.
- **Fast, simple analytics** — slicing plays by month/weekday becomes a plain
  join + group-by that any BI tool can do.
- It's the single most common dimension in the entire industry.

Ours uses Postgres `generate_series` to build the spine, with the range
**derived from the data** (full years spanning the play history) so it grows
automatically — no hardcoded dates. The key is the classic **smart key**: the
integer `YYYYMMDD` (e.g. `20260604`), and `fact_plays.date_key` joins to it.

---

## 5. Why this matters in the field

- **"Analytics Engineer" is a job, and this is the job.** dbt + dimensional
  modeling + tested SQL in a warehouse is the core of the modern data stack
  (dbt + Snowflake/BigQuery/Redshift/Postgres).
- **Reproducibility & trust.** Version-controlled, tested transforms mean anyone
  can rebuild the exact same tables and *trust* the numbers. That trust is the
  entire point of a data team.
- **Maintainability.** Layering + `ref()` + the DAG turn "a folder of scripts no
  one dares touch" into a system you can safely change.
- **Communication.** A star schema is a shared language between engineers,
  analysts, and BI tools. It's deliberately simple so non-engineers can self-serve.

---

## 6. Every file in the project — what it does & why it exists

### Infrastructure & config (repo root)
| File | Responsibility / purpose |
|---|---|
| `docker-compose.yml` | Defines the Postgres 15 service (our warehouse). Mounts `sql/ddl/` so schema DDL runs automatically on first start; persists data in a Docker volume. |
| `requirements.txt` | Python + dbt dependencies. Phase 3 added **pinned** `dbt-core==1.10.*` / `dbt-postgres==1.10.*`. |
| `.env` | **Real secrets** (Spotify creds, Last.fm key, Postgres creds). Gitignored — never committed. |
| `.env.example` | Placeholder template of the same vars, safe to commit. |
| `.gitignore` | Keeps secrets, venv, caches, dbt build artifacts out of git. |
| `README.md` | Public-facing project overview, architecture diagram, roadmap. |
| `PLAN.md` | The local-only 14-day learning plan (not the source of truth for structure). |

### Raw schema DDL (`sql/`)
| File | Responsibility / purpose |
|---|---|
| `sql/ddl/01_create_schemas.sql` | Creates the `raw` and `analytics` schemas and the `raw.plays` / `raw.artists` tables. Auto-runs on first DB start. |
| `sql/ddl/02_artist_tags.sql` | Creates `raw.artist_tags` (Last.fm tags keyed by Spotify artist id). |

### Extract (`src/extract/`) — the "E"
| File | Responsibility / purpose |
|---|---|
| `authorize.py` | One-time Spotify OAuth flow; caches a refresh token in `.cache` so later runs are non-interactive. |
| `spotify_client.py` | Thin wrapper over the Spotify API (spotipy). `get_recent_plays()` returns the last ≤50 plays. |
| `lastfm_client.py` | Thin wrapper over the Last.fm API. `get_artist_tags()` returns an artist's top tags (our genre proxy), with key-safe error handling. |
| `__init__.py` | Marks the folder as an importable Python package. |

### Load (`src/load/`) — the "L"
| File | Responsibility / purpose |
|---|---|
| `load_to_postgres.py` | Pulls from the extract clients and **idempotently** inserts raw JSONB into `raw.plays` and `raw.artist_tags` (skips rows already present). Notably unnests **all** artists per track — the reason the tag set is larger than the play set. |
| `__init__.py` | Package marker. |

### Transform (`src/transform/` + `dbt/`) — the "T" (Phase 3)
| File | Responsibility / purpose |
|---|---|
| `src/transform/README.md` | Points to the dbt project and lists the run commands. |
| `dbt/dbt_project.yml` | The dbt project config: paths, the `max_genres_per_artist` variable, and the materialization strategy (views for staging/intermediate, tables for marts). |
| `dbt/profiles.yml` | The database connection, project-local and env-var driven (defaults match docker-compose, no secrets). Used via `--profiles-dir .`. |
| `dbt/.gitignore` | Ignores dbt build output (`target/`, `dbt_packages/`, `logs/`). |
| `dbt/seeds/non_genre_tags.csv` | A **seed**: a CSV dbt loads into the warehouse as a table. Our curated denylist of non-genre tags used to filter the folksonomy. |

#### dbt models — staging
| File | Responsibility / purpose |
|---|---|
| `models/staging/_staging__sources.yml` | Declares the `raw` source tables so models can `{{ source(...) }}` them. |
| `models/staging/stg_plays.sql` | Flattens `raw.plays` JSONB into tidy typed columns (track, album, primary artist, context); one row per play. Materialized as a view. |
| `models/staging/stg_artist_tags.sql` | Unnests the Last.fm `toptags.tag[]` array → one row per (artist, tag); guards against artists with no tags. |
| `models/staging/_staging__models.yml` | Descriptions + `not_null`/`unique` tests for the staging models. |

#### dbt models — intermediate
| File | Responsibility / purpose |
|---|---|
| `models/intermediate/int_artist_genres.sql` | The genre-cleaning pipeline: normalize → dedupe → denylist/regex filter → rank → top-N. The reusable core feeding `dim_genre` and the bridge. |

#### dbt models — marts (the star schema)
| File | Responsibility / purpose |
|---|---|
| `models/marts/dim_artist.sql` | One row per artist (union of play-artists and tag-artists), with a convenience `primary_genre`. |
| `models/marts/dim_track.sql` | One row per track with album attributes + a `dim_artist` FK. |
| `models/marts/dim_genre.sql` | One row per distinct cleaned genre. |
| `models/marts/dim_date.sql` | Calendar date dimension — one row per day across the years in the play history (data-driven range, integer `YYYYMMDD` key + year/quarter/month/weekday/`is_weekend`). |
| `models/marts/bridge_artist_genre.sql` | Many-to-many link of artists to their top-N genres (with rank + tag count). |
| `models/marts/fact_plays.sql` | The fact table — one row per play; FKs to track/artist/**date**, a `played_date`, and the `duration_ms` / `play_count` measures. |
| `models/marts/_marts__models.yml` | Descriptions + the full test suite for the marts: `not_null`, `unique`, and `relationships` (referential integrity). |

### Tests (`tests/`)
| File | Responsibility / purpose |
|---|---|
| `tests/test_lastfm_client.py` | Unit tests for the Last.fm client (mocked `requests`, no network) — incl. one asserting the API key never leaks into a traceback. |
| `tests/test_load_idempotency.py` | Integration tests against Postgres: the `INSERT … WHERE NOT EXISTS` dedup logic and the `raw.plays` uniqueness invariant (skip if DB down; rollback so nothing persists). |

### Docs (`docs/`)
| File | Responsibility / purpose |
|---|---|
| `RESUME.md` | "Where I left off / how to resume" — the session bookmark. |
| `STAR-summary.md` | Interview STAR stories drawn from the project. |
| `learning-notes.md` | Plain-language recap of Session 1 (Phase 1). |
| `phase-2-deep-dive.md` | Self-study guide for Phase 2 (Extract & Load). |
| `phase-3-deep-dive.md` | **This file** — the Phase 3 (Transform) walkthrough. |

### Generated / local (not committed, FYI)
| Path | What it is |
|---|---|
| `dbt/target/` | dbt's compiled SQL + run artifacts (regenerated every run). |
| `dbt/logs/` | dbt run logs. |
| `.cache` | Spotify OAuth token cache. |
| `.venv/` | The Python virtual environment. |
| `.idea/` | IDE (PyCharm) settings. |

---

## 7. How to run it

```bash
colima status                         # Docker engine up?
docker compose up -d                  # Postgres up
source .venv/bin/activate             # Python env (where dbt lives)
cd dbt
export DBT_SEND_ANONYMOUS_USAGE_STATS=False   # avoids telemetry SSL noise on this machine

dbt debug --profiles-dir .            # check the connection
dbt seed  --profiles-dir .            # load the denylist
dbt run   --profiles-dir .            # build staging -> marts
dbt test  --profiles-dir .            # run all data tests
```

Quick look at the results:

```bash
docker compose exec -T postgres psql -U postgres -d spotify -c \
  "SELECT a.artist_name, a.primary_genre, count(*) plays
   FROM analytics.fact_plays f JOIN analytics.dim_artist a USING (artist_key)
   GROUP BY 1,2 ORDER BY plays DESC LIMIT 8;"
```

---

## 8. Glossary (quick reference)

- **ELT / ETL** — load-then-transform vs transform-then-load.
- **Model** — one dbt `.sql` file = one `SELECT` that becomes a view/table.
- **Materialization** — how a model is built: `view` or `table` (also
  `incremental`, `ephemeral`).
- **Source / `ref`** — Jinja functions that name raw tables / other models and
  build the dependency graph.
- **DAG** — the dependency graph dbt builds models in.
- **Seed** — a CSV dbt loads as a table (our denylist).
- **Staging / intermediate / marts** — the warehouse layering convention.
- **Fact / dimension** — events+measures vs descriptive context.
- **Grain** — what one row means.
- **Surrogate key** — a generated stand-in key (`md5(...)`).
- **Bridge table** — resolves a many-to-many relationship (artist↔genre).
- **Idempotent** — re-running changes nothing.
- **Folksonomy** — a crowd-sourced free-text tag vocabulary.
- **Referential integrity** — every FK points at a row that exists (the
  `relationships` test).

---

## 9. Things to review on your own

- Re-read `int_artist_genres.sql` and trace one artist through each CTE.
- Open `dbt/target/compiled/…` after a run to see your Jinja compiled into plain
  SQL — demystifies `ref()`/`source()`.
- Try changing `max_genres_per_artist` to 5, `dbt run` + `dbt test`, and watch
  the bridge grow.
- Run `dbt docs generate && dbt docs serve --profiles-dir .` to see the
  auto-generated lineage graph of your DAG.
- Think about the grain of each table until you can say each one out loud.

---

## 10. What's next (Phase 4)
- ✅ `dim_date` for clean time-based analysis (done — see §4d).
- `dbt docs` + lineage in the README.
- Wire `dbt build` (run + test in one) into the load step, then schedule it.
- A small dashboard / notebook on top of the star schema.
```
