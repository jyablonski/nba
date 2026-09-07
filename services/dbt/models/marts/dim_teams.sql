with teams as (
    select * from {{ ref('stg_teams') }}
),

current_arenas as (
    select * from {{ ref('nba_team_arenas') }}
),

team_colors as (
    select * from {{ ref('nba_team_colors') }}
),

payroll as (
    select * from {{ ref('stg_team_payroll') }}
),

cba_caps as (
    select * from {{ ref('nba_cba_caps') }}
),

current_payroll_season as (
    select min(payroll.season) as season
    from payroll
),

current_team_payroll as (
    select
        teams.team_id,
        payroll.season as current_contract_season,
        payroll.total_salary as current_season_payroll,
        payroll.remaining_guaranteed as current_remaining_guaranteed,
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
    inner join current_payroll_season
        on payroll.season = current_payroll_season.season
    inner join teams
        on payroll.team_id = teams.team_id
    left join cba_caps
        on payroll.season = cba_caps.season
)

select
    teams.team_id,
    teams.abbreviation,
    teams.team_name,
    teams.city,
    teams.nickname,
    teams.conference,
    teams.division,
    current_arenas.arena_name,
    current_arenas.arena_latitude,
    current_arenas.arena_longitude,
    team_colors.primary_color,
    team_colors.alternate_color,
    current_team_payroll.current_contract_season,
    current_team_payroll.current_season_payroll,
    current_team_payroll.current_remaining_guaranteed,
    current_team_payroll.salary_cap,
    current_team_payroll.luxury_tax,
    current_team_payroll.first_apron,
    current_team_payroll.second_apron,
    current_team_payroll.over_luxury_tax,
    current_team_payroll.over_first_apron,
    current_team_payroll.over_second_apron
from teams
left join current_arenas
    on teams.team_id = current_arenas.team_id
left join team_colors
    on teams.team_id = team_colors.team_id
left join current_team_payroll
    on teams.team_id = current_team_payroll.team_id
