"""Integration tests for idempotent loading.

These exercise the loader's `INSERT ... WHERE NOT EXISTS` dedup pattern against
the real Postgres container. They skip cleanly if the database isn't reachable,
and never persist writes (temp table + rollback).
"""
import pytest
from psycopg2.extras import Json

from src.load.load_to_postgres import get_connection


@pytest.fixture
def conn():
    try:
        c = get_connection()
    except Exception as e:  # container down / not reachable
        pytest.skip(f"Postgres not available: {e}")
    try:
        yield c
    finally:
        c.rollback()  # never persist anything a test wrote
        c.close()


def test_insert_is_idempotent_on_played_at(conn):
    """Re-inserting the same play (same played_at) must not create a duplicate."""
    sql = """
        INSERT INTO _dedup_probe (played_at, payload)
        SELECT %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM _dedup_probe WHERE played_at = %s)
    """
    ts = "2026-01-01T00:00:00Z"
    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE _dedup_probe (played_at timestamptz, payload jsonb)")
        cur.execute(sql, (ts, Json({"x": 1}), ts))
        first = cur.rowcount
        cur.execute(sql, (ts, Json({"x": 1}), ts))
        second = cur.rowcount
        cur.execute("SELECT count(*) FROM _dedup_probe")
        total = cur.fetchone()[0]
    assert first == 1   # first insert lands
    assert second == 0  # second is skipped by WHERE NOT EXISTS
    assert total == 1


def test_raw_plays_has_no_duplicate_played_at(conn):
    """Invariant: dedup keeps raw.plays unique on its natural key (played_at)."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) - count(DISTINCT played_at) FROM raw.plays")
        dupes = cur.fetchone()[0]
    assert dupes == 0
