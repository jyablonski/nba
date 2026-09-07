with duplicate_grains as (
    select
        player_id,
        team_id,
        season,
        count(*) as row_count
    from {{ ref('fct_player_contracts') }}
    group by player_id, team_id, season
)

select *
from duplicate_grains
where row_count > 1
