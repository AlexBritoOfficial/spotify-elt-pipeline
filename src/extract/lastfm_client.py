"""Thin wrapper around the Last.fm API — artist tags as a genre proxy.

Spotify stopped returning `genres` to new apps, so we enrich artists with
Last.fm's crowd-sourced top tags (e.g. "rock", "grunge", "alternative").
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"

# Last.fm error code for "artist not found" — callers may safely skip these.
ARTIST_NOT_FOUND = 6


def get_artist_tags(artist_name: str) -> dict:
    """Return Last.fm's top-tags JSON for an artist (landed raw).

    Last.fm reports failures in the JSON body (e.g. {"error": 6, ...}). Real
    errors (bad key, rate limit) are raised with a message that never includes
    the API key; "artist not found" is passed through for the caller to skip.
    """
    api_key = os.getenv("LASTFM_API_KEY")
    if not api_key:
        raise RuntimeError("Missing LASTFM_API_KEY — check your .env")
    params = {
        "method": "artist.gettoptags",
        "artist": artist_name,
        "api_key": api_key,
        "autocorrect": 1,        # let Last.fm fix minor name mismatches
        "format": "json",
    }
    response = requests.get(LASTFM_API_URL, params=params, timeout=10)
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"Last.fm returned non-JSON (HTTP {response.status_code})")
    error = data.get("error")
    if error and error != ARTIST_NOT_FOUND:
        # Deliberately do NOT echo the request URL/key in the message.
        raise RuntimeError(f"Last.fm API error {error}: {data.get('message')}")
    return data
