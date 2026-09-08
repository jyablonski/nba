"""Scraper DB helper integration tests against Testcontainers Postgres."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import select, text

from db import get_session, upsert_rows
from models import (
    Game,
    GameExternalId,
    PlayByPlay,
    Player,
    PlayerContract,
    PlayerExternalId,
    PlayerGameLog,
    Team,
    TeamExternalId,
    TeamPayroll,
)

TEAM_HOME = UUID("00000000-0000-4000-8000-000000000201")
TEAM_AWAY = UUID("00000000-0000-4000-8000-000000000202")
PLAYER_ONE = UUID("00000000-0000-4000-8000-000000000301")
GAME_ONE = UUID("00000000-0000-4000-8000-000000000401")


def _teams(now: datetime) -> list[dict]:
    return [
        {
            "team_id": TEAM_HOME,
            "canonical_slug": "test-home",
            "abbreviation": "TST",
            "full_name": "Test Home",
            "city": "Home",
            "nickname": "Home",
            "conference": "West",
            "division": "Pacific",
            "scraped_at": now,
        },
        {
            "team_id": TEAM_AWAY,
            "canonical_slug": "test-away",
            "abbreviation": "AWY",
            "full_name": "Test Away",
            "city": "Away",
            "nickname": "Away",
            "conference": "East",
            "division": "Atlantic",
            "scraped_at": now,
        },
    ]


@pytest.mark.integration
def test_get_session_commits_real_rows(db_session_factory) -> None:
    now = datetime.now(UTC)
    with get_session() as session:
        upsert_rows(session, Team, _teams(now), ["team_id"])

    with db_session_factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM source.teams WHERE team_id = :team_id"),
            {"team_id": TEAM_HOME},
        ).scalar_one()
        assert count == 1


@pytest.mark.integration
def test_get_session_rolls_back_on_error(db_session_factory) -> None:
    with pytest.raises(RuntimeError), get_session() as session:
        session.execute(
            text(
                "INSERT INTO source.teams "
                "(team_id, canonical_slug, abbreviation, full_name, city, nickname, conference, division) "
                "VALUES (:team_id, 'rollback', 'RBK', 'Rollback', 'X', 'X', 'West', 'Pacific')"
            ),
            {"team_id": UUID("00000000-0000-4000-8000-000000000299")},
        )
        raise RuntimeError("boom")

    with db_session_factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM source.teams WHERE abbreviation = 'RBK'")
        ).scalar_one()
        assert count == 0


@pytest.mark.integration
def test_upsert_canonical_entities_and_external_ids(db_session_factory) -> None:
    now = datetime.now(UTC)
    with get_session() as session:
        assert upsert_rows(session, Team, _teams(now), ["team_id"]) == 2
        upsert_rows(
            session,
            Player,
            [
                {
                    "player_id": PLAYER_ONE,
                    "first_name": "Test",
                    "last_name": "Player",
                    "full_name": "Test Player",
                    "is_active": True,
                    "team_id": TEAM_HOME,
                    "scraped_at": now,
                }
            ],
            ["player_id"],
        )
        upsert_rows(
            session,
            Game,
            [
                {
                    "game_id": GAME_ONE,
                    "season": "2024-25",
                    "season_type": "Regular Season",
                    "game_date": date(2024, 11, 1),
                    "home_team_id": TEAM_HOME,
                    "away_team_id": TEAM_AWAY,
                    "home_score": 100,
                    "away_score": 98,
                    "status": "Final",
                    "scraped_at": now,
                }
            ],
            ["game_id"],
        )
        upsert_rows(
            session,
            PlayerExternalId,
            [
                {
                    "player_id": PLAYER_ONE,
                    "provider": "basketball-reference",
                    "external_id": "testpl01",
                }
            ],
            ["provider", "external_id"],
        )
        upsert_rows(
            session,
            TeamExternalId,
            [{"team_id": TEAM_HOME, "provider": "basketball-reference", "external_id": "TST"}],
            ["provider", "external_id"],
        )
        upsert_rows(
            session,
            GameExternalId,
            [{"game_id": GAME_ONE, "provider": "basketball-reference", "external_id": "test-game"}],
            ["provider", "external_id"],
        )
        upsert_rows(
            session,
            PlayerGameLog,
            [
                {
                    "player_id": PLAYER_ONE,
                    "game_id": GAME_ONE,
                    "team_id": TEAM_HOME,
                    "game_date": date(2024, 11, 1),
                    "season": "2024-25",
                    "matchup": "TST vs. AWY",
                    "wl": "W",
                    "min": 32.0,
                    "pts": 25,
                    "reb": 5,
                    "ast": 4,
                    "scraped_at": now,
                }
            ],
            ["player_id", "game_id"],
        )
        upsert_rows(
            session,
            PlayerGameLog,
            [
                {
                    "player_id": PLAYER_ONE,
                    "game_id": GAME_ONE,
                    "team_id": TEAM_HOME,
                    "game_date": date(2024, 11, 1),
                    "season": "2024-25",
                    "matchup": "TST vs. AWY",
                    "wl": "W",
                    "min": 34.0,
                    "pts": 28,
                    "reb": 5,
                    "ast": 4,
                    "scraped_at": now,
                }
            ],
            ["player_id", "game_id"],
        )

    with db_session_factory() as session:
        log = session.execute(
            select(PlayerGameLog).where(
                PlayerGameLog.player_id == PLAYER_ONE,
                PlayerGameLog.game_id == GAME_ONE,
            )
        ).scalar_one()
        assert log.pts == 28
        assert log.min == 34.0


@pytest.mark.integration
def test_upsert_contracts_payroll_and_play_by_play(db_session_factory) -> None:
    now = datetime.now(UTC)
    with get_session() as session:
        upsert_rows(session, Team, _teams(now), ["team_id"])
        upsert_rows(
            session,
            Player,
            [
                {
                    "player_id": PLAYER_ONE,
                    "first_name": "Test",
                    "last_name": "Player",
                    "full_name": "Test Player",
                    "is_active": True,
                    "team_id": TEAM_HOME,
                    "scraped_at": now,
                }
            ],
            ["player_id"],
        )
        upsert_rows(
            session,
            Game,
            [
                {
                    "game_id": GAME_ONE,
                    "season": "2024-25",
                    "season_type": "Regular Season",
                    "game_date": date(2024, 11, 1),
                    "home_team_id": TEAM_HOME,
                    "away_team_id": TEAM_AWAY,
                    "home_score": 100,
                    "away_score": 98,
                    "status": "Final",
                    "scraped_at": now,
                }
            ],
            ["game_id"],
        )
        upsert_rows(
            session,
            PlayerContract,
            [
                {
                    "player_id": PLAYER_ONE,
                    "team_id": TEAM_HOME,
                    "player_name": "Test Player",
                    "player_name_normalized": "test player",
                    "season": "2024-25",
                    "salary": 50000000,
                    "is_fully_guaranteed": True,
                    "remaining_guaranteed": 50000000,
                    "player_age": 25,
                    "source_url": "https://www.basketball-reference.com/contracts/TST.html",
                    "scraped_at": now,
                }
            ],
            ["player_id", "team_id", "season"],
        )
        upsert_rows(
            session,
            TeamPayroll,
            [
                {
                    "team_id": TEAM_HOME,
                    "season": "2024-25",
                    "total_salary": 50000000,
                    "remaining_guaranteed": 50000000,
                    "source_url": "https://www.basketball-reference.com/contracts/TST.html",
                    "scraped_at": now,
                }
            ],
            ["team_id", "season"],
        )
        upsert_rows(
            session,
            PlayByPlay,
            [
                {
                    "game_id": GAME_ONE,
                    "season": "2024-25",
                    "action_number": 4,
                    "action_id": 400,
                    "period": 1,
                    "clock": "PT11M32.00S",
                    "score_home": 2,
                    "score_away": 0,
                    "team_id": TEAM_HOME,
                    "player_id": PLAYER_ONE,
                    "action_type": "2pt",
                    "sub_type": "Jump Shot",
                    "description": "Test Player 18' Jump Shot (2 PTS)",
                    "extras": {"shotResult": "Made"},
                    "scraped_at": now,
                }
            ],
            ["game_id", "action_number", "action_id"],
        )

    with db_session_factory() as session:
        row = session.execute(
            text(
                "SELECT description, extras->>'shotResult' "
                "FROM source.play_by_play WHERE game_id = :game_id AND action_number = 4"
            ),
            {"game_id": GAME_ONE},
        ).one()
        assert row[0] == "Test Player 18' Jump Shot (2 PTS)"
        assert row[1] == "Made"
