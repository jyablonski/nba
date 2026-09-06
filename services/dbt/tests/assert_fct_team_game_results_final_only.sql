-- Completed-game fact must stay Final-only even after schedule ingest.
with results as (
    select * from {{ ref('fct_team_game_results') }}
),

schedule as (
    select * from {{ ref('stg_games_schedule') }}
),

non_final as (
    select count(*) as row_count
    from results
    inner join schedule
        on results.game_id = schedule.game_id
    where schedule.status != 'Final'
)

select 1 as failure
from non_final
where non_final.row_count > 0
