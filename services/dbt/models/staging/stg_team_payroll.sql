with source as (
    select * from {{ source('source', 'team_payroll') }}
)

select
    source.bref_team_abbreviation,
    source.nba_team_abbreviation,
    source.season,
    source.total_salary,
    source.remaining_guaranteed,
    source.source_url
from source
