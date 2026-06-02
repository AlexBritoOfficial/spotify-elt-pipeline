"""One-time Spotify OAuth flow.

Phase 2: run this once. It opens a browser, you approve, and spotipy caches a
refresh token so later runs authenticate non-interactively. Put the resulting
token in .env as SPOTIFY_REFRESH_TOKEN.

    python -m src.extract.authorize
"""

# TODO (Phase 2):
#   - load SPOTIFY_CLIENT_ID / SECRET from .env (python-dotenv)
#   - build a spotipy.oauth2.SpotifyOAuth with scope
#     "user-read-recently-played user-top-read"
#   - trigger the flow so the refresh token gets cached
