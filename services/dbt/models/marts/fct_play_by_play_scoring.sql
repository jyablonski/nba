with scoring as (
    select * from {{ ref('int_play_by_play_scoring') }}
)

select
    scoring.game_id,
    scoring.season,
    scoring.action_number,
    scoring.period,
    scoring.clock,
    scoring.clock_remaining_seconds,
    scoring.elapsed_seconds,
    scoring.score_home,
    scoring.score_away,
    scoring.score_differential,
    scoring.home_points,
    scoring.away_points,
    scoring.points_scored,
    scoring.scoring_side,
    scoring.team_id,
    scoring.player_id,
    scoring.action_type,
    scoring.sub_type,
    scoring.description
from scoring
