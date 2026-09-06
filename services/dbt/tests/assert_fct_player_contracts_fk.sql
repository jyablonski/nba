-- Matched contract player_ids must exist on dim_players (no orphan FKs).
with player_contracts as (
    select * from {{ ref('fct_player_contracts') }}
),

players as (
    select * from {{ ref('dim_players') }}
)

select player_contracts.player_id
from player_contracts
left join players
    on player_contracts.player_id = players.player_id
where
    player_contracts.player_id is not null
    and players.player_id is null
