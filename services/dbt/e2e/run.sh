#!/usr/bin/env bash
# Seed Postgres, run dbt, and assert gold mart outputs.
# Source tables come from Alembic (compose migrate) before this script runs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=nba}"
: "${POSTGRES_USER:=nba_user}"
: "${POSTGRES_PASSWORD:=nba_pass}"

export PGPASSWORD="$POSTGRES_PASSWORD"
PSQL=(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1)

echo "==> waiting for postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}"
for _ in $(seq 1 60); do
  if "${PSQL[@]}" -c "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
"${PSQL[@]}" -c "SELECT 1" >/dev/null

echo "==> seeding sample rows"
"${PSQL[@]}" -f "$ROOT/e2e/seed.sql"

echo "==> dbt deps / build"
# Image build bakes dbt_packages; deps still runs here so a development
# target without a rebuild (or a bind-mounted project) can compile.
uv run dbt deps --profiles-dir .
uv run dbt build --profiles-dir .

echo "==> asserting gold outputs"
"${PSQL[@]}" <<'SQL'
DO $$
DECLARE
  team_count integer;
  player_count integer;
  game_count integer;
  log_count integer;
  b2b_count integer;
  kawhi_games integer;
  gsw_lat numeric;
  gsw_lon numeric;
  curry_salary bigint;
  gsw_payroll bigint;
  contract_count integer;
  standings_count integer;
  gsw_rank integer;
  gsw_gb numeric;
  schedule_count integer;
  scheduled_count integer;
  prediction_count integer;
  prediction_duplicate_count integer;
  feature_count integer;
  scheduled_feature_outcome_count integer;
  scorecard_count integer;
  injury_matched integer;
  scoring_count integer;
  flow_count integer;
  flow_max_lead integer;
  reddit_post_count integer;
  reddit_comment_count integer;
  reddit_comment_fk integer;
