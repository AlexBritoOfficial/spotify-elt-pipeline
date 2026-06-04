"""Land raw Spotify + Last.fm payloads into Postgres (the raw schema)."""
import os
import time

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

from src.extract.spotify_client import get_recent_plays
from src.extract.lastfm_client import get_artist_tags

load_dotenv()


def get_connection():
    """Open a connection to the Postgres container."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def load_recent_plays() -> int:
    """Pull recent plays and insert only the new ones. Returns # inserted."""
    plays = get_recent_plays(limit=50)
    inserted = 0
    conn = get_connection()
    try:
        with conn:  # commits on success, rolls back on any error
            with conn.cursor() as cur:
                for play in plays:
                    cur.execute(
                        """
                        INSERT INTO raw.plays (played_at, payload)
                        SELECT %s, %s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM raw.plays WHERE played_at = %s
                        )
                        """,
                        (play["played_at"], Json(play), play["played_at"]),
                    )
                    inserted += cur.rowcount
    finally:
        conn.close()
    return inserted


def _distinct_artists_from_plays(cur) -> list[tuple[str, str]]:
    """Distinct (artist_id, artist_name) pairs referenced by loaded plays."""
    cur.execute(
        """
        SELECT DISTINCT artist->>'id'   AS artist_id,
                        artist->>'name' AS artist_name
        FROM raw.plays,
             LATERAL jsonb_array_elements(payload->'track'->'artists') AS artist
        WHERE artist->>'id' IS NOT NULL
        """
    )
    return cur.fetchall()


def _existing_tag_artist_ids(cur) -> set:
    cur.execute("SELECT artist_id FROM raw.artist_tags")
    return {row[0] for row in cur.fetchall()}


def load_artist_tags() -> int:
    """Fetch Last.fm tags (genre proxy) for artists not yet stored.

    Reads the artist list and fetches from Last.fm *outside* any DB
    transaction (slow network), then inserts the results in one short
    transaction. Returns the number of new rows inserted.
    """
    conn = get_connection()
    try:
        # 1. Which artists do we still need? (read, then release the txn)
        with conn:
            with conn.cursor() as cur:
                artists = _distinct_artists_from_plays(cur)
                have = _existing_tag_artist_ids(cur)
        new = [(aid, name) for aid, name in artists if aid not in have]

        # 2. Fetch from Last.fm with no DB transaction held open
        fetched = []
        for artist_id, artist_name in new:
            payload = get_artist_tags(artist_name)
            if payload.get("error"):  # e.g. artist not found on Last.fm
                continue
            fetched.append((artist_id, artist_name, payload))
            time.sleep(0.25)  # be polite to the Last.fm API

        # 3. Insert everything in one transaction (idempotent)
        inserted = 0
        with conn:
            with conn.cursor() as cur:
                for artist_id, artist_name, payload in fetched:
                    cur.execute(
                        """
                        INSERT INTO raw.artist_tags (artist_id, artist_name, payload)
                        SELECT %s, %s, %s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM raw.artist_tags WHERE artist_id = %s
                        )
                        """,
                        (artist_id, artist_name, Json(payload), artist_id),
                    )
                    inserted += cur.rowcount
        return inserted
    finally:
        conn.close()


if __name__ == "__main__":
    new_plays = load_recent_plays()
    new_tags = load_artist_tags()
    print(f"✅ Inserted {new_plays} new play(s) and {new_tags} new artist-tag row(s)")
