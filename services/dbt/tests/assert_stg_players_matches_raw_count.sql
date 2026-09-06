-- Raw players and staging players must have the same row count.
with raw_counts as (
    select count(*) as row_count from {{ source('source', 'players') }}
),

stg_counts as (
    select count(*) as row_count from {{ ref('stg_players') }}
)

select 1 as failure
from raw_counts
cross join stg_counts
where raw_counts.row_count != stg_counts.row_count
