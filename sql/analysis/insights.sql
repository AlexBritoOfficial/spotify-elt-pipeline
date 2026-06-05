-- Sample analytics on the star schema (analytics.* built by dbt).
-- Run any block against the warehouse, e.g.:
--   docker compose exec -T postgres psql -U postgres -d spotify -f - < sql/analysis/insights.sql

-- 1. Headline summary --------------------------------------------------------
SELECT
    count(*)                              AS total_plays,
    count(DISTINCT track_key)             AS distinct_tracks,
    count(DISTINCT artist_key)            AS distinct_artists,
    round(sum(duration_ms) / 3600000.0, 1) AS total_hours
FROM analytics.fact_plays;

-- 2. Top genres by number of plays ------------------------------------------
SELECT g.genre_name,
       count(*) AS plays
FROM analytics.fact_plays f
JOIN analytics.bridge_artist_genre b USING (artist_key)
JOIN analytics.dim_genre g           USING (genre_key)
GROUP BY g.genre_name
ORDER BY plays DESC
LIMIT 10;

-- 3. Top artists by number of plays -----------------------------------------
SELECT a.artist_name,
       a.primary_genre,
       count(*) AS plays
FROM analytics.fact_plays f
JOIN analytics.dim_artist a USING (artist_key)
GROUP BY a.artist_name, a.primary_genre
ORDER BY plays DESC
LIMIT 10;

-- 4. Most-played tracks ------------------------------------------------------
SELECT t.track_name,
       t.artist_id,
       t.album_name,
       count(*) AS plays
FROM analytics.fact_plays f
JOIN analytics.dim_track t USING (track_key)
GROUP BY t.track_name, t.artist_id, t.album_name
ORDER BY plays DESC
LIMIT 10;

-- 5. Listening by weekday (uses dim_date) -----------------------------------
SELECT d.day_name,
       d.is_weekend,
       count(*)                              AS plays,
       round(sum(f.duration_ms) / 60000.0, 1) AS minutes
FROM analytics.fact_plays f
JOIN analytics.dim_date d USING (date_key)
GROUP BY d.day_of_week, d.day_name, d.is_weekend
ORDER BY d.day_of_week;

-- 6. Plays by album release decade ------------------------------------------
SELECT (left(t.album_release_date, 3) || '0s') AS release_decade,
       count(*)                                AS plays
FROM analytics.fact_plays f
JOIN analytics.dim_track t USING (track_key)
WHERE t.album_release_date ~ '^[0-9]{4}'
GROUP BY release_decade
ORDER BY release_decade;
