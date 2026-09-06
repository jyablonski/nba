"""API integration tests against Testcontainers Postgres + seeded gold."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_health_real_app(integration_client) -> None:
    response = integration_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
def test_list_players_seeded(integration_client) -> None:
    response = integration_client.get("/api/v1/players", params={"search": "Kawhi"})
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["full_name"] == "Kawhi Leonard"
    assert body["data"][0]["team_abbreviation"] == "LAC"


@pytest.mark.integration
def test_get_player_and_game_log(integration_client) -> None:
    detail = integration_client.get("/api/v1/players/202695")
    assert detail.status_code == 200
    assert detail.json()["data"]["career_games_played"] == 3

    logs = integration_client.get(
        "/api/v1/players/202695/game-log",
        params={"season": "2024-25"},
    )
    assert logs.status_code == 200
    body = logs.json()
    assert body["meta"]["total"] == 3
    assert body["data"][0]["points"] == 30


@pytest.mark.integration
def test_player_back_to_backs(integration_client) -> None:
    response = integration_client.get(
        "/api/v1/players/202695/back-to-backs",
        params={"season": "2024-25"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total_back_to_backs"] == 1
    assert body["games_played_in_b2b"] == 1
    assert body["avg_pts_b2b"] == 24.0


@pytest.mark.integration
def test_compare_players(integration_client) -> None:
    response = integration_client.get(
        "/api/v1/players/compare",
        params={"ids": "202695,201939", "stat": "ppg"},
    )
    assert response.status_code == 200
    rows = response.json()["data"]
    names = [row["full_name"] for row in rows]
    assert names[0] == "Stephen Curry"
    by_id = {row["player_id"]: row for row in rows}
    assert by_id[201939]["career_avg_plus_minus"] == 3.5
    assert by_id[202695]["career_avg_plus_minus"] == 0.7


@pytest.mark.integration
def test_teams_and_record(integration_client) -> None:
    teams = integration_client.get("/api/v1/teams")
    assert teams.status_code == 200
    assert teams.json()["meta"]["total"] == 3

    detail = integration_client.get("/api/v1/teams/1610612744")
    assert detail.status_code == 200
    team = detail.json()["data"]
    assert team["arena_name"] == "Chase Center"
    assert team["arena_latitude"] == pytest.approx(37.76806)
    assert team["arena_longitude"] == pytest.approx(-122.38750)

    record = integration_client.get("/api/v1/teams/1610612746/record")
    assert record.status_code == 200
    body = record.json()["data"]
    assert body["wins"] == 2
    assert body["losses"] == 1
    assert body["win_pct"] == 0.667


@pytest.mark.integration
def test_games_and_seasons(integration_client) -> None:
    games = integration_client.get("/api/v1/games", params={"season": "2024-25"})
    assert games.status_code == 200
    assert games.json()["meta"]["total"] == 3

    seasons = integration_client.get("/api/v1/seasons")
    assert seasons.status_code == 200
    assert seasons.json()["data"] == ["2024-25"]

    schedule = integration_client.get("/api/v1/schedule", params={"season": "2024-25"})
    assert schedule.status_code == 200
    body = schedule.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["game_id"] == "0022400999"
    assert body["data"][0]["status"] == "Scheduled"
    assert body["data"][0]["home_team_abbreviation"] == "GSW"


@pytest.mark.integration
def test_status_and_coverage(integration_client, postgres_engine) -> None:
    from sqlalchemy import text

    response = integration_client.get("/api/v1/status")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["last_scraped_at"] is None
    assert body["player_count"] == 2
    assert body["game_count"] == 3
    assert body["season_count"] == 1
    assert body["first_season"] == "2024-25"
    assert body["last_season"] == "2024-25"

    with postgres_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO source.teams (
                    team_id, abbreviation, full_name, city, nickname,
                    conference, division, scraped_at
                ) VALUES (
                    1610612744, 'GSW', 'Golden State Warriors', 'San Francisco',
                    'Warriors', 'West', 'Pacific', :ts
                )
                """
            ),
            {"ts": "2026-08-01 12:00:00"},
        )
    fallback = integration_client.get("/api/v1/status")
    assert fallback.status_code == 200
    assert fallback.json()["data"]["last_scraped_at"] == "2026-08-01T12:00:00Z"

    with postgres_engine.begin() as conn:
        conn.execute(
            text("UPDATE source.scrape_pipeline SET last_success_at = :ts WHERE id = 1"),
            {"ts": "2026-09-04 04:12:00"},
        )
    stamped = integration_client.get("/api/v1/status")
    assert stamped.status_code == 200
    assert stamped.json()["data"]["last_scraped_at"] == "2026-09-04T04:12:00Z"


