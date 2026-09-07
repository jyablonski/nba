with source as (
    select * from {{ source('source', 'team_payroll') }}
)

select
    source.team_id,
    source.season,
    source.total_salary,
    source.remaining_guaranteed,
    source.source_url
from source
