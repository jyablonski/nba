-- Completed 82-game official snapshots must have 82 Regular Season Finals per team.
-- Catches schedule rows dropped when both sides repeat the "@" matchup.
with regular_season_games as (
    select * from {{ ref('fct_team_game_results') }}
    where season_type = 'Regular Season'
),

home_appearances as (
    select
        regular_season_games.home_team_id as team_id,
        regular_season_games.season
    from regular_season_games
),

away_appearances as (
    select
        regular_season_games.away_team_id as team_id,
        regular_season_games.season
    from regular_season_games
),

appearances as (
    select * from home_appearances
    union all
    select * from away_appearances
),

game_counts as (
    select
        appearances.team_id,
        appearances.season,
        count(*) as games
    from appearances
    group by appearances.team_id, appearances.season
),

standings as (
    select * from {{ ref('fct_standings') }}
),

completed_standings as (
    select
        standings.team_id,
        standings.season,
        standings.wins + standings.losses as games
    from standings
    where standings.season_type = 'Regular Season'
      and standings.wins is not null
      and standings.losses is not null
      and standings.wins + standings.losses = 82
)

select
    completed_standings.team_id,
    completed_standings.season,
    completed_standings.games as standings_games,
    game_counts.games as result_games
from completed_standings
left join game_counts
    on completed_standings.team_id = game_counts.team_id
    and completed_standings.season = game_counts.season
where game_counts.games is distinct from 82
