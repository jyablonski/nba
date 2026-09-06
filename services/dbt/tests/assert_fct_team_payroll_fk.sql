-- Payroll team_id must exist on dim_teams.
with payroll as (
    select * from {{ ref('fct_team_payroll') }}
),

teams as (
    select * from {{ ref('dim_teams') }}
)

select payroll.team_id
from payroll
left join teams
    on payroll.team_id = teams.team_id
where teams.team_id is null
