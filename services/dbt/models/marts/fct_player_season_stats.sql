with player_game_logs as (
    select * from {{ ref('int_player_game_logs_enriched') }}
)

select
    player_game_logs.player_id,
    player_game_logs.season,
    count(*) as games_played,
    min(player_game_logs.game_date) as first_game_date,
    max(player_game_logs.game_date) as last_game_date,
    round(avg(player_game_logs.points)::numeric, 1) as ppg,
    round(avg(player_game_logs.rebounds)::numeric, 1) as rpg,
    round(avg(player_game_logs.assists)::numeric, 1) as apg
from player_game_logs
group by player_game_logs.player_id, player_game_logs.season
