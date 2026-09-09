-- One wide gold fact per Basketball-Reference action: the raw action columns
-- plus the typed event detail parsed in int_play_by_play_events. Previously
-- two marts over the identical 632k-row grain (fct_play_by_play kept the raw
-- text, fct_play_by_play_events the parsed columns); the split cost a full
-- duplicate table and left the parsed events unreachable from Cube.
with events as (
    select * from {{ ref('int_play_by_play_events') }}
)

select
    events.game_id,
    events.season,
    events.action_number,
    events.action_id,
    events.period,
    events.clock,
    events.score_home,
    events.score_away,
    events.team_id,
    events.player_id,
    events.secondary_player_id,
    events.action_type,
    events.sub_type,
    events.event_type,
    events.shot_value,
    events.shot_type,
    events.shot_distance_ft,
    events.is_assisted,
    events.is_blocked,
    events.is_stolen,
    events.free_throw_kind,
    events.free_throw_number,
    events.free_throw_of,
    events.rebound_side,
    events.is_team_rebound,
    events.turnover_kind,
    events.foul_kind,
    events.flagrant_degree,
    events.violation_kind,
    events.timeout_kind,
    events.replay_kind,
    events.replay_outcome,
    events.description,
    events.scraped_at
from events
