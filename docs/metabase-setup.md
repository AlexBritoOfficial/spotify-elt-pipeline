# Metabase setup (BI dashboard)

Metabase is the serving layer: it points at the `analytics` star schema and lets
you build charts/dashboards with no code. It runs as a `docker-compose` service
alongside Postgres.

## 1. Start it

```bash
docker compose up -d            # brings up postgres + metabase
```

First boot takes ~1–2 minutes to initialize. Then open **http://localhost:3000**.

## 2. Create the admin account
On first run Metabase asks you to create a local admin user (name / email /
password). This is local-only — nothing leaves your machine.

## 3. Connect to the warehouse
When prompted to add your data (or later via **Admin settings → Databases →
Add database**), choose **PostgreSQL** and enter:

| Field | Value | Note |
|---|---|---|
| Display name | `Spotify` | anything |
| Host | **`postgres`** | the compose **service name**, *not* `localhost` — Metabase reaches Postgres over the Docker network |
| Port | `5432` | |
| Database name | `spotify` | |
| Username | `postgres` | (compose default) |
| Password | `postgres` | (compose default) |
| Schemas | `analytics` (optional) | restrict to just the marts |

Save — Metabase will scan the schema and find `fact_plays`, `dim_artist`,
`dim_track`, `dim_genre`, `dim_date`, and `bridge_artist_genre`.

## 4. Build the dashboard
The queries in [`../sql/analysis/insights.sql`](../sql/analysis/insights.sql)
map directly to good starter charts. Create each as a "Question" (use the visual
query builder, or paste the SQL via **+ New → SQL query**), then add them to a
dashboard:

- **Headline numbers** — total plays / distinct tracks / total hours (Number cards)
- **Top genres by plays** — bar chart (`fact_plays` ⋈ `bridge_artist_genre` ⋈ `dim_genre`)
- **Top artists by plays** — bar chart (⋈ `dim_artist`)
- **Plays by weekday** — bar chart (⋈ `dim_date`, ordered by `day_of_week`)
- **Plays by release decade** — bar chart (⋈ `dim_track`)

Tip: starting from the **dimension tables** in the query builder makes the star
schema's joins automatic — that's the payoff of the dimensional model.

## 5. Capture it
Screenshot the finished dashboard into the README (e.g. `docs/img/dashboard.png`)
so the project shows a visible result.

## Notes
- Metabase's own data persists in the `metabase_data` Docker volume — survives
  `docker compose down`, wiped by `docker compose down -v`.
- The image is `metabase/metabase:latest`; pin a tag in `docker-compose.yml`
  (e.g. `:v0.50.26`) if you want fully reproducible builds.
- Stop just Metabase with `docker compose stop metabase` (keeps Postgres up).
