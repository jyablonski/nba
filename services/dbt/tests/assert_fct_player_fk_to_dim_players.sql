-- Every fact player_id must exist on dim_players (no orphan FKs).
with player_game_logs as (
    select * from {{ ref('fct_player_game_logs') }}
),

players as (
    select * from {{ ref('dim_players') }}
)

select player_game_logs.player_id
from player_game_logs
left join players
    on player_game_logs.player_id = players.player_id
where players.player_id is null
