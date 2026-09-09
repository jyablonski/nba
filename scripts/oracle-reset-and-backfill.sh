#!/usr/bin/env bash
# Reset the Oracle Postgres volume, pull the runtime/job images, load a full
# season from Basketball-Reference, validate source coverage, then run dbt and
# Elo before bringing the serving stack back.

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE="${COMPOSE:-docker compose}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$ROOT")}"
export COMPOSE_PROJECT_NAME

# CI publishes all repo-built runtime/job images. Postgres and Caddy remain
# upstream images; the Oracle host pulls the repo images from GHCR below.
IMAGE_PREFIX="${IMAGE_PREFIX-ghcr.io/jyablonski/}"
IMAGE_TAG="${IMAGE_TAG-$(git rev-parse HEAD)}"
if [[ -n "$IMAGE_PREFIX" ]]; then
  IMAGE_PREFIX="${IMAGE_PREFIX%/}/"
fi
export IMAGE_PREFIX IMAGE_TAG

SEASONS="${SEASONS:-2025-26}"
WITH_REDDIT="${WITH_REDDIT:-0}"
BUILD_TOOLS="${BUILD_TOOLS:-0}"
RESET_VOLUME="${RESET_VOLUME:-1}"
MIN_FINAL_GAMES="${MIN_FINAL_GAMES:-1200}"

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
STACK_DOWN=0

compose() {
  DOCKER_TARGET=runtime $COMPOSE "${COMPOSE_FILES[@]}" "$@"
}

tool() {
  compose --profile tools run --rm --no-deps "$@"
}

