# ML: pregame Elo and logit

Both models are one-shot jobs on Compose profile `tools`, not always-on services and not a betting product.

Two models score every game. **Elo v0** is the champion the product shows; **logit v1** runs in shadow beside it. `CHAMPION_MODEL_VERSION` decides which one `gold.fct_game_predictions` surfaces, so promotion and rollback are an env change plus a re-run, never a backfill. Plan and promotion criteria: `docs/plans/ml-v2.md`.

## What it does

Reads Regular Season **Final** rows from `gold.fct_team_game_results` and walk-forwards ratings: start 1500, home advantage +100, K=20, regress 25% toward 1500 at each season boundary.

Scores upcoming games from `gold.fct_games_schedule` and writes `source.game_predictions`:

- `model_name=elo`, `model_version=elo-v0`
- grain is `game_id` + `as_of` + `model_version`, so a game can be rescored later
- `model_wp` is the **home** win probability; the away side is `1 - model_wp`
- `market_wp` is copied from matching odds when present — a calibration reference, not the label

Playoffs are excluded from training and holdout. Injuries and odds are ingested daily but are **not** Elo features.

## Running it

Needs gold Finals and schedule to exist, so run it after scrape + dbt.

```bash
make ml         # score both models, then the dbt copy into gold.fct_game_predictions
make ml-train   # fit logit v1 and persist its artifact
make ml-eval    # expanding-window logit metrics vs the Elo and always-home baselines

# or directly
docker compose --profile tools run --rm --no-deps ml python -m main eval
docker compose --profile tools run --rm --no-deps ml python -m main score
```

`score` writes a logit row only when a trained artifact exists in `source.model_artifacts`; with no artifact the run is silently Elo-only. Run `make ml-train` once before expecting a second model in the table.

**Never train on the daily cron.** `make ml-train` is deliberate and manual: training beside the always-on stack is how the refresh starts OOMing, and a model that retrains nightly cannot be reproduced. `refresh-daily.sh` runs `score` only.

Per-season head-to-head metrics (log loss, Brier, accuracy, calibration error, market baselines) land in `gold.fct_prediction_scorecard`.

`eval` prints holdout log loss, Brier, accuracy, and the always-pick-home baseline. It writes nothing.

`score` fits on all loaded Regular Season Finals and upserts a new `as_of` batch. `make refresh` already runs it after dbt; an ml failure fails the whole script.

Unit tests: `make test-ml` (90% coverage gate, no Docker).

## Not built

No public predictions endpoint, no win-probability badge in the UI, no "who wins tonight" in Ask, no live in-game WP, and no historical odds backfill as training features.

`gold.fct_prediction_scorecard` is computed but nothing reads it yet: no API route, no Cube member, no admin view. Comparing the two models today means querying the mart directly.

One trap worth naming: **do not join `gold.fct_standings` onto a past game and call it "rank that night."** That table is a season-to-date upsert, so doing so leaks the future into the past.
