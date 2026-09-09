with standings as (
    select * from {{ ref('stg_standings') }}
),

teams as (
    select * from {{ ref('stg_teams') }}
),

playoff_seeds as (
    select * from {{ ref('int_playoff_seeds') }}
)

select
    standings.team_id,
    teams.abbreviation,
    teams.team_name,
    teams.city,
    teams.nickname,
    standings.season,
    standings.season_type,
    standings.as_of_date,
    standings.conference,
    standings.division,
    standings.conference_rank,
    standings.division_rank,
    standings.wins,
    standings.losses,
    standings.win_pct,
    standings.games_back,
    standings.conf_games_back,
    standings.streak,
    standings.last_10,
    playoff_seeds.playoff_seed
from standings
inner join teams
    on standings.team_id = teams.team_id
left join playoff_seeds
    on standings.team_id = playoff_seeds.team_id
    and standings.season = playoff_seeds.season
