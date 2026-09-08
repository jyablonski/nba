with games as (
    select * from {{ ref('stg_games') }}
),

home_teams as (
    select * from {{ ref('stg_teams') }}
),

away_teams as (
    select * from {{ ref('stg_teams') }}
),

home_arenas as (
    select
        team_id::uuid as team_id,
        arena_name,
        arena_city,
        arena_state
    from {{ ref('nba_team_arenas') }}
)

select
    games.game_id,
    games.season,
    games.season_type,
    games.game_date,
    coalesce(games.arena, home_arenas.arena_name) as arena,
    coalesce(games.arena_city, home_arenas.arena_city) as arena_city,
    coalesce(games.arena_state, home_arenas.arena_state) as arena_state,
    games.score_margin,
    games.home_team_id,
    home_teams.abbreviation as home_team_abbreviation,
    home_teams.team_name as home_team_name,
    games.home_score,
    games.away_team_id,
    away_teams.abbreviation as away_team_abbreviation,
    away_teams.team_name as away_team_name,
    games.away_score,
    games.winning_team_id,
    case
        when games.winning_team_id = games.home_team_id then 'home'
        else 'away'
    end as winner_location
from games
left join home_teams
    on games.home_team_id = home_teams.team_id
left join away_teams
    on games.away_team_id = away_teams.team_id
left join home_arenas
    on games.home_team_id = home_arenas.team_id
