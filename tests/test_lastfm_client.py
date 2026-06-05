"""Unit tests for the Last.fm client. No network — `requests` is monkeypatched."""
import pytest

from src.extract import lastfm_client


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data


def _patch_get(monkeypatch, data, status_code=200):
    monkeypatch.setattr(
        lastfm_client.requests, "get",
        lambda *a, **k: FakeResponse(data, status_code),
    )


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("LASTFM_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Missing LASTFM_API_KEY"):
        lastfm_client.get_artist_tags("Nirvana")


def test_artist_not_found_passes_through(monkeypatch):
    monkeypatch.setenv("LASTFM_API_KEY", "k" * 32)
    _patch_get(monkeypatch, {"error": lastfm_client.ARTIST_NOT_FOUND, "message": "not found"})
    # "artist not found" is returned (not raised) so the caller can skip it
    data = lastfm_client.get_artist_tags("Nobody At All")
    assert data["error"] == lastfm_client.ARTIST_NOT_FOUND


def test_real_error_raises_and_never_leaks_key(monkeypatch):
    secret = "s" * 32
    monkeypatch.setenv("LASTFM_API_KEY", secret)
    _patch_get(monkeypatch, {"error": 10, "message": "Invalid API key"})
    with pytest.raises(RuntimeError) as exc:
        lastfm_client.get_artist_tags("Nirvana")
    assert "Last.fm API error 10" in str(exc.value)
    assert secret not in str(exc.value)  # the API key must never appear in a traceback


def test_success_returns_payload(monkeypatch):
    monkeypatch.setenv("LASTFM_API_KEY", "k" * 32)
    payload = {"toptags": {"tag": [{"name": "grunge", "count": 100}]}}
    _patch_get(monkeypatch, payload)
    assert lastfm_client.get_artist_tags("Nirvana") == payload
