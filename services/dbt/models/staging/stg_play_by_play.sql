with source as (
    select * from {{ source('source', 'play_by_play') }}
)

select
    source.game_id,
    source.season,
    source.action_number,
    source.action_id,
    source.period,
    source.clock,
    source.score_home,
    source.score_away,
    source.team_id,
    source.player_id,
    source.action_type,
    source.sub_type,
    source.description,
    source.scraped_at
from source
