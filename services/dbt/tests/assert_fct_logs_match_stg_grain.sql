-- Fact player game logs must preserve staging grain (one row per player/game).
with stg_counts as (
    select count(*) as row_count from {{ ref('stg_player_game_logs') }}
),

fct_counts as (
    select count(*) as row_count from {{ ref('fct_player_game_logs') }}
)

select 1 as failure
from stg_counts
cross join fct_counts
where stg_counts.row_count != fct_counts.row_count
