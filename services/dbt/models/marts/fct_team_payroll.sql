with payroll as (
    select * from {{ ref('stg_team_payroll') }}
),

teams as (
    select * from {{ ref('stg_teams') }}
),

player_contracts as (
    select * from {{ ref('int_player_contracts_matched') }}
),

player_counts as (
    select
        player_contracts.nba_team_abbreviation,
        player_contracts.season,
        count(*) as player_season_count,
        count(player_contracts.player_id) as matched_player_count
    from player_contracts
    group by
        player_contracts.nba_team_abbreviation,
        player_contracts.season
),

cba_caps as (
    select * from {{ ref('nba_cba_caps') }}
)

select
    teams.team_id,
    payroll.bref_team_abbreviation,
    payroll.nba_team_abbreviation,
    teams.team_name,
    payroll.season,
    payroll.total_salary,
    payroll.remaining_guaranteed,
    coalesce(player_counts.player_season_count, 0) as player_season_count,
    coalesce(player_counts.matched_player_count, 0) as matched_player_count,
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
inner join teams
    on payroll.nba_team_abbreviation = teams.abbreviation
left join player_counts
    on
        payroll.nba_team_abbreviation = player_counts.nba_team_abbreviation
        and payroll.season = player_counts.season
left join cba_caps
    on payroll.season = cba_caps.season