log() {
  printf '\n[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

die() {
  echo "error: $*" >&2
  exit 1
}

restore_stack() {
  local status=$?
  if [[ "$STACK_DOWN" == "1" ]]; then
    log "restoring production serving stack"
    if ! compose up -d postgres api frontend mcp cube caddy; then
      echo "error: serving stack could not be restored" >&2
      [[ "$status" == "0" ]] && status=1
    fi
  fi
  exit "$status"
}

trap restore_stack EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

command -v docker >/dev/null 2>&1 || die "docker is required"
[[ -f .env ]] || die "run this from the deployed repo with .env present"
[[ "$RESET_VOLUME" == "0" || "$RESET_VOLUME" == "1" ]] || die "RESET_VOLUME must be 0 or 1"
[[ "$BUILD_TOOLS" == "0" || "$BUILD_TOOLS" == "1" ]] || die "BUILD_TOOLS must be 0 or 1"
[[ "$WITH_REDDIT" == "0" || "$WITH_REDDIT" == "1" ]] || die "WITH_REDDIT must be 0 or 1"

IFS=',' read -r -a season_list <<< "$SEASONS"
for index in "${!season_list[@]}"; do
  season="${season_list[$index]}"
  season="${season//[[:space:]]/}"
  [[ -n "$season" ]] || die "SEASONS contains an empty season"
  season_list[$index]="$season"
done

PG_VOLUME="${COMPOSE_PROJECT_NAME}_pgdata"

log "validating production compose configuration"
compose config >/dev/null
log "target seasons: ${season_list[*]}"
log "repo images: ${IMAGE_PREFIX}nba-api:${IMAGE_TAG}, ${IMAGE_PREFIX}nba-frontend:${IMAGE_TAG}, ${IMAGE_PREFIX}nba-migrate:${IMAGE_TAG}, ${IMAGE_PREFIX}nba-mcp:${IMAGE_TAG}, ${IMAGE_PREFIX}nba-cube:${IMAGE_TAG}, ${IMAGE_PREFIX}nba-scraper:${IMAGE_TAG}, ${IMAGE_PREFIX}nba-dbt:${IMAGE_TAG}, ${IMAGE_PREFIX}nba-ml:${IMAGE_TAG}"

if [[ "$RESET_VOLUME" == "1" ]]; then
  echo
  echo "This will permanently delete only Docker volume: $PG_VOLUME"
  echo "Caddy certificate/config volumes will be retained."
  if [[ "${CONFIRM_RESET:-}" != "RESET" ]]; then
    read -r -p "Type RESET to continue: " confirmation || die "reset not confirmed"
    [[ "$confirmation" == "RESET" ]] || die "reset not confirmed"
  fi
fi

log "stopping production containers without deleting volumes"
compose down --remove-orphans
STACK_DOWN=1

log "pulling repo images"
compose pull api frontend migrate mcp cube scraper dbt ml

if [[ "$BUILD_TOOLS" == "1" ]]; then
  log "building migrate, scraper, dbt, ML, and MCP images sequentially"
  compose --parallel 1 --profile tools build migrate scraper dbt ml mcp
fi

if [[ "$RESET_VOLUME" == "1" ]]; then
  if docker volume inspect "$PG_VOLUME" >/dev/null 2>&1; then
    log "removing Postgres volume $PG_VOLUME"
    docker volume rm "$PG_VOLUME" >/dev/null
  else
    log "Postgres volume $PG_VOLUME does not exist; continuing with a new volume"
  fi
else
  log "RESET_VOLUME=0; preserving existing Postgres volume"
fi

log "starting clean Postgres and waiting for readiness"
compose up -d postgres --wait

log "running Alembic migrations"
compose run --rm --no-deps migrate alembic upgrade head

scrape_all_args=(scrape-all --seasons "$SEASONS")
if [[ "$WITH_REDDIT" == "1" ]]; then
  scrape_all_args+=(--with-reddit)
fi

log "scraping teams, players, contracts, schedules, game logs, and standings"
tool scraper python -m main "${scrape_all_args[@]}"

log "scraping current injuries and odds snapshots"
tool scraper python -m main scrape-injuries
tool scraper python -m main scrape-odds

for season in "${season_list[@]}"; do
  log "scraping play-by-play for $season; this is intentionally sequential"
  tool scraper python -m main scrape-play-by-play --season "$season"
done

db_query() {
  local query="$1"
  compose exec -T postgres sh -c \
    'psql -v ON_ERROR_STOP=1 -At -F "|" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"' \
    sh "$query"
}

log "validating schedule and per-game logs/PBP coverage"
declare -A covered_seasons=()
schedule_counts="$(db_query "
  SELECT season, status, count(*)
  FROM source.games
  GROUP BY season, status
  ORDER BY season, status;
")"
printf '%s\n' "$schedule_counts"

coverage="$(db_query "
  WITH final_games AS (
    SELECT game_id, season
    FROM source.games
    WHERE status = 'Final'
  ),
  logs AS (
    SELECT DISTINCT game_id FROM source.player_game_logs
  ),
  pbp AS (
    SELECT DISTINCT game_id FROM source.play_by_play
  )
  SELECT f.season,
         count(*) AS final_games,
         count(logs.game_id) AS log_games,
         count(pbp.game_id) AS pbp_games,
         count(*) FILTER (WHERE logs.game_id IS NULL) AS games_missing_logs,
         count(*) FILTER (WHERE pbp.game_id IS NULL) AS games_missing_pbp
  FROM final_games f
  LEFT JOIN logs ON logs.game_id = f.game_id
  LEFT JOIN pbp ON pbp.game_id = f.game_id
  GROUP BY f.season
  ORDER BY f.season;
")"
printf '%s\n' "$coverage"

while IFS='|' read -r season final_games log_games pbp_games missing_logs missing_pbp; do
  [[ -n "${season:-}" ]] || continue
  covered_seasons["$season"]=1
  if (( final_games < MIN_FINAL_GAMES )); then
    die "$season has only $final_games Final games; expected at least $MIN_FINAL_GAMES"
  fi
  if [[ "$missing_logs" != "0" || "$missing_pbp" != "0" ]]; then
    die "$season is incomplete: missing_logs=$missing_logs missing_pbp=$missing_pbp"
  fi
done <<< "$coverage"

for season in "${season_list[@]}"; do
  [[ -n "${covered_seasons[$season]+x}" ]] || die "$season has no Final games in source.games"
done

# --full-refresh is required, not optional: int_play_by_play_events is
# incremental, and a reset that preserves the Postgres volume (RESET_VOLUME=0)
# would otherwise keep its existing rows and only append newly scraped games.
# A backfill exists to produce a clean warehouse, so rebuild every model.
log "running dbt deps and build (seeds, models, and tests in DAG order, full refresh)"
tool dbt sh -c \
  'dbt deps --profiles-dir . && dbt build --profiles-dir . --full-refresh'

log "running Elo scoring"
tool ml python -m main score

log "publishing ML predictions through dbt"
tool dbt sh -c \
  'dbt deps --profiles-dir . && dbt run --profiles-dir . --select stg_game_predictions+'

log "source and warehouse refresh complete"
