with injuries as (
    select * from {{ ref('stg_player_injuries') }}
)

select
    injuries.player_id,
    injuries.team_id,
    injuries.player_name,
    injuries.player_name_normalized,
    'external_id' as match_method,
    injuries.update_date,
    injuries.description,
    injuries.source_url,
    injuries.scraped_at
from injuries
