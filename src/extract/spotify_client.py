"""Thin wrapper around the Spotify Web API (spotipy)."""
import os

from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPE = "user-read-recently-played user-top-read"


def get_client() -> Spotify:
    """Build an authenticated Spotify client.

    Reads the cached token from .cache (created by authorize.py), so this
    runs silently — no browser — as long as you've authorized once.
    """
    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=SCOPE,
        cache_path=".cache",
    )
    return Spotify(auth_manager=auth_manager)


def get_recent_plays(limit: int = 50) -> list[dict]:
    """Return recently-played items, most recent first.

    Spotify caps this endpoint at 50 items per call.
    """
    sp = get_client()
    response = sp.current_user_recently_played(limit=limit)
    return response["items"]