BEGIN
  SELECT count(*) INTO team_count FROM gold.dim_teams;
  SELECT count(*) INTO player_count FROM gold.dim_players;
  SELECT count(*) INTO game_count FROM gold.fct_team_game_results;
  SELECT count(*) INTO log_count FROM gold.fct_player_game_logs;
  SELECT count(*) INTO b2b_count
  FROM gold.fct_player_game_logs
  WHERE is_back_to_back IS TRUE;
  SELECT career_games_played INTO kawhi_games
  FROM gold.dim_players
  WHERE player_id = '22222222-2222-4222-8222-222222222222';

  IF team_count < 3 THEN
    RAISE EXCEPTION 'expected >= 3 teams, got %', team_count;
  END IF;
  IF player_count < 2 THEN
    RAISE EXCEPTION 'expected >= 2 players, got %', player_count;
  END IF;
  IF game_count < 3 THEN
    RAISE EXCEPTION 'expected >= 3 games, got %', game_count;
  END IF;
  IF log_count < 5 THEN
    RAISE EXCEPTION 'expected >= 5 player game logs, got %', log_count;
  END IF;
  IF b2b_count < 1 THEN
    RAISE EXCEPTION 'expected >= 1 back-to-back game log, got %', b2b_count;
  END IF;
  IF kawhi_games IS DISTINCT FROM 3 THEN
    RAISE EXCEPTION 'expected Kawhi career_games_played=3, got %', kawhi_games;
  END IF;

  SELECT arena_latitude, arena_longitude INTO gsw_lat, gsw_lon
  FROM gold.dim_teams
  WHERE team_id = '7bf8726a-a852-452d-b81f-14839127c5fb';
  IF gsw_lat IS NULL OR gsw_lon IS NULL THEN
    RAISE EXCEPTION 'expected GSW arena_latitude/arena_longitude from team arena seed';
  END IF;

  SELECT current_season_salary INTO curry_salary
  FROM gold.dim_players
  WHERE player_id = '11111111-1111-4111-8111-111111111111';
  IF curry_salary IS DISTINCT FROM 50000000 THEN
    RAISE EXCEPTION 'expected Curry current_season_salary=50000000, got %', curry_salary;
  END IF;

  SELECT current_season_payroll INTO gsw_payroll
  FROM gold.dim_teams
  WHERE team_id = '7bf8726a-a852-452d-b81f-14839127c5fb';
  IF gsw_payroll IS DISTINCT FROM 51000000 THEN
    RAISE EXCEPTION 'expected GSW current_season_payroll=51000000, got %', gsw_payroll;
  END IF;

  SELECT count(*) INTO contract_count FROM gold.fct_player_contracts;
  IF contract_count < 4 THEN
    RAISE EXCEPTION 'expected >= 4 player contracts, got %', contract_count;
  END IF;

  SELECT count(*) INTO standings_count FROM gold.fct_standings;
  IF standings_count < 3 THEN
    RAISE EXCEPTION 'expected >= 3 standings rows, got %', standings_count;
  END IF;

  SELECT conference_rank, games_back INTO gsw_rank, gsw_gb
  FROM gold.fct_standings
  WHERE team_id = '7bf8726a-a852-452d-b81f-14839127c5fb'
    AND season = '2024-25'
    AND season_type = 'Regular Season';
  IF gsw_rank IS DISTINCT FROM 1 THEN
    RAISE EXCEPTION 'expected GSW conference_rank=1, got %', gsw_rank;
  END IF;
  IF gsw_gb IS DISTINCT FROM 0 THEN
    RAISE EXCEPTION 'expected GSW games_back=0, got %', gsw_gb;
  END IF;

  SELECT count(*) INTO schedule_count FROM gold.fct_games_schedule;
  IF schedule_count < 4 THEN
    RAISE EXCEPTION 'expected >= 4 schedule rows, got %', schedule_count;
  END IF;

  SELECT count(*) INTO scheduled_count
  FROM gold.fct_games_schedule
  WHERE status = 'Scheduled';
  IF scheduled_count < 1 THEN
    RAISE EXCEPTION 'expected >= 1 Scheduled game, got %', scheduled_count;
  END IF;

  SELECT count(*) INTO prediction_count FROM gold.fct_game_predictions;
  IF prediction_count < 1 THEN
    RAISE EXCEPTION 'expected >= 1 prediction row, got %', prediction_count;
  END IF;

  SELECT count(*) INTO prediction_duplicate_count
  FROM (
    SELECT game_id, model_version
    FROM gold.fct_game_predictions
    GROUP BY game_id, model_version
    HAVING count(*) > 1
  ) duplicates;
  IF prediction_duplicate_count <> 0 THEN
    RAISE EXCEPTION 'expected one champion prediction per game, got % duplicate groups', prediction_duplicate_count;
  END IF;

  SELECT count(*) INTO feature_count FROM silver.int_game_features;
  IF feature_count < 4 THEN
    RAISE EXCEPTION 'expected >= 4 game feature rows, got %', feature_count;
  END IF;

  SELECT count(*) INTO scheduled_feature_outcome_count
  FROM silver.int_game_features
  WHERE game_id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd'
    AND home_won IS NOT NULL;
  IF scheduled_feature_outcome_count <> 0 THEN
    RAISE EXCEPTION 'expected scheduled game to have null home_won, got % rows', scheduled_feature_outcome_count;
  END IF;

  SELECT count(*) INTO scorecard_count FROM gold.fct_prediction_scorecard;
  IF scorecard_count < 1 THEN
    RAISE EXCEPTION 'expected >= 1 prediction scorecard row, got %', scorecard_count;
  END IF;

  SELECT count(*) INTO injury_matched
  FROM silver.int_player_injuries_matched
  WHERE match_method = 'external_id';
  IF injury_matched < 1 THEN
    RAISE EXCEPTION 'expected >= 1 matched injury row, got %', injury_matched;
  END IF;

  SELECT count(*) INTO scoring_count FROM gold.fct_play_by_play_scoring;
  IF scoring_count < 6 THEN
    RAISE EXCEPTION 'expected >= 6 scoring plays, got %', scoring_count;
  END IF;

  SELECT count(*), max(max_lead) INTO flow_count, flow_max_lead
  FROM gold.fct_game_flow;
  IF flow_count < 1 THEN
    RAISE EXCEPTION 'expected >= 1 game flow row, got %', flow_count;
  END IF;
  IF flow_max_lead IS NULL OR flow_max_lead < 1 THEN
    RAISE EXCEPTION 'expected game flow max_lead >= 1, got %', flow_max_lead;
  END IF;

  SELECT count(*) INTO reddit_post_count FROM gold.fct_reddit_posts;
  IF reddit_post_count < 1 THEN
    RAISE EXCEPTION 'expected >= 1 reddit post, got %', reddit_post_count;
  END IF;

  SELECT count(*) INTO reddit_comment_count FROM gold.fct_reddit_comments;
  IF reddit_comment_count < 2 THEN
    RAISE EXCEPTION 'expected >= 2 reddit comments, got %', reddit_comment_count;
  END IF;

  SELECT count(*) INTO reddit_comment_fk
  FROM gold.fct_reddit_comments comments
  JOIN gold.fct_reddit_posts posts ON posts.reddit_id = comments.post_reddit_id;
  IF reddit_comment_fk IS DISTINCT FROM reddit_comment_count THEN
    RAISE EXCEPTION 'expected every reddit comment to join a post, got % of %',
      reddit_comment_fk, reddit_comment_count;
  END IF;

  RAISE NOTICE 'dbt e2e assertions passed (teams=%, players=%, games=%, logs=%, b2b=%, standings=%, schedule=%, predictions=%, scoring=%, flow=%, reddit_posts=%, reddit_comments=%)',
    team_count, player_count, game_count, log_count, b2b_count, standings_count,
    schedule_count, prediction_count, scoring_count, flow_count,
    reddit_post_count, reddit_comment_count;
END $$;
SQL

echo "==> dbt e2e passed"
