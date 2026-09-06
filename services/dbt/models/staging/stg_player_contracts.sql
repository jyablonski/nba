with source as (
    select * from {{ source('source', 'player_contracts') }}
)

select
    source.bref_player_slug,
    source.player_name,
    source.player_name_normalized,
    source.bref_team_abbreviation,
    source.nba_team_abbreviation,
    source.season,
    source.salary,
    source.is_fully_guaranteed,
    source.remaining_guaranteed,
    source.player_age,
    source.source_url
from source
