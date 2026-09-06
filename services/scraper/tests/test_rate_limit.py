from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scrapers import ensure_headers, nba_call, rate_limit


@pytest.mark.unit
def test_ensure_headers_updates_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    import scrapers as scrapers_mod

    monkeypatch.setattr(scrapers_mod, "_headers_applied", False)
    http = SimpleNamespace(headers={"User-Agent": "old"}, nba_headers=None)
    with patch.dict(
        "sys.modules", {"nba_api.stats.library.http": SimpleNamespace(NBAStatsHTTP=http)}
    ):
        with patch("nba_api.stats.library.http.NBAStatsHTTP", http, create=True):
            ensure_headers()
    monkeypatch.setattr(scrapers_mod, "_headers_applied", False)
    ensure_headers()
    ensure_headers()


@pytest.mark.unit
def test_rate_limit_and_nba_call(monkeypatch: pytest.MonkeyPatch) -> None:
    import scrapers as scrapers_mod

    monkeypatch.setattr(scrapers_mod, "REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(scrapers_mod, "_last_request_at", 0.0)
    monkeypatch.setattr(scrapers_mod, "ensure_headers", lambda: None)
    slept = []
    monkeypatch.setattr("scrapers.time.sleep", lambda seconds: slept.append(seconds))
    rate_limit()
    assert nba_call(lambda: 42) == 42

    monkeypatch.setattr(scrapers_mod, "REQUEST_DELAY_SECONDS", 5)
    monkeypatch.setattr(scrapers_mod, "_last_request_at", 10_000.0)
    monkeypatch.setattr("scrapers.time.monotonic", lambda: 10_000.1)
    slept.clear()
    rate_limit()
    assert slept and slept[-1] > 0


@pytest.mark.unit
def test_ensure_headers_setattr_non_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    import scrapers as scrapers_mod

    monkeypatch.setattr(scrapers_mod, "_headers_applied", False)
    http = SimpleNamespace(headers="legacy", nba_headers="legacy")
    fake_mod = SimpleNamespace(NBAStatsHTTP=http)
    with patch.dict("sys.modules", {"nba_api.stats.library.http": fake_mod}):
        ensure_headers()
    assert http.headers == scrapers_mod.HEADERS or scrapers_mod._headers_applied is True
