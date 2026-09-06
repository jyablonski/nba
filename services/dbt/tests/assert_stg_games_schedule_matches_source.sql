-- Schedule staging must keep every source.games row, including non-Final.
with source_counts as (
    select count(*) as row_count
    from {{ source('source', 'games') }}
),

stg_counts as (
    select count(*) as row_count from {{ ref('stg_games_schedule') }}
)

select 1 as failure
from source_counts
cross join stg_counts
where source_counts.row_count != stg_counts.row_count
