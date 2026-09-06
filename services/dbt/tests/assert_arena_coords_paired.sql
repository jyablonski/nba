-- Latitude and longitude must both be present or both be null.
with dim_teams as (
    select * from {{ ref('dim_teams') }}
)

select dim_teams.team_id
from dim_teams
where (dim_teams.arena_latitude is null) <> (dim_teams.arena_longitude is null)
