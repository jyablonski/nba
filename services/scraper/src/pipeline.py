"""Operational gate for scrape → dbt refresh.

Reads the singleton row in ``source.scrape_pipeline`` to decide whether a
run should scrape NBA daily, scrape r/nba, no-op (off-season / no flags),
or skip (disabled). Default is safe: enabled=false until an operator
enables the pipeline.

NBA Stats / BRef / odds daily follows ``enabled`` + ``season_active`` (and
the season window when set): schedule, Finals logs, those games' PBP,
standings, injuries, remaining-year contracts, odds-if-keyed.

Reddit always runs when the pipeline is enabled (or ``--force``). It is
not behind ``season_active``. Missing ``REDDIT_*`` skips HTTP like odds.

Source DDL is owned by Alembic (``make db-migrate``); this module does
not CREATE TABLES.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from notify import SyncAlert, SyncFailedError
from sqlalchemy.orm import Session

from config import missing_reddit_env_names
from db import get_session
from queries.pipeline_runs import (
    INSERT_PIPELINE_RUN,
    UPDATE_PIPELINE_RUN,
    UPDATE_PIPELINE_RUN_DBT_EXIT,
)
from queries.scrape_pipeline import (
    SELECT_PIPELINE_CONFIG,
    UPDATE_PIPELINE_ENABLED,
    UPDATE_PIPELINE_SUCCESS,
)
from scrapers import current_season
from scrapers.contracts import scrape_contracts
from scrapers.games import scrape_games, scrape_todays_games
from scrapers.injuries import scrape_injuries
from scrapers.odds import scrape_odds
from scrapers.play_by_play import scrape_play_by_play
from scrapers.player_game_logs import scrape_logs_for_games, scrape_player_game_logs
from scrapers.reddit import DEFAULT_SUBREDDIT, scrape_reddit
from scrapers.standings import scrape_standings

ScrapeAction = Literal[
    "daily",
    "season",
    "reddit",
    "noop",
    "skipped_disabled",
    "skipped_offseason",
    "skipped_mode_none",
]

# Modest daily r/nba pull: hot + top for the day, plus top-N comments per post.
DAILY_REDDIT_SUBREDDIT = DEFAULT_SUBREDDIT
DAILY_REDDIT_LIMIT = 50
DAILY_REDDIT_TIME_FILTER = "day"
DAILY_REDDIT_COMMENTS_PER_POST = 10

logger = logging.getLogger(__name__)

_NBA_RUN_ACTIONS = frozenset({"daily", "season"})


@dataclass(frozen=True)
class PipelineConfig:
    enabled: bool
    season_active: bool
    season_start: date | None
    season_end: date | None
    scrape_mode: str
    target_season: str | None
    last_success_at: datetime | None
    last_scrape_date: date | None
    reason: str | None
    updated_at: datetime | None

    @classmethod
    def from_row(cls, row: Any) -> PipelineConfig:
        return cls(
            enabled=bool(row.enabled),
            season_active=bool(row.season_active),
            season_start=row.season_start,
            season_end=row.season_end,
            scrape_mode=str(row.scrape_mode or "daily"),
            target_season=row.target_season,
            last_success_at=row.last_success_at,
            last_scrape_date=row.last_scrape_date,
            reason=row.reason,
            updated_at=row.updated_at,
        )


def load_config(session: Session) -> PipelineConfig:
    row = session.execute(SELECT_PIPELINE_CONFIG).one()
    return PipelineConfig.from_row(row)


def set_enabled(
    session: Session,
    *,
    enabled: bool,
    reason: str | None = None,
    season_active: bool | None = None,
    season_start: date | None = None,
    season_end: date | None = None,
    scrape_mode: str | None = None,
    target_season: str | None = None,
) -> PipelineConfig:
    session.execute(
        UPDATE_PIPELINE_ENABLED,
        {
            "enabled": enabled,
            "season_active": season_active,
            "season_start": season_start,
            "season_end": season_end,
            "scrape_mode": scrape_mode,
            "target_season": target_season,
            "reason": reason,
        },
    )
    return load_config(session)


def in_season_window(config: PipelineConfig, today: date | None = None) -> bool:
    """True when scraping is in-season.

    Prefer explicit ``season_active``. If season_start/end are set, also
    require ``today`` to fall inside that inclusive window.
    """
    day = today or date.today()
    if not config.season_active:
        return False
    if config.season_start and day < config.season_start:
        return False
    return not (config.season_end and day > config.season_end)


def decide_action(
    config: PipelineConfig,
    *,
    force: bool = False,
    today: date | None = None,
) -> tuple[ScrapeAction, str]:
    """Return the NBA scrape action (reddit is decided separately).

    ``--force`` bypasses ``enabled`` and the season window so a manual test
    can run the basketball daily. It does not change ``scrape_mode=none``.
    """
    if not force and not config.enabled:
        return (
            "skipped_disabled",
            "Pipeline disabled in source.scrape_pipeline (enable to run on schedule).",
        )

    if not force and not in_season_window(config, today=today):
        return (
            "skipped_offseason",
            "Season inactive or outside season_start/season_end window.",
        )

    mode = (config.scrape_mode or "daily").lower()
    if mode == "none":
        return ("skipped_mode_none", "scrape_mode=none; nothing to scrape.")
    if mode == "season":
        if not config.target_season:
            return ("noop", "scrape_mode=season but target_season is unset.")
        return ("season", f"Scrape season {config.target_season}.")
    return (
        "daily",
        "Scrape today's slate (Final + upcoming), logs, PBP for those Finals, standings, injuries, contracts, odds.",
    )


def should_run_reddit(config: PipelineConfig, *, force: bool = False) -> bool:
    """Everyday r/nba when the pipeline is allowed to run.

    Requires ``enabled`` unless ``--force``. Not gated by ``season_active``.
    Missing ``REDDIT_*`` skips HTTP inside ``execute_reddit`` (like odds).
    """
    return bool(force or config.enabled)


def compose_run_action(nba_action: ScrapeAction, run_reddit: bool) -> str:
    nba_runs = nba_action in _NBA_RUN_ACTIONS
    if nba_runs and run_reddit:
        return f"{nba_action}+reddit"
    if run_reddit and not nba_runs:
        return "reddit"
    return nba_action


def _final_game_ids(games: list[dict]) -> list[str]:
    return [str(game["game_id"]) for game in games if game.get("game_id")]


def execute_scrape(
    action: ScrapeAction,
    config: PipelineConfig,
    *,
    alert: SyncAlert | None = None,
) -> tuple[int, str]:
    """Run the scrape implied by ``action``. Returns (rows_or_games, detail)."""
    collector = alert if alert is not None else SyncAlert(action)
    if action == "daily":
        games = collector.try_run("todays_games", scrape_todays_games)
        season = current_season()
        n_standings = collector.try_run(
            "standings",
            lambda: scrape_standings(season),
            season=season,
        )
        n_injuries = collector.try_run("injuries", scrape_injuries)
        n_odds = collector.try_run("odds", scrape_odds)
        contracts = collector.try_run("contracts", scrape_contracts)
        standings_count = 0 if n_standings is None else n_standings
        injuries_count = 0 if n_injuries is None else n_injuries
        odds_count = 0 if n_odds is None else n_odds
        if contracts is None:
            n_contracts, n_payroll = 0, 0
        else:
            n_contracts, n_payroll = contracts
        snapshot_count = standings_count + injuries_count + odds_count + n_contracts + n_payroll
        extra = (
            f"standings: {standings_count}; injuries: {injuries_count}; "
            f"odds: {odds_count}; contracts: {n_contracts}; payroll: {n_payroll}."
        )
        if not games:
            collector.raise_if_failed()
            return (
                snapshot_count,
                f"No completed games today; {extra}",
            )
        game_ids = _final_game_ids(games)
        count = collector.try_run("player_game_logs", lambda: scrape_logs_for_games(games))
        n_pbp = collector.try_run(
            "play_by_play",
            lambda: scrape_play_by_play(game_ids=game_ids),
        )
        log_count = 0 if count is None else count
        pbp_count = 0 if n_pbp is None else n_pbp
        collector.raise_if_failed()
        return (
            log_count + snapshot_count + pbp_count,
            f"Upserted logs for {len(games)} game(s); {log_count} player log rows; "
            f"pbp: {pbp_count}; {extra}",
        )
    if action == "season":
        season = config.target_season
        assert season is not None
        n_games = collector.try_run("games", lambda: scrape_games(season), season=season)
        n_logs = collector.try_run(
            "player_game_logs",
            lambda: scrape_player_game_logs(season, active_only=False),
            season=season,
        )
        n_standings = collector.try_run(
            "standings",
            lambda: scrape_standings(season),
            season=season,
        )
        games_count = 0 if n_games is None else n_games
        log_count = 0 if n_logs is None else n_logs
        standings_count = 0 if n_standings is None else n_standings
        collector.raise_if_failed()
        return (
            games_count + log_count + standings_count,
            f"Season {season}: {games_count} games, {log_count} log rows, "
            f"{standings_count} standings.",
        )
    return (0, f"No scrape executed for action={action}.")


def execute_reddit(alert: SyncAlert | None = None) -> int | None:
    """Daily r/nba posts (hot + top for the day) and top-N comments per post.

    Not team subs. Missing ``REDDIT_*`` skips HTTP and returns 0 (same
    pattern as odds).
    """
    collector = alert if alert is not None else SyncAlert("reddit")
    if missing_reddit_env_names():
        logger.info("REDDIT_* unset; skipping reddit scrape")
        return 0
    return collector.try_run(
        "reddit",
        lambda: scrape_reddit(
            subreddit=DAILY_REDDIT_SUBREDDIT,
            limit=DAILY_REDDIT_LIMIT,
            time_filter=DAILY_REDDIT_TIME_FILTER,
            comments_per_post=DAILY_REDDIT_COMMENTS_PER_POST,
        ),
    )


def start_run(session: Session, *, triggered_by: str, scrape_action: str) -> int:
    run_id = session.execute(
        INSERT_PIPELINE_RUN,
        {"triggered_by": triggered_by, "scrape_action": scrape_action},
    ).scalar_one()
    return int(run_id)


def finish_run(
    session: Session,
    run_id: int,
    *,
    status: str,
    scrape_exit: int | None = None,
    dbt_exit: int | None = None,
    detail: str | None = None,
    reddit_ran: bool = False,
    reddit_exit: int | None = None,
) -> None:
    session.execute(
        UPDATE_PIPELINE_RUN,
        {
            "run_id": run_id,
            "status": status,
            "scrape_exit": scrape_exit,
            "dbt_exit": dbt_exit,
            "detail": detail,
            "reddit_ran": reddit_ran,
            "reddit_exit": reddit_exit,
        },
    )


def mark_scrape_success(session: Session, *, scrape_date: date | None = None) -> None:
    session.execute(
        UPDATE_PIPELINE_SUCCESS,
        {"scrape_date": scrape_date or date.today()},
    )


def run_pipeline_scrape(
    *,
    force: bool = False,
    triggered_by: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Gate + scrape. Does not run dbt (orchestrator / Make target does)."""
    day = today or date.today()
    by = triggered_by or ("force" if force else "manual")

    with get_session() as session:
        config = load_config(session)
        nba_action, detail = decide_action(config, force=force, today=day)
        run_reddit = should_run_reddit(config, force=force)
        action = compose_run_action(nba_action, run_reddit)
        run_id = start_run(session, triggered_by=by, scrape_action=action)

    nba_runs = nba_action in _NBA_RUN_ACTIONS
    if not nba_runs and not run_reddit:
        with get_session() as session:
            finish_run(
                session,
                run_id,
                status="skipped",
                scrape_exit=0,
                detail=detail,
            )
        return {
            "run_id": run_id,
            "status": "skipped",
            "action": action,
            "detail": detail,
            "scrape_exit": 0,
            "reddit_ran": False,
            "reddit_exit": None,
        }

    scrape_exit = 0
    scrape_detail = detail
    status = "success"
    reddit_ran = False
    reddit_exit: int | None = None
    alert = SyncAlert("pipeline")
    parts: list[str] = []
    try:
        if nba_runs:
            try:
                _count, nba_detail = execute_scrape(nba_action, config, alert=alert)
                parts.append(nba_detail)
            except SyncFailedError:
                parts.append(detail)
        elif run_reddit:
            parts.append(detail)
        if run_reddit:
            reddit_ran = True
            n_reddit = execute_reddit(alert)
            reddit_exit = 0 if n_reddit is not None else 1
            if n_reddit is not None:
                parts.append(f"reddit: {n_reddit} r/{DAILY_REDDIT_SUBREDDIT} posts.")
        alert.raise_if_failed()
        scrape_detail = " ".join(part for part in parts if part) or detail
    except Exception as exc:  # noqa: BLE001 — surface to source.pipeline_runs
        scrape_exit = 1
        status = "failed"
        scrape_detail = f"{' '.join(part for part in parts if part) or detail} Error: {exc}"
        if not alert.failures:
            alert.record(action, exc)

    try:
        with get_session() as session:
            if status == "success":
                mark_scrape_success(session, scrape_date=day)
            finish_run(
                session,
                run_id,
                status=status,
                scrape_exit=scrape_exit,
                detail=scrape_detail,
                reddit_ran=reddit_ran,
                reddit_exit=reddit_exit,
            )
    finally:
        if status == "failed":
            alert.notify()

    return {
        "run_id": run_id,
        "status": status,
        "action": action,
        "detail": scrape_detail,
        "scrape_exit": scrape_exit,
        "reddit_ran": reddit_ran,
        "reddit_exit": reddit_exit,
    }


def update_run_dbt_exit(run_id: int, dbt_exit: int, *, detail: str | None = None) -> None:
    with get_session() as session:
        session.execute(
            UPDATE_PIPELINE_RUN_DBT_EXIT,
            {"run_id": run_id, "dbt_exit": dbt_exit, "detail": detail},
        )
