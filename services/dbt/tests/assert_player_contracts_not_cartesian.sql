-- A contract grain must never match more than one NBA player_id (anti-cartesian).
with player_contracts as (
    select * from {{ ref('fct_player_contracts') }}
),

exploded as (
    select
        player_contracts.bref_player_slug,
        player_contracts.bref_team_abbreviation,
        player_contracts.season,
        count(distinct player_contracts.player_id) as matched_player_ids
    from player_contracts
    where player_contracts.player_id is not null
    group by
        player_contracts.bref_player_slug,
        player_contracts.bref_team_abbreviation,
        player_contracts.season
)

select
    exploded.bref_player_slug,
    exploded.bref_team_abbreviation,
    exploded.season,
    exploded.matched_player_ids
from exploded
where exploded.matched_player_ids > 1
