from datetime import date, datetime

import pytest

from scrapers import (
    current_season,
    dataset_rows,
    generate_seasons,
    matchup_is_home,
    matchup_row_is_home,
    matchup_team_abbr,
    nba_date,
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
def test_season_helpers() -> None:
    assert season_from_start_year(2024) == "2024-25"
    assert season_start_year("2024-25") == 2024
    assert generate_seasons("2023-24", "2024-25") == ["2023-24", "2024-25"]
    with pytest.raises(ValueError):
        generate_seasons("2024-25", "2023-24")


@pytest.mark.unit
def test_current_season_october_boundary() -> None:
    assert current_season(date(2025, 10, 1)) == "2025-26"
    assert current_season(date(2026, 1, 15)) == "2025-26"


@pytest.mark.unit
def test_parse_seasons() -> None:
    assert parse_seasons("2024-25, 2023-24") == ["2024-25", "2023-24"]
    assert parse_seasons("2010-11,2024-25") == ["2010-11", "2024-25"]
    assert parse_seasons(None) == [current_season()]
    assert parse_seasons("  ,  ") == [current_season()]


@pytest.mark.unit
def test_parse_game_date_formats() -> None:
    assert parse_game_date(date(2024, 10, 22)) == date(2024, 10, 22)
    assert parse_game_date(datetime(2024, 10, 22, 19, 0)) == date(2024, 10, 22)
    assert parse_game_date("2024-10-22") == date(2024, 10, 22)
    assert parse_game_date("Oct 22, 2024") == date(2024, 10, 22)
    assert parse_game_date("October 22, 2024") == date(2024, 10, 22)
    assert parse_game_date("10/22/2024") == date(2024, 10, 22)
    with pytest.raises(ValueError):
        parse_game_date("not-a-date")


@pytest.mark.unit
def test_parse_minutes_and_numbers() -> None:
    assert parse_minutes(None) is None
    assert parse_minutes("") is None
    assert parse_minutes(36) == 36.0
    assert parse_minutes("36:30") == 36.5
    assert parse_minutes("not") is None
    assert parse_minutes("12.5") == 12.5
    assert to_int("") is None
    assert to_int("12.0") == 12
    assert to_int("x") is None
    assert to_float("") is None
    assert to_float("1.5") == 1.5
    assert to_float("x") is None
    assert to_str(None) is None
    assert to_str("  clip  ") == "clip"
    assert to_str("  ") is None


@pytest.mark.unit
def test_row_get_and_dataset_rows() -> None:
    assert row_get({"GAME_ID": "1"}, "game_id") == "1"
    assert row_get({"a": 1}, "b") is None
    assert dataset_rows({"PlayerGameLog": [{"id": 1}]}, "PlayerGameLog") == [{"id": 1}]
    assert dataset_rows({"other": [{"id": 2}]}) == [{"id": 2}]
    assert dataset_rows({"x": "nope"}) == []


@pytest.mark.unit
def test_matchup_helpers() -> None:
    assert matchup_is_home("LAC vs. GSW") is True
    assert matchup_is_home("LAC @ CHI") is False
    assert matchup_team_abbr("LAC vs. GSW") == "LAC"
    assert matchup_team_abbr("") is None
    assert parse_matchup_sides("DAL @ DET") == ("DET", "DAL")
    assert parse_matchup_sides("DET vs. DAL") == ("DET", "DAL")
    assert parse_matchup_sides("NYK vs ORL") == ("NYK", "ORL")
    assert parse_matchup_sides("") == (None, None)
    assert parse_matchup_sides("All-Star Game") == (None, None)
    assert matchup_row_is_home("DAL @ DET", "DET") is True
    assert matchup_row_is_home("DAL @ DET", "DAL") is False
    assert matchup_row_is_home("SAS @ OKC", "OKC") is True
    assert matchup_row_is_home("SAS @ OKC", "SAS") is False
    assert matchup_row_is_home("DET vs. DAL", None) is True
    assert nba_date(date(2024, 10, 22)) == "2024-10-22"
