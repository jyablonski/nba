"""Eval list for rule-based /ask families (option A / NLP_BACKEND=rules)."""

from __future__ import annotations

from typing import Any

import pytest
from cube.errors import CubeUnavailableError
from ids import (
    GAME_ONE,
    PLAYER_CURRY,
    PLAYER_KAWHI,
    PLAYER_LEBRON,
    TEAM_BOS,
    TEAM_GSW,
    TEAM_LAL,
    TEAM_OKC,
)
from services.nl_query import NaturalLanguageQueryService


class FakeCubeAnalytics:
    def search_players(self, name: str) -> list[dict[str, Any]]:
        catalog = [
            {"player_id": PLAYER_KAWHI, "full_name": "Kawhi Leonard"},
            {"player_id": PLAYER_LEBRON, "full_name": "LeBron James"},
            {"player_id": PLAYER_CURRY, "full_name": "Stephen Curry"},
        ]
        needle = (name or "").lower()
        return [row for row in catalog if needle in row["full_name"].lower()]

    def get_player(self, player_id: str) -> dict[str, Any] | None:
        if str(player_id) == PLAYER_CURRY:
            return {
                "player_id": PLAYER_CURRY,
                "full_name": "Stephen Curry",
                "current_season_salary": 55772427,
                "current_remaining_guaranteed": 55772427,
                "current_contract_season": "2025-26",
            }
        if str(player_id) == PLAYER_LEBRON:
            return {
                "player_id": PLAYER_LEBRON,
                "full_name": "LeBron James",
                "current_season_salary": 52662789,
                "current_remaining_guaranteed": None,
                "current_contract_season": None,
            }
        if str(player_id) == PLAYER_KAWHI:
            return {
                "player_id": PLAYER_KAWHI,
                "full_name": "Kawhi Leonard",
                "current_season_salary": None,
            }
        return None

    def get_back_to_back_stats(self, player_id: str, season: str | None) -> dict:
        return {
            "total_back_to_backs": 10,
            "games_played_in_b2b": 8,
            "games_sat_in_b2b": 2,
            "avg_pts_b2b": 25.0,
            "avg_pts_non_b2b": 27.0,
            "season": season,
        }

    def compare_players(self, player_ids: list[str], stats: list[str] | None = None) -> list[dict]:
        if len(player_ids) < 2:
            raise ValueError("compare_players requires at least 2 player_ids")
        rows = [
            {
                "player_id": PLAYER_LEBRON,
                "full_name": "LeBron James",
                "career_games_played": 1500,
                "career_ppg": 27.1,
                "career_rpg": 7.5,
                "career_apg": 7.4,
            },
            {
                "player_id": PLAYER_CURRY,
                "full_name": "Stephen Curry",
                "career_games_played": 1000,
                "career_ppg": 24.3,
                "career_rpg": 4.7,
                "career_apg": 6.5,
            },
        ]
        player_id_values = {str(player_id) for player_id in player_ids}
        return [row for row in rows if row["player_id"] in player_id_values]

    def find_team(self, abbreviation: str) -> dict | None:
        teams = {
            "GSW": {
                "team_id": TEAM_GSW,
                "abbreviation": "GSW",
                "team_name": "Golden State Warriors",
                "current_season_payroll": 180000000,
                "current_remaining_guaranteed": 170000000,
                "current_contract_season": "2025-26",
            },
            "LAL": {
                "team_id": TEAM_LAL,
                "abbreviation": "LAL",
                "team_name": "Los Angeles Lakers",
                "current_season_payroll": 190000000,
                "current_remaining_guaranteed": None,
                "current_contract_season": None,
            },
            "OKC": {
                "team_id": TEAM_OKC,
                "abbreviation": "OKC",
                "team_name": "Oklahoma City Thunder",
                "current_season_payroll": None,
            },
        }
        return teams.get(abbreviation.upper())

    def get_team_record(self, team_abbreviation: str, **kwargs) -> dict:
        team = self.find_team(team_abbreviation)
        return {
            "team_id": team["team_id"] if team else None,
            "abbreviation": team_abbreviation,
            "team_name": team["team_name"] if team else None,
            "wins": 3,
            "losses": 1,
            "win_pct": 0.75,
            "games": 4,
            "game_list": [],
            "filters_applied": {
                "team_abbreviation": team_abbreviation,
                "arena_city": kwargs.get("arena_city"),
                "since_season": kwargs.get("since_season"),
            },
        }

    def list_standings(
        self, season: str | None = None, conference: str | None = None
    ) -> list[dict]:
        rows = [
            {
                "team_id": TEAM_OKC,
                "abbreviation": "OKC",
                "team_name": "Oklahoma City Thunder",
                "conference": "West",
                "conference_rank": 1,
                "wins": 50,
                "losses": 10,
                "win_pct": 0.833,
                "games_back": 0,
            },
            {
                "team_id": TEAM_LAL,
                "abbreviation": "LAL",
                "team_name": "Los Angeles Lakers",
                "conference": "West",
                "conference_rank": 6,
                "wins": 40,
                "losses": 20,
                "win_pct": 0.667,
                "games_back": 10.0,
            },
            {
                "team_id": TEAM_BOS,
                "abbreviation": "BOS",
                "team_name": "Boston Celtics",
                "conference": "East",
                "conference_rank": 1,
                "wins": 48,
                "losses": 12,
                "win_pct": 0.8,
                "games_back": 0,
            },
        ]
        if conference:
            rows = [row for row in rows if row["conference"].lower() == conference.lower()]
        return rows

    def get_team_standing(self, team_id: str, season: str | None = None) -> dict | None:
        for row in self.list_standings():
            if str(row["team_id"]) == str(team_id):
                return row
        return None

    def get_player_game_log(self, player_id: str, season: str | None = None) -> list[dict]:
        return [{"player_id": player_id, "points": 30, "season": season}]

    def get_career_stats(self, player_id: str) -> dict | None:
        return self.get_player(player_id)

    def get_player_contract(self, player_id: str, season: str | None = None) -> dict | None:
        return self.get_player(player_id)

    def get_team_payroll(self, abbreviation: str, season: str | None = None) -> dict | None:
        return self.find_team(abbreviation)

    def get_player_season_stats(self, player_id: str) -> list[dict]:
        if str(player_id) != PLAYER_CURRY:
            return []
        return [
            {"player_id": PLAYER_CURRY, "season": "2023-24", "games_played": 74, "ppg": 26.4},
            {"player_id": PLAYER_CURRY, "season": "2024-25", "games_played": 70, "ppg": 24.5},
        ]

    def get_games_schedule(self, **kwargs) -> list[dict]:
        return [{"game_id": GAME_ONE, "status": "Scheduled"}]

    def get_game_predictions(self, **kwargs) -> list[dict]:
        return [{"game_id": GAME_ONE, "model_wp": 0.58, "model_version": "elo-v0"}]

    def get_player_injuries(self, **kwargs) -> list[dict]:
        return [{"player_name": "Kawhi Leonard", "description": "knee"}]

    def get_game_odds(self, **kwargs) -> list[dict]:
        return [{"game_id": GAME_ONE, "market": "h2h"}]

    def get_play_by_play(self, game_id: str, limit: int | None = None) -> list[dict]:
        return [{"game_id": game_id, "action_number": 1}]

    def get_reddit_posts(self, **kwargs) -> list[dict]:
        return [{"reddit_id": "abc", "title": "Game thread"}]

    def meta_summary(self) -> str:
        return "## players\nMeasures: players.count\nDimensions: players.full_name\n"

    def run_cube_query(self, query: dict) -> list[dict]:
        if "mystery.ppg" in (query.get("measures") or []):
            from cube.errors import UnknownMemberError

            raise UnknownMemberError("Unknown Cube member(s): mystery.ppg")
        return [{"ok": True}]


