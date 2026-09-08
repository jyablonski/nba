from datetime import date, datetime
from types import SimpleNamespace

import pytest

from scrapers import (
    BREF_HEADERS,
    BREF_PROVIDER,
    BrefHTTPError,
    bref_get,
    bref_rate_limit,
    current_season,
    dataset_rows,
    generate_seasons,
    parse_game_date,
    parse_matchup_sides,
    parse_minutes,
    parse_seasons,
    row_get,
    season_from_start_year,
    season_start_year,
    to_float,
    to_int,
    to_str,
)


@pytest.mark.unit
def test_bref_identity_and_season_helpers() -> None:
    assert BREF_PROVIDER == "basketball-reference"
    assert BREF_HEADERS["User-Agent"]
    assert season_from_start_year(2024) == "2024-25"
    assert season_start_year("2024-25") == 2024
    assert generate_seasons("2023-24", "2024-25") == ["2023-24", "2024-25"]
    with pytest.raises(ValueError):
        generate_seasons("2024-25", "2023-24")


@pytest.mark.unit
def test_current_season_and_parse_seasons() -> None:
    assert current_season(date(2025, 10, 1)) == "2025-26"
    assert current_season(date(2026, 1, 15)) == "2025-26"
    assert parse_seasons("2024-25, 2023-24") == ["2024-25", "2023-24"]
    assert parse_seasons("  ,  ") == [current_season()]


@pytest.mark.unit
def test_parse_game_date_and_numeric_helpers() -> None:
    assert parse_game_date(date(2024, 10, 22)) == date(2024, 10, 22)
    assert parse_game_date(datetime(2024, 10, 22, 19, 0)) == date(2024, 10, 22)
    assert parse_game_date("Oct 22, 2024") == date(2024, 10, 22)
    with pytest.raises(ValueError):
        parse_game_date("not-a-date")
    assert parse_minutes("36:30") == 36.5
    assert parse_minutes("not") is None
    assert to_int("12.0") == 12
    assert to_float("1.5") == 1.5
    assert to_str("  clip  ") == "clip"


@pytest.mark.unit
def test_row_and_payload_helpers() -> None:
    assert row_get({"GAME_ID": "1"}, "game_id") == "1"
    assert row_get({"a": 1}, "b") is None
    assert dataset_rows({"PlayerGameLog": [{"id": 1}]}, "PlayerGameLog") == [{"id": 1}]
    assert dataset_rows({"x": "nope"}) == []
    assert parse_matchup_sides("DAL @ DET") == ("DET", "DAL")
    assert parse_matchup_sides("DET vs. DAL") == ("DET", "DAL")
    assert parse_matchup_sides("All-Star Game") == (None, None)


@pytest.mark.unit
def test_bref_rate_limit_and_http(monkeypatch: pytest.MonkeyPatch) -> None:
    import scrapers

    monkeypatch.setattr(scrapers, "BREF_REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(scrapers, "_last_bref_request_at", 0.0)
    bref_rate_limit()
    response = SimpleNamespace(status_code=200, text="<html>ok</html>")
    assert (
        bref_get("https://example.test/x", get=lambda *args, **kwargs: response)
        == "<html>ok</html>"
    )
    error = SimpleNamespace(status_code=403, text="nope")
    with pytest.raises(BrefHTTPError, match="HTTP 403"):
        bref_get("https://example.test/x", get=lambda *args, **kwargs: error)
