from datetime import date, timedelta
from uuid import UUID

import pytest
from logit import (
    FEATURE_NAMES,
    cold_start,
    feature_row_from_mapping,
    fit_artifact,
    predict_artifact,
    rows_from_mappings,
)

HOME = UUID("00000000-0000-4000-8000-000000000201")
AWAY = UUID("00000000-0000-4000-8000-000000000202")


def _mapping(index: int, home_won: bool | None) -> dict:
    values = {name: 0.0 for name in FEATURE_NAMES}
    values["point_diff_diff"] = float(index - 10)
    values["h2h_home_win_pct"] = None if index % 3 == 0 else 0.5
    values["h2h_games_before"] = float(index % 4)
    return {
        "game_id": UUID(int=index + 1),
        "game_date": date(2024, 10, 1) + timedelta(days=index),
        "season": "2024-25",
        "home_team_id": HOME,
        "away_team_id": AWAY,
        "home_won": home_won,
        "home_games_before": index,
        "away_games_before": index,
        **values,
    }


@pytest.mark.unit
def test_feature_rows_parse_and_detect_cold_start() -> None:
    row = feature_row_from_mapping(_mapping(2, True))
    assert row.values["point_diff_diff"] == -8.0
    assert row.home_won is True
    assert cold_start(row, 3) is True
    assert cold_start(row, 2) is False
    assert len(rows_from_mappings([_mapping(1, False)])) == 1


@pytest.mark.unit
def test_fit_and_predict_artifact_is_calibrated_and_bounded() -> None:
    rows = [feature_row_from_mapping(_mapping(index, index % 2 == 0)) for index in range(24)]
    artifact = fit_artifact(rows)
    assert artifact["training_rows"] == 24
    assert artifact["feature_names"] == list(FEATURE_NAMES)
    low = predict_artifact(artifact, rows[0])
    high = predict_artifact(artifact, rows[-1])
    assert 0.0 < low < 1.0
    assert 0.0 < high < 1.0
    assert set(artifact["calibration"]) == {"slope", "intercept"}


@pytest.mark.unit
def test_fit_artifact_requires_completed_games() -> None:
    with pytest.raises(ValueError, match="completed games"):
        fit_artifact([feature_row_from_mapping(_mapping(1, None))])


@pytest.mark.unit
def test_feature_row_supports_attribute_objects_and_missing_values() -> None:
    mapping = _mapping(4, False)
    mapping["win_pct_diff"] = None
    row_object = type("Feature", (), mapping)()
    parsed = feature_row_from_mapping(row_object)
    assert parsed.values["win_pct_diff"] is None
    assert parsed.home_won is False


@pytest.mark.unit
def test_predict_artifact_without_calibration_uses_raw_logit() -> None:
    rows = [feature_row_from_mapping(_mapping(index, index % 2 == 0)) for index in range(12)]
    artifact = fit_artifact(rows)
    artifact.pop("calibration")
    probability = predict_artifact(artifact, rows[-1])
    assert 0.0 < probability < 1.0