EVAL_CASES = [
    ("How many back-to-backs has Kawhi played?", "b2b"),
    ("How does Kawhi Leonard perform on back-to-backs?", "b2b"),
    ("Compare LeBron vs Curry career games", "compare"),
    ("Who has more games, LeBron or Curry?", "compare"),
    (
        "How many more career games has LeBron played than Stephen Curry?",
        "compare",
    ),
    ("What is the Warriors' win percentage in Chicago?", "arena_city"),
    ("Warriors record in Chicago", "arena_city"),
    ("Who leads the West?", "standings"),
    ("How many games back are the Lakers?", "standings"),
    ("Eastern Conference standings", "standings"),
    ("What is Curry's salary?", "salary"),
    ("What is the Warriors payroll?", "salary"),
    ("How much does LeBron make?", "salary"),
    ("Curry PPG by season", "season_stats"),
    ("What is the meaning of life?", "refuse"),
]


@pytest.fixture
def service() -> NaturalLanguageQueryService:
    return NaturalLanguageQueryService(FakeCubeAnalytics())


@pytest.mark.unit
@pytest.mark.parametrize(("question", "family"), EVAL_CASES)
def test_nl_eval_family(
    service: NaturalLanguageQueryService,
    question: str,
    family: str,
) -> None:
    assert service.classify(question) == family
    response = service.answer(question)
    assert response.answer
    if family == "refuse":
        assert response.data == []
        assert "salary/payroll" in response.answer
        assert "standings" in response.answer
    else:
        assert response.data
        for row in response.data:
            assert "player_id" not in row
            assert "team_id" not in row
            assert "filters_applied" not in row
            assert "game_list" not in row
            assert "total_b2b_games" not in row
            assert "avg_pts_in_b2b" not in row
            if "full_name" in row:
                assert "player_name" not in row


