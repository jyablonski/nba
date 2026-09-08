"""SQL against gold team and player game facts."""

from __future__ import annotations

from sqlalchemy import text

LIST_GAMES_COUNT = text(
    """
    SELECT count(*) AS total
    FROM gold.fct_team_game_results
    WHERE (:season IS NULL OR season = :season)
      AND (:season_type IS NULL OR season_type = :season_type)
    """
)

LIST_GAMES = text(
    """
    SELECT
        games.game_id,
        games.season,
        games.season_type,
        games.game_date,
        coalesce(nullif(btrim(games.arena), ''), home_teams.arena_name) AS arena,
        coalesce(nullif(btrim(games.arena_city), ''), home_teams.city) AS arena_city,
        games.arena_state,
        games.home_team_id,
        games.home_team_abbreviation,
        games.home_team_name,
        games.home_score,
        games.away_team_id,
        games.away_team_abbreviation,
        games.away_team_name,
        games.away_score,
        games.winning_team_id,
        games.winner_location,
        games.score_margin
    FROM gold.fct_team_game_results AS games
    LEFT JOIN gold.dim_teams AS home_teams
        ON home_teams.team_id = games.home_team_id
    WHERE (:season IS NULL OR games.season = :season)
      AND (:season_type IS NULL OR games.season_type = :season_type)
    ORDER BY games.game_date DESC, games.game_id DESC
    LIMIT :limit OFFSET :offset
    """
)

GAME_EXISTS = text(
    """
    SELECT 1
    FROM gold.fct_team_game_results
    WHERE game_id = :game_id
    """
)

LIST_PLAY_BY_PLAY = text(
    """
    SELECT
        scoring.game_id,
        scoring.action_number,
        scoring.period,
        scoring.clock,
        scoring.clock_remaining_seconds,
        scoring.elapsed_seconds,
        scoring.score_home,
        scoring.score_away,
        scoring.score_differential,
        scoring.home_points,
        scoring.away_points,
        scoring.points_scored,
        scoring.scoring_side,
        scoring.team_id,
        scoring.player_id,
        scoring.action_type,
        scoring.sub_type,
        scoring.description
    FROM gold.fct_play_by_play_scoring AS scoring
    WHERE scoring.game_id = :game_id
    ORDER BY scoring.elapsed_seconds, scoring.action_number
    """
)

GET_GAME_FLOW = text(
    """
    SELECT
        games.game_id,
        games.season,
        games.game_date,
        games.home_team_id,
        games.home_team_abbreviation,
        games.home_team_name,
        home_teams.primary_color AS home_primary_color,
        home_teams.alternate_color AS home_alternate_color,
        games.home_score,
        games.away_team_id,
        games.away_team_abbreviation,
        games.away_team_name,
        away_teams.primary_color AS away_primary_color,
        away_teams.alternate_color AS away_alternate_color,
        games.away_score,
        games.winning_team_id,
        flow.winning_team_abbreviation,
        games.winner_location,
        flow.scoring_play_count,
        flow.max_home_lead,
        flow.max_away_lead,
        flow.max_lead,
        flow.lead_changes,
        flow.ties,
        flow.home_lead_seconds,
        flow.away_lead_seconds,
        flow.tied_seconds,
        flow.home_lead_pct,
        flow.away_lead_pct,
        flow.tied_pct,
        flow.game_elapsed_seconds,
        flow.biggest_run_team_abbreviation,
        flow.biggest_run_winner_points,
        flow.biggest_run_opponent_points,
        flow.biggest_run_start_seconds,
        flow.biggest_run_end_seconds,
        flow.biggest_run_label,
        flow.final_period,
        flow.overtime_periods,
        flow.went_to_overtime,
        flow.largest_lead_blown,
        flow.blown_lead_team_abbreviation,
        flow.comeback_team_abbreviation,
        flow.blown_lead_period,
        flow.blown_lead_elapsed_seconds,
        flow.is_wire_to_wire,
        flow.winner_halftime_margin,
        flow.winner_margin_entering_fourth
    FROM gold.fct_team_game_results AS games
    LEFT JOIN gold.fct_game_flow AS flow
        ON flow.game_id = games.game_id
    LEFT JOIN gold.dim_teams AS home_teams
        ON home_teams.team_id = games.home_team_id
    LEFT JOIN gold.dim_teams AS away_teams
        ON away_teams.team_id = games.away_team_id
    WHERE games.game_id = :game_id
    """
)

LIST_SCHEDULE_COUNT = text(
    """
    SELECT count(*) AS total
    FROM gold.fct_games_schedule AS games
    WHERE games.game_date >= :from_date
      AND (:season IS NULL OR games.season = :season)
      AND (
          :status IS NULL
          OR (
              lower(:status) = 'scheduled'
              AND lower(games.status) NOT IN ('final', '3')
          )
          OR games.status = :status
      )
    """
)

LIST_SCHEDULE = text(
    """
    SELECT
        games.game_id,
        games.season,
        games.season_type,
        games.game_date,
        games.status,
        coalesce(nullif(btrim(games.arena), ''), home_teams.arena_name) AS arena,
        coalesce(nullif(btrim(games.arena_city), ''), home_teams.city) AS arena_city,
        games.arena_state,
        games.home_team_id,
        games.home_team_abbreviation,
        games.home_team_name,
        games.away_team_id,
        games.away_team_abbreviation,
        games.away_team_name
    FROM gold.fct_games_schedule AS games
    LEFT JOIN gold.dim_teams AS home_teams
        ON home_teams.team_id = games.home_team_id
    WHERE games.game_date >= :from_date
      AND (:season IS NULL OR games.season = :season)
      AND (
          :status IS NULL
          OR (
              lower(:status) = 'scheduled'
              AND lower(games.status) NOT IN ('final', '3')
          )
          OR games.status = :status
      )
    ORDER BY games.game_date ASC, games.game_id ASC
    LIMIT :limit OFFSET :offset
    """
)

LIST_SEASONS = text(
    """
    SELECT season FROM (
        SELECT DISTINCT season FROM gold.fct_team_game_results
        UNION
        SELECT DISTINCT season FROM gold.fct_player_game_logs
        UNION
        SELECT DISTINCT season FROM gold.fct_games_schedule
    ) seasons
    WHERE season IS NOT NULL
    ORDER BY season DESC
    """
)


# "Collapse of the season": the biggest lead a team held and still lost, most
# painful first. largest_lead_blown is 0 for wire-to-wire games, so those are
# excluded rather than ranked last.
LIST_BIGGEST_COLLAPSES = text(
    """
    SELECT
        flow.game_id,
        flow.season,
        flow.game_date,
        flow.home_team_abbreviation,
        flow.home_score,
        flow.away_team_abbreviation,
        flow.away_score,
        flow.largest_lead_blown,
        flow.blown_lead_team_abbreviation,
        flow.comeback_team_abbreviation,
        flow.blown_lead_period,
        flow.winner_margin_entering_fourth,
        flow.lead_changes,
        flow.overtime_periods
    FROM gold.fct_game_flow AS flow
    WHERE flow.largest_lead_blown > 0
      AND (:season IS NULL OR flow.season = :season)
    ORDER BY flow.largest_lead_blown DESC, flow.game_date DESC
    LIMIT :limit
    """
)
