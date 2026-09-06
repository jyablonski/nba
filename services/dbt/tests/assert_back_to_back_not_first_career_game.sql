-- Back-to-back rows must not be a player's first career game in the dataset.
with player_game_logs as (
    select * from {{ ref('fct_player_game_logs') }}
)

select
    player_game_logs.player_id,
    player_game_logs.game_id,
    player_game_logs.career_game_number
from player_game_logs
where
    player_game_logs.is_back_to_back is true
    and player_game_logs.career_game_number = 1
