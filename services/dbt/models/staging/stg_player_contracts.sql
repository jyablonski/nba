with source as (
    select * from {{ source('source', 'player_contracts') }}
)

select
    source.player_id,
    source.team_id,
    source.player_name,
    source.player_name_normalized,
    source.season,
    source.salary,
    source.is_fully_guaranteed,
    source.remaining_guaranteed,
    source.player_age,
    source.source_url
from source
