# Spotify ELT Pipeline — STAR Interview Summary

A reference for talking about this project in interviews using the **STAR**
framework (Situation · Task · Action · Result). Start with the headline story,
then pull a specific story for whatever the interviewer asks (debugging,
security, working under constraints).

**One-liner:** A local, reproducible **ELT pipeline** that extracts my personal
Spotify listening history via the Web API, lands it raw (JSONB) in Postgres, and
prepares it for in-warehouse transformation — all running in Docker.

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

## Concepts & practices to name-drop
- **ELT vs ETL**; raw-first, replayable design
- **Idempotent loads** (dedup on a natural key)
- **JSONB** for schema-flexible raw storage
- **Docker Compose** for reproducible infrastructure
- **OAuth** refresh-token flow
- **Separation of concerns** (extract vs load modules)
- **Git/GitHub workflow** (branches, PRs) and **secret management**

## Quick facts / metrics
- 50 plays loaded; idempotent (0 duplicates on re-run)
- Postgres 15 in Docker (Colima runtime, macOS 13)
- `raw` → `analytics` schema separation
- Phase 1 (foundation) + Phase 2 core (extract/load of plays) complete
