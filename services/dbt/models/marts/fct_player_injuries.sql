with injuries as (
    select * from {{ ref('int_player_injuries_matched') }}
)

select
    injuries.player_name,
    injuries.player_name_normalized,
    injuries.bref_player_slug,
    injuries.bref_team_abbreviation,
    injuries.nba_team_abbreviation,
    injuries.update_date,
    injuries.description,
    injuries.source_url,
    injuries.scraped_at,
    injuries.team_id,
    injuries.player_id,
    injuries.match_method
from injuries
