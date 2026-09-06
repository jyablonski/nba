# Pregame Elo (current)

How to run the ratings job today. Pipeline hook and ingest caveats are also in [data.md](data.md) and [operations.md](operations.md). Backlog (logit, Courtline badge, `/ask` picks) stays in [plans/ml-win-predictions.md](plans/ml-win-predictions.md) — do not treat that plan’s older “not built” phases as current.

## Purpose

Elo v0 is a one-shot **3.14** job on Compose profile `tools`. It is not an always-on service and not a betting product.

## What it does now

Reads Regular Season **Final** rows from `gold.fct_team_game_results` (no playoffs). Walk-forwards ratings: start 1500, home-court +100 Elo, K=20, 25% regress toward 1500 at season change. Scores upcoming `game_id`s from `gold.fct_games_schedule` where status is not Final.

Writes `source.game_predictions` (`model_name=elo`, `model_version=elo-v0`). Grain is `game_id` + `as_of` + `model_version`. `model_wp` is home win probability. `market_wp` is copied from matched h2h odds when present (calibrator, not the label).

`refresh-daily` then runs `dbt run --select stg_game_predictions+` so `gold.fct_game_predictions` has the batch. Same `game_id` can gain a later `as_of`.

Injuries and odds are **ingested** on daily (odds key-gated). Injuries are **not** Elo features in v0.

## Commands

After scrape + dbt so gold Finals and schedule exist:

```bash
docker compose --profile tools run --rm --no-deps ml python -m main eval
docker compose --profile tools run --rm --no-deps ml python -m main score
# local checkout:
cd services/ml && uv run python -m main eval && uv run python -m main score
```

`eval` prints holdout-season (last Regular Season in gold) logloss, Brier, accuracy, and home-always accuracy. It does not write.

`score` fits on all loaded Regular Season Finals and upserts a new `as_of` batch. `make ml` is the score + gold copy; `make refresh` / `refresh-daily-once` already call it after dbt; ml failure fails the script (no extra Slack).

Unit tests: `make test-ml` (90% coverage gate, no Docker).

## What is not shipped

No public predictions API. No Courtline win-prob badge. No `/ask` “who wins tonight”. No live / in-game WP. No playoffs in train or holdout. No historical injury/odds backfill as training features.

Do not join `gold.fct_standings` onto a historical game and call it “rank that night” — that table is a season-to-date upsert.
