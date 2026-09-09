from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from config import Settings, missing_reddit_env_names
from db import (
    PG_MAX_BIND_PARAMS,
    UPSERT_BATCH_SIZE,
    engine,
    get_session,
    iter_upsert_batches,
    upsert_batch_size,
    upsert_rows,
)
from models import (
    GameOdds,
    PlayByPlay,
    Player,
    PlayerContract,
    PlayerInjury,
    PlayerInjuryHistory,
    RedditComment,
    RedditPost,
    Standing,
    Team,
)


@pytest.mark.unit
def test_settings_builds_database_url() -> None:
    settings = Settings(database_url="")
    assert "nba_user" in settings.database_url
    assert settings.database_url.startswith("postgresql://")


@pytest.mark.unit
def test_env_file_helpers(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import config as cfg

    monkeypatch.setattr(cfg, "_repo_root", lambda: None)
    monkeypatch.chdir(tmp_path)
    assert cfg._env_file() is None
    env_path = tmp_path / ".env"
    env_path.write_text("POSTGRES_DB=nba\n", encoding="utf-8")
    assert cfg._env_file() == env_path

    monkeypatch.setattr(cfg, "_repo_root", lambda: tmp_path)
    assert cfg._env_file() == env_path
    env_path.unlink()
    assert cfg._env_file() is None

    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "init.sql").write_text("--\n", encoding="utf-8")
    monkeypatch.setattr(cfg.Path, "cwd", classmethod(lambda cls: tmp_path))
    found = cfg._repo_root()
    assert found is None or found == tmp_path
    blank = Settings(
        database_url="postgresql://nba_user:nba_pass@localhost:5432/nba",
        reddit_client_id="",
        reddit_client_secret="",
        reddit_user_agent="",
    )
    assert blank.reddit_client_id == ""
    assert missing_reddit_env_names(blank) == [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
    ]


@pytest.mark.unit
def test_settings_odds_api_key_empty_is_none() -> None:
    assert Settings(odds_api_key="").odds_api_key is None
    assert Settings(odds_api_key="   ").odds_api_key is None
    assert Settings(odds_api_key=None).odds_api_key is None
    assert Settings(odds_api_key="abc123").odds_api_key == "abc123"


@pytest.mark.unit
def test_settings_slack_webhook_url_empty_is_none() -> None:
    assert Settings(slack_webhook_url="").slack_webhook_url is None
    assert Settings(slack_webhook_url="   ").slack_webhook_url is None
    assert Settings(slack_webhook_url=None).slack_webhook_url is None
    assert (
        Settings(slack_webhook_url="https://hooks.slack.com/services/x").slack_webhook_url
        == "https://hooks.slack.com/services/x"
    )


@pytest.mark.unit
def test_engine_hides_bind_parameters() -> None:
    assert engine.hide_parameters is True
    assert UPSERT_BATCH_SIZE == 100
    assert UPSERT_BATCH_SIZE * 12 < PG_MAX_BIND_PARAMS


@pytest.mark.unit
def test_upsert_batch_size_caps_to_pg_limit() -> None:
    assert upsert_batch_size(12, requested=50) == 50
    assert upsert_batch_size(12, requested=20000) == PG_MAX_BIND_PARAMS // 12
    assert upsert_batch_size(0, requested=10) == 10
    assert upsert_batch_size(65535, requested=500) == 1


@pytest.mark.unit
def test_iter_upsert_batches_chunks_rows() -> None:
    rows = [{"n": i} for i in range(5)]
    batches = list(iter_upsert_batches(rows, batch_size=2, column_count=1))
    assert [len(batch) for batch in batches] == [2, 2, 1]
    assert batches[0][0]["n"] == 0
    assert batches[-1][0]["n"] == 4


@pytest.mark.unit
def test_iter_upsert_batches_caps_requested_size() -> None:
    rows = [{"n": i} for i in range(4)]
    batches = list(iter_upsert_batches(rows, batch_size=500, column_count=40000))
    assert len(batches) == 4
    assert all(len(batch) == 1 for batch in batches)


@pytest.mark.unit
def test_upsert_rows_empty() -> None:
    session = MagicMock()
    assert upsert_rows(session, Team, [], ["team_id"]) == 0
    session.execute.assert_not_called()


@pytest.mark.unit
def test_upsert_rows_batches() -> None:
    session = MagicMock()
    now = datetime.now()
    rows = [
        {
            "team_id": i,
            "abbreviation": f"T{i}",
            "full_name": "Warriors",
            "city": "SF",
            "nickname": "Warriors",
            "conference": "West",
            "division": "Pacific",
            "scraped_at": now,
        }
        for i in range(5)
    ]
    written = upsert_rows(session, Team, rows, ["team_id"], batch_size=2)
    assert written == 5
    assert session.execute.call_count == 3
    session.commit.assert_called()


@pytest.mark.unit
def test_get_session_commits_and_rollbacks() -> None:
    session = MagicMock()
    with patch("db.SessionLocal", return_value=session), get_session() as db:
        assert db is session
    session.commit.assert_called_once()
    session.close.assert_called_once()

    session = MagicMock()
    session.commit.side_effect = RuntimeError("fail")
    with patch("db.SessionLocal", return_value=session), pytest.raises(RuntimeError):
        with get_session():
            pass
    session.rollback.assert_called()


@pytest.mark.unit
def test_models_have_source_schema() -> None:
    assert Team.__table__.schema == "source"
    assert Player.__table__.schema == "source"
    assert PlayerContract.__table__.schema == "source"
    assert Standing.__table__.schema == "source"
    assert Player.__table__.name == "players"
    assert Standing.__table__.name == "standings"
    assert RedditPost.__table__.schema == "source"
    assert RedditPost.__table__.name == "reddit_posts"
    assert RedditComment.__table__.schema == "source"
    assert RedditComment.__table__.name == "reddit_comments"
    assert PlayerInjury.__table__.schema == "source"
    assert PlayerInjury.__table__.name == "player_injuries"
    assert PlayerInjuryHistory.__table__.schema == "source"
    assert PlayerInjuryHistory.__table__.name == "player_injuries_history"
    assert GameOdds.__table__.schema == "source"
    assert GameOdds.__table__.name == "game_odds"
    assert PlayByPlay.__table__.schema == "source"
    assert PlayByPlay.__table__.name == "play_by_play"
