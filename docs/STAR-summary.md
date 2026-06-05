# Spotify ELT Pipeline — STAR Interview Summary

A reference for talking about this project in interviews using the **STAR**
framework (Situation · Task · Action · Result). Start with the headline story,
then pull a specific story for whatever the interviewer asks (debugging,
security, working under constraints).

**One-liner:** A local, reproducible **ELT pipeline** that extracts my personal
Spotify listening history via the Web API, lands it raw (JSONB) in Postgres, and
transforms it with **dbt** into a tested **star schema** — orchestrated end to
end and running in Docker.

---

## ⭐ Headline — building the pipeline

**Situation.** I wanted a portfolio project that showed real data-engineering
practice, not a throwaway script. I used my own Spotify listening history as the
dataset.

**Task.** Stand up an end-to-end ELT pipeline (extract → load raw → transform
in-warehouse) that runs reproducibly on any machine and follows modern patterns:
raw-first, idempotent, version-controlled.

**Action.**
- Containerized **Postgres 15** with Docker Compose; the `raw` and `analytics`
  schemas auto-create on first start via a mounted DDL script.
- Wrote a Python **extraction layer** (spotipy) behind a thin client module;
  authenticated once with OAuth and cached a refresh token for silent reruns.
- Built an **idempotent loader**: each play is stored as a JSONB payload in
  `raw.plays`, inserted only if its `played_at` isn't already present — so
  re-runs never duplicate data.
- Kept **extract and load as separate modules**, each with one responsibility.

**Result.** A working pipeline that pulls my 50 most recent plays into Postgres;
re-running inserts **zero** duplicates. The raw JSONB is queryable immediately
(e.g. `payload->'track'->>'name'`), proving the "load raw, transform later"
approach.

---

## ⭐ Solving an environment constraint (Docker on an unsupported OS)

**S.** My Mac runs macOS 13 (Intel); Docker Desktop now requires macOS 14+, so it
wouldn't install.

**T.** Get a working Docker runtime without upgrading the OS.

**A.** Diagnosed the version requirement, evaluated alternatives, and installed
**Colima** (a lightweight open-source Docker engine) + the Docker CLI via
Homebrew, set to auto-start. Verified with `docker run hello-world` and confirmed
every `docker`/`docker compose` command works unchanged.

**R.** Full Docker functionality on an unsupported OS, no upgrade needed — and I
documented Colima as an alternative in the project README for others in the same
spot.

---

## ⭐ Catching and remediating a leaked secret (security)

**S.** During repo setup, a real Spotify Client Secret got committed into a
tracked file (`.env.example`) and reached GitHub via a merged pull request.

**T.** Contain the exposure properly — not just delete the line.

**A.**
- Recognized that removing a secret from git history is **insufficient** once
  it's on a remote (it can be cached, cloned, or indexed).
- **Rotated** the secret in the Spotify dashboard — the only action that truly
  invalidates it.
- Moved real credentials into a gitignored `.env`; restored `.env.example` to
  placeholders.
- Scrubbed history: removed the offending commit, force-pushed a clean branch,
  deleted the leaked branch, and verified no ref still contained the secret.

**R.** Exposure neutralized via rotation and the history cleaned. I adopted the
rule that secrets live only in a gitignored `.env`, never in committed files — a
concrete lesson in secret hygiene and incident response.

---

## ⭐ Routing around a platform constraint with a second data source

**S.** To enrich plays with genres, I needed Spotify's artist endpoint. The batch
(`/artists?ids=`) call returned **403 Forbidden**, and single-artist responses
came back with `genres: null`.

**T.** Find the root cause and still deliver genre data.

**A.** Isolated the failure (single call worked, batch was forbidden, genres
absent either way) and traced it to **Spotify's 2024 Web API changes**, which
strip catalog fields like `genres` from new apps in development mode. Rather than
fight a platform policy, I **integrated a second source**: Last.fm's
`artist.getTopTags`. I wrote a small client, landed the raw tag payloads in a new
`raw.artist_tags` table keyed by Spotify `artist_id`, and made the load
idempotent (it only fetches artists not already stored). I also hardened the
client so the API key can't leak in a traceback, and debugged a real failure
along the way (a truncated 31-char key returning HTTP 403 "Invalid API key").

