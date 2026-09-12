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
    -- The venue seed fills gaps for a home team playing at home, and must not
    -- be mixed into a row that already names a different building. Coalescing
    -- each column on its own put a Mexico City / London / Las Vegas neutral-site
    -- game in the home team's city, because the source names the arena but
    -- leaves city blank. A neutral site keeps a null city rather than a wrong one.
    coalesce(nullif(btrim(games.arena), ''), home_arenas.arena_name) as arena,
    case
        when nullif(btrim(games.arena), '') is null
            or btrim(games.arena) = home_arenas.arena_name
            then coalesce(nullif(btrim(games.arena_city), ''), home_arenas.arena_city)
        else nullif(btrim(games.arena_city), '')
    end as arena_city,
    case
        when nullif(btrim(games.arena), '') is null
            or btrim(games.arena) = home_arenas.arena_name
            then coalesce(nullif(btrim(games.arena_state), ''), home_arenas.arena_state)
        else nullif(btrim(games.arena_state), '')
    end as arena_state,
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
