"""Thin wrapper around the Spotify Web API (spotipy).

Phase 2: recently-played + top tracks/artists.
Phase 2: artist metadata (genres), batched up to 50 IDs per call, with 429
         rate-limit handling.
"""

# TODO (Phase 2): get_recent_plays() -> wraps sp.current_user_recently_played()
# TODO (Phase 2): get_artists_batch(ids) -> wraps sp.artists(), batches of 50,
#                 sleeps + retries once on HTTP 429