@pytest.mark.integration
def test_player_directory_and_season_stats(integration_client) -> None:
    players = integration_client.get(
        "/api/v1/players",
        params={"team_id": 1610612746, "active": True},
    )
    assert players.status_code == 200
    row = players.json()["data"][0]
    assert row["full_name"] == "Kawhi Leonard"
    assert row["career_games_played"] == 3
    assert row["career_ppg"] == 27.3

    logs = integration_client.get(
        "/api/v1/players/202695/game-log",
        params={"is_back_to_back": True},
    )
    assert logs.status_code == 200
    assert logs.json()["meta"]["total"] == 1
    assert logs.json()["data"][0]["points"] == 24

    seasons = integration_client.get("/api/v1/players/202695/season-stats")
    assert seasons.status_code == 200
    assert seasons.json()["data"][0]["season"] == "2024-25"
    assert seasons.json()["data"][0]["games_played"] == 3

    compare = integration_client.get(
        "/api/v1/players/compare",
        params={"ids": "202695,201939"},
    )
    assert compare.status_code == 200
    kawhi = next(item for item in compare.json()["data"] if item["player_id"] == 202695)
    assert kawhi["team_abbreviation"] == "LAC"
    assert kawhi["first_season"] == "2024-25"
    assert kawhi["career_avg_plus_minus"] == 0.7


@pytest.mark.integration
def test_compare_head_to_head(integration_client) -> None:
    h2h = integration_client.get(
        "/api/v1/players/compare/head-to-head",
        params={"ids": "202695,201939"},
    )
    assert h2h.status_code == 200
    meeting = h2h.json()["data"]
    assert meeting["games_played"] == 2
    by_id = {row["player_id"]: row for row in meeting["players"]}
    assert by_id[202695]["ppg"] == 29.0
    assert by_id[201939]["ppg"] == 30.5
    assert by_id[202695]["plus_minus"] == -2.0
    assert by_id[201939]["plus_minus"] == 3.5
    assert {game["game_id"] for game in meeting["games"]} == {"0022400001", "0022400003"}


@pytest.mark.integration
def test_teams_directory_records(integration_client) -> None:
    teams = integration_client.get("/api/v1/teams", params={"season": "2024-25"})
    assert teams.status_code == 200
    by_abbr = {row["abbreviation"]: row for row in teams.json()["data"]}
    assert by_abbr["GSW"]["wins"] == 50
    assert by_abbr["GSW"]["nickname"] == "Warriors"
    assert by_abbr["CHI"]["conference"] == "East"


@pytest.mark.integration
def test_salary_payroll_and_standings(integration_client) -> None:
    curry = integration_client.get("/api/v1/players/201939")
    assert curry.status_code == 200
    player = curry.json()["data"]
    assert player["current_season_salary"] == 50_000_000
    assert player["current_remaining_guaranteed"] == 101_000_000
    assert player["current_contract_season"] == "2024-25"

    standings = integration_client.get("/api/v1/standings", params={"conference": "West"})
    assert standings.status_code == 200
    rows = standings.json()["data"]
    assert standings.json()["meta"]["total"] == 2
    assert rows[0]["abbreviation"] == "GSW"
    assert rows[0]["conference_rank"] == 1
    assert rows[0]["games_back"] == 0
    assert rows[1]["abbreviation"] == "LAC"
    assert rows[1]["games_back"] == 1.5

    team = integration_client.get("/api/v1/teams/1610612744")
    assert team.status_code == 200
    body = team.json()["data"]
    assert body["current_season_payroll"] == 51_000_000
    assert body["standing"]["conference_rank"] == 1
    assert body["standing"]["conference"] == "West"
