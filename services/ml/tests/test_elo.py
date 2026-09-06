from datetime import date

import pytest

from elo import (
    HOME_ADVANTAGE,
    INITIAL_RATING,
    GameRow,
    expected_home_win,
    fit_ratings,
    game_row_from_mapping,
    regress_ratings,
    score_games,
    walk_forward,
)


def _game(
    game_id: str,
    day: date,
    season: str,
    home: int,
    away: int,
    home_won: bool | None,
) -> GameRow:
    return GameRow(
        game_id=game_id,
        game_date=day,
        season=season,
        home_team_id=home,
        away_team_id=away,
        home_won=home_won,
    )


@pytest.mark.unit
def test_equal_teams_home_favored() -> None:
    prob = expected_home_win(INITIAL_RATING, INITIAL_RATING)
    assert 0.5 < prob < 0.7
    assert HOME_ADVANTAGE == 100.0


@pytest.mark.unit
def test_walk_forward_updates_after_result_not_before() -> None:
    games = [
        _game("1", date(2024, 10, 22), "2024-25", 1, 2, True),
        _game("2", date(2024, 10, 23), "2024-25", 1, 2, True),
    ]
    preds, ratings = walk_forward(games)
    assert preds[0] == expected_home_win(INITIAL_RATING, INITIAL_RATING)
    assert ratings[1] > INITIAL_RATING
    assert ratings[2] < INITIAL_RATING
    assert preds[1] > preds[0]


@pytest.mark.unit
def test_walk_forward_does_not_use_same_game_score() -> None:
    games = [
        _game("1", date(2024, 10, 22), "2024-25", 10, 20, True),
        _game("2", date(2024, 10, 23), "2024-25", 30, 40, None),
    ]
    preds, _ratings = walk_forward(games)
    assert preds[1] == expected_home_win(INITIAL_RATING, INITIAL_RATING)


@pytest.mark.unit
def test_season_reset_regresses_toward_mean() -> None:
    ratings = {1: 1700.0, 2: 1300.0}
    reset = regress_ratings(ratings)
    assert INITIAL_RATING < reset[1] < 1700.0
    assert 1300.0 < reset[2] < INITIAL_RATING


@pytest.mark.unit
def test_fit_then_score_upcoming() -> None:
    history = [
        _game("1", date(2023, 10, 22), "2023-24", 1, 2, True),
        _game("2", date(2023, 10, 23), "2023-24", 1, 2, True),
    ]
    ratings = fit_ratings(history)
    upcoming = [_game("3", date(2024, 10, 22), "2024-25", 1, 2, None)]
    preds = score_games(upcoming, ratings)
    assert 0.5 < preds[0] < 1.0


@pytest.mark.unit
def test_game_row_from_mapping_winner_location() -> None:
    row = {
        "game_id": "002",
        "game_date": date(2024, 10, 22),
        "season": "2024-25",
        "home_team_id": 1,
        "away_team_id": 2,
        "winner_location": "away",
    }
    parsed = game_row_from_mapping(row)
    assert parsed.home_won is False
    parsed_home = game_row_from_mapping({**row, "winner_location": "home"})
    assert parsed_home.home_won is True