@pytest.mark.unit
def test_classify_empty_is_refuse(service: NaturalLanguageQueryService) -> None:
    assert service.classify("   ") == "refuse"
    response = service.answer("   ")
    assert response.data == []
    assert "non-empty" in response.answer


@pytest.mark.unit
def test_resolves_bref_initial_player_names() -> None:
    class BrefNames(FakeCubeAnalytics):
        def search_players(self, name: str) -> list[dict[str, Any]]:
            if name.casefold() == "leonard":
                return [{"player_id": PLAYER_KAWHI, "full_name": "K. Leonard"}]
            return []

    response = NaturalLanguageQueryService(BrefNames()).answer(
        "How many back-to-backs has Kawhi Leonard played?"
    )

    assert response.data
    assert "K. Leonard has" in response.answer


@pytest.mark.unit
def test_cube_down_is_clear_answer() -> None:
    class Down(FakeCubeAnalytics):
        def search_players(self, name: str) -> list[dict]:
            raise CubeUnavailableError(
                "Ask is unavailable because the Cube semantic layer is down."
            )

    service = NaturalLanguageQueryService(Down())
    response = service.answer("How many back-to-backs has Kawhi played?")
    assert response.data == []
    assert "Cube semantic layer is down" in response.answer


@pytest.mark.unit
def test_salary_unmatched_and_null(service: NaturalLanguageQueryService) -> None:
    missing = service.answer("What is Jokic's salary?")
    assert missing.data == []
    assert "No player found" in missing.answer

    null_salary = service.answer("What is Kawhi's salary?")
    assert "don't have a current salary" in null_salary.answer


@pytest.mark.unit
def test_payroll_and_games_back(service: NaturalLanguageQueryService) -> None:
    payroll = service.answer("OKC payroll")
    assert "don't have a current payroll" in payroll.answer

    games_back = service.answer("How many games behind are the Lakers?")
    assert service.classify("How many games behind are the Lakers?") == "standings"
    assert "games back" in games_back.answer
    assert games_back.data[0]["abbreviation"] == "LAL"


