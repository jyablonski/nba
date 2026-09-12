with source as (
    select * from {{ source('source', 'transaction_participants') }}
)

select
    source.transaction_key,
    source.participant_type,
    source.direction,
    source.bref_slug,
    source.display_name,
    source.player_id,
    source.team_id,
    source.scraped_at
from source
