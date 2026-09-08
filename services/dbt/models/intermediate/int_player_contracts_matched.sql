with contracts as (
    select * from {{ ref('stg_player_contracts') }}
)

select
    contracts.player_id,
    contracts.team_id,
    contracts.player_name,
    contracts.player_name_normalized,
    'external_id' as match_method,
    contracts.season,
    contracts.salary,
    contracts.is_fully_guaranteed,
    contracts.remaining_guaranteed,
    contracts.player_age,
    contracts.source_url
from contracts
