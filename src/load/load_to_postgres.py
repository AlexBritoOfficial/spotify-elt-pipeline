"""Land raw Spotify payloads into Postgres (the `raw` schema).

Phase 2: insert each play into raw.plays as a JSONB row, idempotently (skip any
         whose played_at already exists). Upsert artist payloads into
         raw.artists. Extraction stays "dumb" — no reshaping here.
"""

# TODO (Phase 2): connect with psycopg2 using the POSTGRES_* vars from .env,
#                 insert plays idempotently (dedup on played_at), upsert artists
