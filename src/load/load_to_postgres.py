"""Land raw Spotify payloads into Postgres (the raw schema)."""
import os

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

from src.extract.spotify_client import get_recent_plays

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


if __name__ == "__main__":
    count = load_recent_plays()
    print(f"✅ Inserted {count} new play(s) into raw.plays")