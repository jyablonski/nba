import math

import pytest

from metrics import accuracy, brier_score, home_always_accuracy, log_loss, summarize


@pytest.mark.unit
def test_logloss_and_brier_perfect_and_empty() -> None:
    assert log_loss([1, 0], [1.0, 0.0]) == pytest.approx(0.0, abs=1e-6)
    assert brier_score([1, 0], [1.0, 0.0]) == pytest.approx(0.0)
    assert math.isnan(log_loss([], []))
    assert math.isnan(brier_score([], []))
    assert math.isnan(accuracy([], []))
    assert math.isnan(home_always_accuracy([]))


@pytest.mark.unit
def test_accuracy_and_home_always() -> None:
    assert accuracy([1, 1, 0], [0.6, 0.4, 0.2]) == pytest.approx(2 / 3)
    assert home_always_accuracy([1, 1, 0]) == pytest.approx(2 / 3)
    summary = summarize([1, 0], [0.7, 0.2])
    assert summary["n"] == 2
    assert 0 < summary["logloss"] < 1
    assert 0 < summary["brier"] < 1
