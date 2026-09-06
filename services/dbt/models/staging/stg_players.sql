with source as (
    select * from {{ source('source', 'players') }}
)

select
    player_id,
    first_name,
    last_name,
    full_name,
    is_active,
    jersey_number,
    position,
    height,
    weight,
    birth_date,
    team_id,
    from_year,
    to_year
from source
