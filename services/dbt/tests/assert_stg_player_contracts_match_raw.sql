-- Staging player contracts keep the raw grain.
with raw_counts as (
    select count(*) as row_count from {{ source('source', 'player_contracts') }}
),

stg_counts as (
    select count(*) as row_count from {{ ref('stg_player_contracts') }}
)

select 1 as failure
from raw_counts
cross join stg_counts
where raw_counts.row_count != stg_counts.row_count