@pytest.mark.unit
def test_nl_error_and_fallback_paths(service: NaturalLanguageQueryService) -> None:
    assert "Could not identify a player" in service.answer("How many back-to-backs?").answer
    assert "No player found" in service.answer("How many back-to-backs has Jokic played?").answer
    assert "at least two player names" in service.answer("Compare LeBron career games").answer
    assert "No player found" in service.answer("Compare LeBron vs Jokic").answer
    assert "Could not identify a team" in service.answer("What is the win percentage?").answer
    assert "Could not identify a player" in service.answer("What is the salary?").answer
    assert "Could not identify a player" in service.answer("PPG by season").answer
    assert "No player found" in service.answer("Jokic PPG by season").answer
    assert "Could not identify a team" in service.answer("What is the payroll?").answer
    assert "No team found" in service.answer("Hawks payroll").answer
    assert "No team found" in service.answer("How many games back are the Hawks?").answer
    assert service.classify("Eastern Conference standings") == "standings"
    assert "East conference standings" in service.answer("Eastern Conference standings").answer
    assert service._extract_team_abbr("GSW") == "GSW"
    assert service._format_usd(None) == "None"
    assert service._extract_season("standings 2024-25") == "2024-25"

    city_the = service.answer("Warriors record in the since 2024-25")
    assert city_the.data

    b2b_season = service.answer("How many back-to-backs has Kawhi played in 2024-25?")
    assert b2b_season.data[0]["season"] == "2024-25"
    assert "sat out" in b2b_season.answer
    standings_season = service.answer("Who leads the West in 2024-25?")
    assert standings_season.data
    header_west = service.answer("Who leads the West?", season="2026-27")
    assert "Oklahoma City Thunder" in header_west.answer
    assert header_west.data[0]["abbreviation"] == "OKC"
    season_stats = service.answer("Curry PPG by season")
    assert season_stats.data[0]["season"] == "2023-24"
    header_season = service.answer("How many back-to-backs has Kawhi played?", season="2025-26")
    assert header_season.data[0]["season"] == "2025-26"


@pytest.mark.unit
def test_salary_missing_detail() -> None:
    class MissingDetail(FakeCubeAnalytics):
        def get_player_contract(self, player_id: str, season: str | None = None) -> dict | None:
            return None

    missing = NaturalLanguageQueryService(MissingDetail())
    assert "No player found" in missing.answer("What is Curry's salary?").answer


@pytest.mark.unit
def test_compare_and_standings_empty_rows() -> None:
    class ThinCompare(FakeCubeAnalytics):
        def compare_players(
            self, player_ids: list[str], stats: list[str] | None = None
        ) -> list[dict]:
            return [
                {
                    "player_id": PLAYER_LEBRON,
                    "full_name": "LeBron James",
                    "career_games_played": 1,
                }
            ]

    class EmptyStandings(FakeCubeAnalytics):
        def list_standings(
            self, season: str | None = None, conference: str | None = None
        ) -> list[dict]:
            return []

        def get_team_standing(self, team_id: str, season: str | None = None) -> dict | None:
            return None

    class PartialNamePlayers(FakeCubeAnalytics):
        def search_players(self, name: str) -> list[dict]:
            return [{"player_id": PLAYER_CURRY, "full_name": "Wardell Stephen Curry"}]

    compare = NaturalLanguageQueryService(ThinCompare())
    assert "Could not load career rows" in compare.answer("Compare LeBron vs Curry").answer

    empty = NaturalLanguageQueryService(EmptyStandings())
    assert "standings rows found" in empty.answer("Who leads the West?").answer
    assert "No standings row" in empty.answer("How many games back are the Lakers?").answer

    partial = NaturalLanguageQueryService(PartialNamePlayers())
    assert partial.answer("What is Curry's salary?").data

    titled = NaturalLanguageQueryService(FakeCubeAnalytics())
    names = titled._extract_player_names("What is Bam Adebayo's salary?")
    assert names == ["Bam Adebayo"]


@pytest.mark.unit
def test_who_leads_west_from_game_record_ranks() -> None:
    class GameRecordStandings(FakeCubeAnalytics):
        def list_standings(
            self, season: str | None = None, conference: str | None = None
        ) -> list[dict]:
            rows = [
                {
                    "team_id": TEAM_OKC,
                    "abbreviation": "OKC",
                    "team_name": "Oklahoma City Thunder",
                    "conference": "West",
                    "conference_rank": 1,
                    "wins": 2,
                    "losses": 0,
                    "win_pct": 1.0,
                    "games_back": 0,
                    "season": season,
                },
                {
                    "team_id": TEAM_GSW,
                    "abbreviation": "GSW",
                    "team_name": "Golden State Warriors",
                    "conference": "West",
                    "conference_rank": 2,
                    "wins": 1,
                    "losses": 1,
                    "win_pct": 0.5,
                    "games_back": 1.0,
                    "season": season,
                },
            ]
            if conference:
                rows = [row for row in rows if row["conference"].lower() == conference.lower()]
            return rows

    service = NaturalLanguageQueryService(GameRecordStandings())
    response = service.answer("Who leads the West?", season="2026-27")
    assert service.classify("Who leads the West?") == "standings"
    assert "Oklahoma City Thunder" in response.answer
    assert "2-0" in response.answer
    assert response.data
    assert response.data[0]["abbreviation"] == "OKC"
    assert response.data[0]["conference_rank"] == 1
    assert "player_id" not in response.data[0]
    assert "team_id" not in response.data[0]


