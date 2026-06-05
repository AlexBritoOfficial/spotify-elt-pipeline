# transform

Phase 3 transformation logic.

The dbt project itself lives at the **repo root in `../../dbt/`** (kept out of
this importable Python package). It reshapes `raw` into the `analytics` star
schema:

- `stg_plays`, `stg_artist_tags` — flatten/unnest the raw JSONB (views)
- `int_artist_genres` — clean the Last.fm folksonomy tags (view)
- `dim_artist`, `dim_track`, `dim_genre` — dimensions
- `bridge_artist_genre` — many-to-many artist↔genre
- `fact_plays` — grain: one play event

Run it:

```bash
cd dbt
dbt seed   --profiles-dir .   # load the non-genre stopword list
dbt run    --profiles-dir .   # build staging -> marts
dbt test   --profiles-dir .   # run schema + relationship tests
```
