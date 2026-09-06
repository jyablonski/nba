with actions as (
    select * from {{ ref('stg_play_by_play') }}
)

select
    actions.game_id,
    actions.season,
    actions.action_number,
    actions.action_id,
    actions.period,
    actions.clock,
    actions.score_home,
    actions.score_away,
    actions.team_id,
    actions.player_id,
    actions.action_type,
    actions.sub_type,
    actions.description,
    actions.scraped_at
from actions
