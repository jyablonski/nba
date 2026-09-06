with source as (
    select * from {{ source('source', 'player_injuries') }}
)

select
    source.player_name,
    source.player_name_normalized,
    source.bref_player_slug,
    source.bref_team_abbreviation,
    source.nba_team_abbreviation,
    source.update_date,
    source.description,
    source.source_url,
    source.scraped_at
from source