@pytest.mark.unit
def test_compare_try_chip_returns_difference(service: NaturalLanguageQueryService) -> None:
    question = "How many more career games has LeBron played than Stephen Curry?"
    assert service.classify(question) == "compare"
    response = service.answer(question)
    assert "500 more career games" in response.answer
    assert "capability" not in response.answer.lower()
    assert "I can answer" not in response.answer
    assert len(response.data) == 2
    assert [row["full_name"] for row in response.data] == [
        "LeBron James",
        "Stephen Curry",
    ]
    assert "player_id" not in response.data[0]
    assert set(response.data[0]) == {"full_name", "career_games_played"}


@pytest.mark.unit
def test_ask_families_limit_visible_fields(service: NaturalLanguageQueryService) -> None:
    salary = service.answer("What is Curry's salary?")
    assert set(salary.data[0]) == {
        "full_name",
        "current_contract_season",
        "current_season_salary",
        "current_remaining_guaranteed",
    }

    payroll = service.answer("What is the Warriors payroll?")
    assert set(payroll.data[0]) == {
        "abbreviation",
        "team_name",
        "current_contract_season",
        "current_season_payroll",
        "current_remaining_guaranteed",
    }

    standings = service.answer("Who leads the West?")
    assert set(standings.data[0]) <= {
        "conference_rank",
        "abbreviation",
        "team_name",
        "conference",
        "wins",
        "losses",
        "win_pct",
        "games_back",
        "streak",
        "last_10",
    }
    assert "season_type" not in standings.data[0]
    assert "as_of_date" not in standings.data[0]

    season_stats = service.answer("Curry PPG by season")
    assert season_stats.data[0]["full_name"] == "Stephen Curry"
    assert "player_id" not in season_stats.data[0]
    assert set(season_stats.data[0]) <= {
        "full_name",
        "season",
        "games_played",
        "ppg",
        "rpg",
        "apg",
    }

    b2b = service.answer("How many back-to-backs has Kawhi played?")
    assert "season" not in b2b.data[0]
    assert set(b2b.data[0]) == {
        "full_name",
        "total_back_to_backs",
        "games_played_in_b2b",
        "games_sat_in_b2b",
        "avg_pts_b2b",
        "avg_pts_non_b2b",
    }


@pytest.mark.unit
def test_arena_city_zero_games_hides_dump_columns() -> None:
    class EmptyRecord(FakeCubeAnalytics):
        def get_team_record(self, team_abbreviation: str, **kwargs) -> dict:
            return {
                "team_id": None,
                "abbreviation": team_abbreviation,
                "team_name": None,
                "wins": 0,
                "losses": 0,
                "win_pct": None,
                "games": 0,
                "game_list": [],
                "filters_applied": {
                    "team_abbreviation": team_abbreviation,
                    "arena_city": kwargs.get("arena_city"),
                    "since_season": kwargs.get("since_season"),
                },
            }

    service = NaturalLanguageQueryService(EmptyRecord())
    question = "What is the Warriors' win percentage in Chicago since 2010-11?"
    response = service.answer(question)
    assert response.data[0]["team_name"] == "Golden State Warriors"
    assert response.data[0]["abbreviation"] == "GSW"
    assert response.data[0]["games"] == 0
    assert "team_id" not in response.data[0]
    assert "filters_applied" not in response.data[0]
    assert "game_list" not in response.data[0]
    assert "0-0" in response.answer
    assert "loaded warehouse" in response.answer