**R.** Recovered the genre feature *without* Spotify — **53 artists enriched**
with accurate tags (e.g. Audioslave → alternative rock/grunge; De La Soul →
hip-hop/rap), re-runnable with zero duplicate fetches. Turned a hard external
blocker into a working feature by swapping data sources; the messy folksonomy
tags become a clean dbt transform in Phase 3.

---

## ⭐ Modeling messy data into a tested star schema (dbt / analytics engineering)

**S.** The raw layer was nested Spotify JSONB plus a noisy crowd-sourced
**folksonomy** of Last.fm tags — case/punctuation duplicates (`Hip-Hop`/`hip hop`),
decade tags (`90s`), nationalities, and artists' own names mixed in with real
genres. Not analyzable as-is.

**T.** Transform `raw` into a clean, trustworthy dimensional model that an analyst
or BI tool could query directly — and prove it's correct.

**A.**
- Built a **dbt** project layered staging → intermediate → marts, with the build
  order derived automatically from `ref()`/`source()` (the DAG).
- Designed a **star schema** at a clearly defined grain (`fact_plays` = one play),
  with `dim_track`/`dim_artist`/`dim_genre`/`dim_date` and a **many-to-many bridge**
  for artist↔genre. Used `md5()` **surrogate keys** throughout.
- Wrote a multi-stage **tag-cleaning pipeline**: normalize → dedupe (max count) →
  filter via a **seed denylist + regex** → rank → keep top-N genres per artist.
- Caught a subtle integrity trap (53 tagged artists > 50 plays = featured artists)
  and made `dim_artist` the **union** of play- and tag-artists so the bridge never
  orphans — proven by **`relationships` tests**.
- Pinned dbt to a stable version after diagnosing that the bare package resolved
  `dbt-core` to a 2.0 **alpha** (its dep spec's `rc` marker enables pre-releases).

**R.** A queryable `analytics` star schema with **39 passing data tests**
(not_null / unique / relationships). The folksonomy became clean ranked genres
(e.g. Diddy → hip hop / rap / rnb), enabling one-join analytics like plays-by-genre,
-artist, -weekday, and -release-decade.

---

## ⭐ Operationalizing the pipeline (Phase 4)

**S.** The pieces (extract, load, transform) ran as separate manual steps.

**T.** Make the whole thing one reproducible, schedulable command, and surface the
results.

**A.** Wrote `run_pipeline.sh` (Postgres up → extract+load → `dbt build` which runs
*and* tests every model), idempotent and cron-ready; generated dbt **docs/lineage**;
and produced a sample **insights** report (queries in `sql/analysis/`).

**R.** `./run_pipeline.sh` refreshes raw data and rebuilds+tests the warehouse in
one shot — a v1 ELT pipeline ready to schedule.

---

## Concepts & practices to name-drop
- **ELT vs ETL**; raw-first, replayable design
- **Idempotent loads** (dedup on a natural key)
- **JSONB** for schema-flexible raw storage
- **dbt**: models, `ref()`/`source()` DAG, materializations (view vs table), seeds
- **Dimensional modeling**: star schema, grain, fact/dimension, **bridge** table,
  **surrogate keys**, a **date dimension**
- **Data testing**: not_null / unique / **referential integrity** (relationships)
- **Docker Compose** for reproducible infrastructure; **OAuth** refresh-token flow
- **BI / serving layer** (Metabase on the star schema — the modern data stack end to end)
- **Separation of concerns**; **dependency pinning** for reproducibility
- **Git/GitHub workflow** (branches, PRs) and **secret management**

## Quick facts / metrics
- End-to-end **ELT**: 50 plays → raw JSONB → dbt star schema, one command
- **9 dbt models, 39 data tests passing**; `fact_plays`(50), `dim_track`(49),
  `dim_artist`(51), `dim_genre`(41), `dim_date`(365), `bridge_artist_genre`(147)
- Idempotent throughout (0 duplicates on re-run; dbt rebuilds deterministically)
- Last.fm enrichment: 53 artists → cleaned, ranked genres
- Postgres 15 in Docker (Colima runtime, macOS 13); `raw` → `analytics` separation
- **Metabase** BI on the star schema (full stack: ingest → warehouse → dbt → BI)
- **All four phases complete** (foundation · extract/load · transform · operate)
