from datetime import date

import pytest

from config import Settings, _env_file, _repo_root
from elo import clip_probability, game_row_from_mapping, rows_from_mappings


@pytest.mark.unit
def test_settings_builds_database_url() -> None:
    settings = Settings(database_url="")
    assert "nba_user" in settings.database_url


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
    assert _repo_root() is not None or _env_file() is None


@pytest.mark.unit
def test_clip_and_rows_from_object() -> None:
    assert clip_probability(2.0) < 1.0
    assert clip_probability(-1.0) > 0.0
    row = type(
        "Row",
        (),
        {
            "game_id": "9",
            "game_date": date(2024, 1, 1),
            "season": "2023-24",
            "home_team_id": 1,
            "away_team_id": 2,
            "home_won": True,
            "winner_location": "home",
        },
    )()
    parsed = game_row_from_mapping(row)
    assert parsed.home_won is True
    assert len(rows_from_mappings([row])) == 1
