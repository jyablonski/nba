-- A blown lead must belong to the losing team and be covered by that team's max
-- lead, and the comeback / blown-lead labels only exist when someone actually
-- coughed up a lead.
with game_flow as (
    select * from {{ ref('fct_game_flow') }}
)

select
    game_flow.game_id,
    game_flow.largest_lead_blown,
    game_flow.max_home_lead,
    game_flow.max_away_lead
from game_flow
where
    game_flow.largest_lead_blown > case
        when game_flow.winning_team_id = game_flow.home_team_id then game_flow.max_away_lead
        else game_flow.max_home_lead
    end
    or (game_flow.largest_lead_blown = 0 and game_flow.blown_lead_team_abbreviation is not null)
    or (game_flow.largest_lead_blown > 0 and game_flow.comeback_team_abbreviation is null)
    or (
        game_flow.comeback_team_abbreviation is not null
        and game_flow.comeback_team_abbreviation
        is distinct from game_flow.winning_team_abbreviation
    )
