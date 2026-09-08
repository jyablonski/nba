with injuries as (
    select * from {{ ref('int_player_injuries_matched') }}
)

select
    injuries.player_id,
    injuries.team_id,
    teams.abbreviation as team_abbreviation,
    injuries.player_name,
    injuries.player_name_normalized,
    injuries.update_date,
    injuries.description,
    injuries.source_url,
    injuries.scraped_at,
    injuries.match_method
from injuries
left join {{ ref('stg_teams') }} as teams
    on injuries.team_id = teams.team_id
