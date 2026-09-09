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
    events.team_id,
    events.player_id,
    events.secondary_player_id,
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
    events.description
from events
