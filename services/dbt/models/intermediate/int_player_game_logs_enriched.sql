with game_logs as (
    select * from {{ ref('stg_player_game_logs') }}
),

with_prev_game as (
    select
        game_logs.*,
        lag(game_logs.game_date) over (
            partition by game_logs.player_id, game_logs.season
            order by game_logs.game_date
        ) as prev_game_date,
        lag(game_logs.game_date) over (
            partition by game_logs.player_id
            order by game_logs.game_date
        ) as prev_game_date_career
    from game_logs
)

select
    with_prev_game.*,
    coalesce(with_prev_game.game_date - with_prev_game.prev_game_date_career = 1, false) as is_back_to_back,
    row_number() over (
        partition by with_prev_game.player_id, with_prev_game.season
        order by with_prev_game.game_date
    ) as season_game_number,
    row_number() over (
        partition by with_prev_game.player_id
        order by with_prev_game.game_date
    ) as career_game_number
from with_prev_game
