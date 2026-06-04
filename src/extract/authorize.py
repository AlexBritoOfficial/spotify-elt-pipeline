"""One-time Spotify OAuth flow.

Phase 2: run this once. It opens a browser, you approve, and spotipy caches a
refresh token so later runs authenticate non-interactively. Put the resulting
token in .env as SPOTIFY_REFRESH_TOKEN.

    python -m src.extract.authorize
"""

import os

from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from spotipy import Spotify

load_dotenv()

spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

if not spotify_client_id or not spotify_client_secret or not spotify_redirect_uri:
    raise RuntimeError(
        "Missing SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET / SPOTIFY_REDIRECT_URI — check your .env"
    )

SCOPE = "user-read-recently-played user-top-read"

auth_manager = SpotifyOAuth(
    client_id=spotify_client_id,
    client_secret=spotify_client_secret,
    redirect_uri=spotify_redirect_uri,
    scope=SCOPE,
    cache_path=".cache"
)

sp = Spotify(auth_manager=auth_manager)

recently_played = sp.current_user_recently_played(limit=1)

if recently_played["items"]:
    track = recently_played["items"][0]["track"]
    print(f"✅ Authenticated! Most recent play: {track['name']} — {track['artists'][0]['name']}")
else:
    print("✅ Authenticated! (No recent plays found on your account.)")


