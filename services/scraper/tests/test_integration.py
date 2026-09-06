"""Scraper DB helper integration tests against Testcontainers Postgres."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select, text

from db import get_session, upsert_rows
from models import Game, PlayByPlay, Player, PlayerContract, PlayerGameLog, Team, TeamPayroll


@pytest.mark.integration
def test_get_session_commits_real_rows(db_session_factory) -> None:
    now = datetime.now(UTC)
    with get_session() as session:
        upsert_rows(
            session,
            Team,
            [
                {
                    "team_id": 100,
                    "abbreviation": "TST",
                    "full_name": "Test Team",
                    "city": "Testville",
                    "nickname": "Testers",
                    "conference": "West",
                    "division": "Pacific",
                    "scraped_at": now,
                }
            ],
            ["team_id"],
        )

    with db_session_factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM source.teams WHERE team_id = 100")
        ).scalar_one()
        assert count == 1


@pytest.mark.integration
def test_get_session_rollbacks_on_error(db_session_factory) -> None:
    with pytest.raises(RuntimeError), get_session() as session:
        session.execute(
            text(
                "INSERT INTO source.teams "
                "(team_id, abbreviation, full_name, city, nickname, conference, division) "
                "VALUES (101, 'X', 'X', 'X', 'X', 'West', 'Pacific')"
            )
        )
        raise RuntimeError("boom")

    with db_session_factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM source.teams WHERE team_id = 101")
        ).scalar_one()
        assert count == 0


@pytest.mark.integration
def test_upsert_teams_players_games_logs(db_session_factory) -> None:
    now = datetime.now(UTC)

    with get_session() as session:
        assert (
            upsert_rows(
                session,
                Team,
                [
                    {
                        "team_id": 1,
                        "abbreviation": "AAA",
                        "full_name": "Team A",
                        "city": "A",
                        "nickname": "A",
                        "conference": "West",
                        "division": "Pacific",
                        "scraped_at": now,
                    },
                    {
                        "team_id": 2,
                        "abbreviation": "BBB",
                        "full_name": "Team B",
                        "city": "B",
                        "nickname": "B",
                        "conference": "East",
                        "division": "Atlantic",
                        "scraped_at": now,
                    },
                ],
                ["team_id"],
            )
            == 2
        )

        # ON CONFLICT DO UPDATE
        upsert_rows(
            session,
            Team,
            [
                {
                    "team_id": 1,
                    "abbreviation": "AAA",
                    "full_name": "Team A",
                    "city": "Updated",
                    "nickname": "A",
                    "conference": "West",
                    "division": "Pacific",
                    "scraped_at": now,
                }
            ],
            ["team_id"],
        )
        team = session.execute(select(Team).where(Team.team_id == 1)).scalar_one()
        assert team.city == "Updated"

        upsert_rows(
            session,
            Player,
            [
                {
                    "player_id": 10,
                    "first_name": "Test",
                    "last_name": "Player",
                    "full_name": "Test Player",
                    "is_active": True,
                    "team_id": 1,
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
                    "game_id": "0022400999",
                    "season": "2024-25",
                    "season_type": "Regular Season",
                    "game_date": date(2024, 11, 1),
                    "home_team_id": 1,
                    "away_team_id": 2,
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
            PlayerGameLog,
            [
                {
                    "player_id": 10,
                    "game_id": "0022400999",
                    "team_id": 1,
                    "game_date": date(2024, 11, 1),
                    "season": "2024-25",
                    "matchup": "AAA vs. BBB",
                    "wl": "W",
                    "min": 30.0,
                    "pts": 20,
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
                    "player_id": 10,
                    "game_id": "0022400999",
                    "team_id": 1,
                    "game_date": date(2024, 11, 1),
                    "season": "2024-25",
                    "matchup": "AAA vs. BBB",
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
        log = session.execute(
            select(PlayerGameLog).where(
                PlayerGameLog.player_id == 10,
                PlayerGameLog.game_id == "0022400999",
            )
        ).scalar_one()
        assert log.pts == 25
        assert log.min == 32.0


@pytest.mark.integration
def test_upsert_player_contracts_and_team_payroll(db_session_factory) -> None:
    now = datetime.now(UTC)
    with get_session() as session:
        assert (
            upsert_rows(
                session,
                PlayerContract,
                [
                    {
                        "bref_player_slug": "curryst01",
                        "player_name": "Stephen Curry",
                        "player_name_normalized": "stephen curry",
                        "bref_team_abbreviation": "GSW",
                        "nba_team_abbreviation": "GSW",
                        "season": "2024-25",
                        "salary": 50000000,
                        "is_fully_guaranteed": True,
                        "remaining_guaranteed": 50000000,
                        "player_age": 36,
                        "source_url": "https://www.basketball-reference.com/contracts/GSW.html",
                        "scraped_at": now,
                    }
                ],
                ["bref_player_slug", "bref_team_abbreviation", "season"],
            )
            == 1
        )
        upsert_rows(
            session,
            PlayerContract,
            [
                {
                    "bref_player_slug": "curryst01",
                    "player_name": "Stephen Curry",
                    "player_name_normalized": "stephen curry",
                    "bref_team_abbreviation": "GSW",
                    "nba_team_abbreviation": "GSW",
                    "season": "2024-25",
                    "salary": 51000000,
                    "is_fully_guaranteed": True,
                    "remaining_guaranteed": 51000000,
                    "player_age": 37,
                    "source_url": "https://www.basketball-reference.com/contracts/GSW.html",
                    "scraped_at": now,
                }
            ],
            ["bref_player_slug", "bref_team_abbreviation", "season"],
        )
        upsert_rows(
            session,
            TeamPayroll,
            [
                {
                    "bref_team_abbreviation": "GSW",
                    "nba_team_abbreviation": "GSW",
                    "season": "2024-25",
                    "total_salary": 51000000,
                    "remaining_guaranteed": 51000000,
                    "source_url": "https://www.basketball-reference.com/contracts/GSW.html",
                    "scraped_at": now,
                }
            ],
            ["bref_team_abbreviation", "season"],
        )

    with db_session_factory() as session:
        salary = session.execute(
            text(
                "SELECT salary FROM source.player_contracts "
                "WHERE bref_player_slug = 'curryst01' AND season = '2024-25'"
            )
        ).scalar_one()
        assert salary == 51000000
        payroll = session.execute(
            text(
                "SELECT total_salary FROM source.team_payroll "
                "WHERE bref_team_abbreviation = 'GSW' AND season = '2024-25'"
            )
        ).scalar_one()
        assert payroll == 51000000


@pytest.mark.integration
def test_upsert_play_by_play(db_session_factory) -> None:
    now = datetime.now(UTC)
    with get_session() as session:
        upsert_rows(
            session,
            Team,
            [
                {
                    "team_id": 11,
                    "abbreviation": "PBP",
                    "full_name": "PBP Home",
                    "city": "Home",
                    "nickname": "Home",
                    "conference": "West",
                    "division": "Pacific",
                    "scraped_at": now,
                },
                {
                    "team_id": 12,
                    "abbreviation": "AWY",
                    "full_name": "PBP Away",
                    "city": "Away",
                    "nickname": "Away",
                    "conference": "East",
                    "division": "Atlantic",
                    "scraped_at": now,
                },
            ],
            ["team_id"],
        )
        upsert_rows(
            session,
            Game,
            [
                {
                    "game_id": "0022400888",
                    "season": "2024-25",
                    "season_type": "Regular Season",
                    "game_date": date(2024, 11, 2),
                    "home_team_id": 11,
                    "away_team_id": 12,
                    "home_score": 101,
                    "away_score": 99,
                    "status": "Final",
                    "scraped_at": now,
                }
            ],
            ["game_id"],
        )
        assert (
            upsert_rows(
                session,
                PlayByPlay,
                [
                    {
                        "game_id": "0022400888",
                        "season": "2024-25",
                        "action_number": 4,
                        "action_id": 400,
                        "period": 1,
                        "clock": "PT11M32.00S",
                        "score_home": 2,
                        "score_away": 0,
                        "team_id": 11,
                        "player_id": 201939,
                        "action_type": "2pt",
                        "sub_type": "Jump Shot",
                        "description": "Curry 18' Jump Shot (2 PTS)",
                        "extras": {"shotResult": "Made"},
                        "scraped_at": now,
                    }
                ],
                ["game_id", "action_number", "action_id"],
            )
            == 1
        )
        upsert_rows(
            session,
            PlayByPlay,
            [
                {
                    "game_id": "0022400888",
                    "season": "2024-25",
                    "action_number": 4,
                    "action_id": 400,
                    "period": 1,
                    "clock": "PT11M32.00S",
                    "score_home": 2,
                    "score_away": 0,
                    "team_id": 11,
                    "player_id": 201939,
                    "action_type": "2pt",
                    "sub_type": "Jump Shot",
                    "description": "Updated description",
                    "extras": {"shotResult": "Made", "shotDistance": 18},
                    "scraped_at": now,
                }
            ],
            ["game_id", "action_number", "action_id"],
        )

    with db_session_factory() as session:
        row = session.execute(
            text(
                "SELECT description, extras->>'shotDistance' "
                "FROM source.play_by_play "
                "WHERE game_id = '0022400888' AND action_number = 4"
            )
        ).one()
        assert row[0] == "Updated description"
        assert row[1] == "18"
