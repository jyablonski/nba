from types import SimpleNamespace

import pytest

import scrapers


@pytest.mark.unit
def test_bref_rate_limit_sleeps_when_requests_are_too_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scrapers, "BREF_REQUEST_DELAY_SECONDS", 5)
    monkeypatch.setattr(scrapers, "_last_bref_request_at", 100.0)
    monkeypatch.setattr(scrapers.time, "monotonic", lambda: 100.1)
    slept: list[float] = []
    monkeypatch.setattr(scrapers.time, "sleep", slept.append)
    scrapers.bref_rate_limit()
    assert slept == [pytest.approx(4.9)]


@pytest.mark.unit
def test_bref_get_passes_headers_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scrapers, "BREF_REQUEST_DELAY_SECONDS", 0)
    calls: list[tuple] = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(status_code=200, text="ok")

    assert scrapers.bref_get("https://example.test", get=fake_get) == "ok"
    assert calls[0][0] == ("https://example.test",)
    assert calls[0][1]["headers"] == scrapers.BREF_HEADERS
    assert calls[0][1]["timeout"] == scrapers.BREF_REQUEST_TIMEOUT
