with matched as (
    select * from {{ ref('int_player_contracts_matched') }}
)

select
    matched.player_id,
    matched.team_id,
    teams.abbreviation as team_abbreviation,
    matched.player_name,
    matched.match_method,
    matched.season,
    matched.salary,
    matched.is_fully_guaranteed,
    matched.remaining_guaranteed,
    matched.player_age
from matched
left join {{ ref('stg_teams') }} as teams
    on matched.team_id = teams.team_id
