with source as (
    select * from {{ source('source', 'teams') }}
)

select
    team_id,
    abbreviation,
    full_name as team_name,
    city,
    nickname,
    conference,
    division
from source
