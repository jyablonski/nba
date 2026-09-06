-- Staging final games must match raw games with status Final.
with raw_final_counts as (
    select count(*) as row_count
    from {{ source('source', 'games') }}
    where status = 'Final'
),

stg_counts as (
    select count(*) as row_count from {{ ref('stg_games') }}
)

select 1 as failure
from raw_final_counts
cross join stg_counts
where raw_final_counts.row_count != stg_counts.row_count
