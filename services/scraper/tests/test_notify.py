from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from notify import (
    StepFailure,
    SyncAlert,
    SyncFailedError,
    format_sync_failure_text,
    notify_sync_failures,
)

from main import cli


def _failure(
    step: str = "games",
    error_type: str = "RuntimeError",
    message: str = "boom",
    season: str | None = "2024-25",
) -> StepFailure:
    return StepFailure(step=step, error_type=error_type, message=message, season=season)


def _response(status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    return response


@pytest.mark.unit
def test_unset_url_sends_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[object] = []
    monkeypatch.setattr("notify.settings", SimpleNamespace(slack_webhook_url=None))
    monkeypatch.setattr(
        "notify.requests.post", lambda *args, **kwargs: posted.append((args, kwargs))
    )
    notify_sync_failures([_failure()], sync_name="scrape-all")
    assert posted == []

    notify_sync_failures([_failure()], sync_name="scrape-all", webhook_url="")
    notify_sync_failures([_failure()], sync_name="scrape-all", webhook_url="   ")
    assert posted == []


@pytest.mark.unit
def test_three_step_failures_post_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[tuple[tuple, dict]] = []

    def fake_post(*args, **kwargs):
        posted.append((args, kwargs))
        return _response()

    monkeypatch.setattr("notify.requests.post", fake_post)
    failures = [
        _failure("games", "RuntimeError", "timeout", "2024-25"),
        _failure("player_game_logs", "HTTPError", "503", "2024-25"),
        _failure("standings", "ValueError", "empty payload", "2023-24"),
    ]
    notify_sync_failures(failures, sync_name="scrape-all", webhook_url="https://hooks.slack.test/x")
    assert len(posted) == 1
    args, kwargs = posted[0]
    assert args[0] == "https://hooks.slack.test/x"
    assert kwargs["timeout"] == 8
    text = kwargs["json"]["text"]
    assert "scrape-all (3 step(s))" in text
    assert "games (2024-25): RuntimeError: timeout" in text
    assert "player_game_logs (2024-25): HTTPError: 503" in text
    assert "standings (2023-24): ValueError: empty payload" in text


@pytest.mark.unit
def test_all_steps_ok_sends_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[object] = []
    monkeypatch.setattr("notify.requests.post", lambda *args, **kwargs: posted.append(1))
    notify_sync_failures([], sync_name="scrape-all", webhook_url="https://hooks.slack.test/x")
    SyncAlert("scrape-daily").notify(webhook_url="https://hooks.slack.test/x")
    assert posted == []


@pytest.mark.unit
def test_webhook_http_error_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("notify.requests.post", lambda *args, **kwargs: _response(500))
    notify_sync_failures(
        [_failure()], sync_name="pipeline", webhook_url="https://hooks.slack.test/x"
    )


@pytest.mark.unit
def test_webhook_transport_error_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args, **kwargs):
        raise TimeoutError("slack down")

    monkeypatch.setattr("notify.requests.post", boom)
    notify_sync_failures(
        [_failure()], sync_name="pipeline", webhook_url="https://hooks.slack.test/x"
    )


@pytest.mark.unit
def test_error_message_strips_html_and_truncates() -> None:
    html = StepFailure.from_exception(
        "contracts",
        RuntimeError("<html><body>" + "x" * 400 + "</body></html>"),
        season=None,
    )
    assert "<html>" not in html.message
    assert "<body>" not in html.message
    assert len(html.message) <= 200
    assert html.message.endswith("...")
    assert "\n" not in html.message


@pytest.mark.unit
def test_format_caps_listed_failures() -> None:
    failures = [_failure(step=f"step-{i}", season=None) for i in range(16)]
    text = format_sync_failure_text("scrape-all", failures)
    assert "16 step(s)" in text
    assert "...and 1 more" in text


@pytest.mark.unit
def test_sync_alert_try_run_records_and_continues() -> None:
    alert = SyncAlert("scrape-all")
    assert alert.try_run("teams", lambda: 30) == 30
    assert (
        alert.try_run(
            "games", lambda: (_ for _ in ()).throw(RuntimeError("nope")), season="2024-25"
        )
        is None
    )
    assert alert.try_run("standings", lambda: 15, season="2024-25") == 15
    assert len(alert.failures) == 1
    assert alert.failures[0].step == "games"
    assert alert.failures[0].error_type == "RuntimeError"
    assert alert.failures[0].season == "2024-25"
    with pytest.raises(SyncFailedError, match="1 scrape step"):
        alert.raise_if_failed()


