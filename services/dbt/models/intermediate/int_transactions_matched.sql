-- Participants joined to the canonical dimensions. The scraper already resolved
-- ids from href slugs, so this stamps how confident that link is rather than
-- attempting any name matching of its own.
with participants as (
    select * from {{ ref('stg_transaction_participants') }}
),

teams as (
    select * from {{ ref('stg_teams') }}
),

players as (
    select * from {{ ref('stg_players') }}
)

select
    participants.transaction_key,
    participants.participant_type,
    participants.direction,
    participants.bref_slug,
    participants.display_name,
    participants.player_id,
    participants.team_id,
    participants.scraped_at,
    teams.abbreviation as team_abbreviation,
    players.full_name as player_name,
    case
        when participants.participant_type = 'team' and teams.team_id is not null
            then 'external_id'
        when participants.participant_type = 'player' and players.player_id is not null
            then 'external_id'
        else 'unmatched'
    end as match_method
from participants
left join teams
    on participants.team_id = teams.team_id
left join players
    on participants.player_id = players.player_id
