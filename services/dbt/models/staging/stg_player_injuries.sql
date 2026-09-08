with source as (
    select * from {{ source('source', 'player_injuries') }}
)

select
    source.player_id,
    source.team_id,
    source.player_name,
    source.player_name_normalized,
    source.update_date,
    source.description,
    source.source_url,
    source.scraped_at
from source
