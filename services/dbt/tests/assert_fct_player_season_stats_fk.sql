-- Every season-stats player_id must exist on dim_players (no orphan FKs).
with player_season_stats as (
    select * from {{ ref('fct_player_season_stats') }}
),

players as (
    select * from {{ ref('dim_players') }}
)

select player_season_stats.player_id
from player_season_stats
left join players
    on player_season_stats.player_id = players.player_id
where players.player_id is null
