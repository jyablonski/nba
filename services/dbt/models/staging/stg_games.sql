with source as (
    select * from {{ source('source', 'games') }}
)

select
    game_id,
    season,
    season_type,
    game_date,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    arena,
    city as arena_city,
    state as arena_state,
    status,
    case
        when home_score > away_score then home_team_id
        when away_score > home_score then away_team_id
    end as winning_team_id,
    abs(home_score - away_score) as score_margin
from source
where status = 'Final'