@pytest.mark.unit
def test_scrape_all_three_failures_one_post(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[object] = []

    def fake_post(*args, **kwargs):
        posted.append(kwargs["json"]["text"])
        return _response()

    monkeypatch.setattr("notify.requests.post", fake_post)
    monkeypatch.setattr(
        "main.scrape_teams", lambda: (_ for _ in ()).throw(RuntimeError("teams down"))
    )
    monkeypatch.setattr(
        "main.scrape_players",
        lambda enrich=False: (_ for _ in ()).throw(ValueError("players down")),
    )
    monkeypatch.setattr(
        "main.scrape_contracts",
        lambda: (_ for _ in ()).throw(RuntimeError("contracts down")),
    )
    monkeypatch.setattr("main.scrape_games", lambda season: 82)
    monkeypatch.setattr("main.scrape_player_game_logs", lambda season, active_only=False: 5)
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr(
        "notify.settings", SimpleNamespace(slack_webhook_url="https://hooks.slack.test/x")
    )
    result = CliRunner().invoke(cli, ["scrape-all", "--seasons", "2024-25"])
    assert result.exit_code == 1
    assert len(posted) == 1
    assert "3 step(s)" in posted[0]
    assert "teams: RuntimeError: teams down" in posted[0]
    assert "players: ValueError: players down" in posted[0]
    assert "contracts: RuntimeError: contracts down" in posted[0]


@pytest.mark.unit
def test_scrape_all_with_reddit_still_one_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("main.scrape_teams", lambda: 30)
    monkeypatch.setattr("main.scrape_players", lambda enrich=False: 10)
    monkeypatch.setattr("main.scrape_contracts", lambda: (8, 2))
    monkeypatch.setattr("main.scrape_games", lambda season: 82)
    monkeypatch.setattr("main.scrape_player_game_logs", lambda season, active_only=False: 5)
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr("main.scrape_reddit", lambda: 12)
    monkeypatch.setattr("main.stamp_cli_success", lambda: None)
    posted: list[object] = []
    monkeypatch.setattr("notify.requests.post", lambda *args, **kwargs: posted.append(1))
    monkeypatch.setattr(
        "notify.settings", SimpleNamespace(slack_webhook_url="https://hooks.slack.test/x")
    )
    result = CliRunner().invoke(cli, ["scrape-all", "--seasons", "2024-25", "--with-reddit"])
    assert result.exit_code == 0
    assert "Reddit posts: 12" in result.output
    assert posted == []


@pytest.mark.unit
def test_scrape_daily_success_sends_no_post(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[object] = []
    monkeypatch.setattr("notify.requests.post", lambda *args, **kwargs: posted.append(1))
    monkeypatch.setattr(
        "notify.settings", SimpleNamespace(slack_webhook_url="https://hooks.slack.test/x")
    )
    monkeypatch.setattr("main.scrape_todays_games", lambda: [])
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr("main.scrape_injuries", lambda: 0)
    monkeypatch.setattr("main.scrape_odds", lambda: 0)
    monkeypatch.setattr("main.scrape_contracts", lambda: (8, 2))
    monkeypatch.setattr("main.stamp_cli_success", lambda: None)
    result = CliRunner().invoke(cli, ["scrape-daily"])
    assert result.exit_code == 0
    assert posted == []


@pytest.mark.unit
def test_scrape_daily_webhook_500_still_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[object] = []

    def fake_post(*args, **kwargs):
        posted.append(1)
        return _response(500)

    monkeypatch.setattr("notify.requests.post", fake_post)
    monkeypatch.setattr(
        "notify.settings", SimpleNamespace(slack_webhook_url="https://hooks.slack.test/x")
    )
    monkeypatch.setattr(
        "main.scrape_todays_games",
        lambda: (_ for _ in ()).throw(RuntimeError("nba timeout")),
    )
    monkeypatch.setattr(
        "main.scrape_standings",
        lambda season: (_ for _ in ()).throw(RuntimeError("standings 503")),
    )
    monkeypatch.setattr("main.scrape_injuries", lambda: 0)
    monkeypatch.setattr("main.scrape_odds", lambda: 0)
    monkeypatch.setattr("main.scrape_contracts", lambda: (0, 0))
    result = CliRunner().invoke(cli, ["scrape-daily"])
    assert result.exit_code == 1
    assert len(posted) == 1
