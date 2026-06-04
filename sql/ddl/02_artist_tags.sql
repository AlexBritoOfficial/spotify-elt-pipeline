-- Last.fm artist tags, used as a genre proxy.
--
-- Spotify stopped returning `genres` to new apps (2024 Web API changes), so we
-- enrich artists from Last.fm's crowd-sourced top tags instead. Landed raw
-- (JSONB), keyed back to the Spotify artist id so it joins to raw.plays.
CREATE TABLE IF NOT EXISTS raw.artist_tags (
    ingested_at  timestamptz NOT NULL DEFAULT now(),
    artist_id    text,          -- Spotify artist id (join key back to plays)
    artist_name  text,          -- name we queried Last.fm with
    payload      jsonb NOT NULL  -- raw Last.fm artist.getTopTags response
);
