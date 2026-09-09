# ML: pregame Elo

Elo v0 is a one-shot job on Compose profile `tools`, not an always-on service and not a betting product.

The successor model is planned in `docs/plans/ml-v2.md`; nothing there is built.

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
make ml     # score, then the dbt copy into gold.fct_game_predictions

# or directly
docker compose --profile tools run --rm --no-deps ml python -m main eval
docker compose --profile tools run --rm --no-deps ml python -m main score
```

`eval` prints holdout log loss, Brier, accuracy, and the always-pick-home baseline. It writes nothing.

`score` fits on all loaded Regular Season Finals and upserts a new `as_of` batch. `make refresh` already runs it after dbt; an ml failure fails the whole script.

Unit tests: `make test-ml` (90% coverage gate, no Docker).

## Not built

No public predictions endpoint, no win-probability badge in the UI, no "who wins tonight" in Ask, no live in-game WP, and no historical injury or odds backfill as training features.

One trap worth naming: **do not join `gold.fct_standings` onto a past game and call it "rank that night."** That table is a season-to-date upsert, so doing so leaks the future into the past.
