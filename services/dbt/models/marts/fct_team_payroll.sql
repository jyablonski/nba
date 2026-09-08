with payroll as (
    select * from {{ ref('stg_team_payroll') }}
),

cba_caps as (
    select * from {{ ref('nba_cba_caps') }}
)

select
    payroll.team_id,
    teams.abbreviation,
    teams.team_name,
    payroll.season,
    payroll.total_salary,
    payroll.remaining_guaranteed,
    cba_caps.salary_cap,
    cba_caps.luxury_tax,
    cba_caps.first_apron,
    cba_caps.second_apron,
    case
        when payroll.total_salary is null or cba_caps.luxury_tax is null then null
        else payroll.total_salary > cba_caps.luxury_tax
    end as over_luxury_tax,
    case
        when payroll.total_salary is null or cba_caps.first_apron is null then null
        else payroll.total_salary > cba_caps.first_apron
    end as over_first_apron,
    case
        when payroll.total_salary is null or cba_caps.second_apron is null then null
        else payroll.total_salary > cba_caps.second_apron
    end as over_second_apron
from payroll
left join cba_caps
    on payroll.season = cba_caps.season
left join {{ ref('stg_teams') }} as teams
    on payroll.team_id = teams.team_id
