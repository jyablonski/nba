with matched as (
    select * from {{ ref('int_player_contracts_matched') }}
)

select
    matched.bref_player_slug,
    matched.player_id,
    matched.player_name,
    matched.match_method,
    matched.team_id,
    matched.bref_team_abbreviation,
    matched.nba_team_abbreviation,
    matched.season,
    matched.salary,
    matched.is_fully_guaranteed,
    matched.remaining_guaranteed,
    matched.player_age
from matched
