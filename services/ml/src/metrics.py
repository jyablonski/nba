"""Walk-forward evaluation metrics. Logloss is primary; accuracy is reported only."""

from __future__ import annotations

import math
from collections.abc import Sequence

EPS = 1e-15


def log_loss(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    if not y_true:
        return float("nan")
    total = 0.0
    for label, prob in zip(y_true, y_prob, strict=True):
        clipped = min(1.0 - EPS, max(EPS, float(prob)))
        if label:
            total += -math.log(clipped)
        else:
            total += -math.log(1.0 - clipped)
    return total / len(y_true)


def brier_score(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    if not y_true:
        return float("nan")
    total = 0.0
    for label, prob in zip(y_true, y_prob, strict=True):
        total += (float(prob) - float(label)) ** 2
    return total / len(y_true)


def accuracy(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    if not y_true:
        return float("nan")
    correct = 0
    for label, prob in zip(y_true, y_prob, strict=True):
        predicted = 1 if float(prob) >= 0.5 else 0
        if predicted == int(label):
            correct += 1
    return correct / len(y_true)


def home_always_accuracy(y_true: Sequence[int]) -> float:
    if not y_true:
        return float("nan")
    return sum(y_true) / len(y_true)


def summarize(
    y_true: Sequence[int],
    y_prob: Sequence[float],
) -> dict[str, float]:
    return {
        "n": float(len(y_true)),
        "logloss": log_loss(y_true, y_prob),
        "brier": brier_score(y_true, y_prob),
        "accuracy": accuracy(y_true, y_prob),
        "home_always_accuracy": home_always_accuracy(y_true),
    }
