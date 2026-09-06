-- Match current BRef injury rows to NBA person_ids without a cartesian join.
-- Same two-step rule as contracts: unique normalized name, else name + team.
with players as (
    select * from {{ ref('stg_players') }}
),

teams as (
    select * from {{ ref('stg_teams') }}
),

injuries as (
    select * from {{ ref('stg_player_injuries') }}
),

players_normalized as (
    select
        players.player_id,
        players.team_id,
        players.full_name,
        {{ normalize_player_name('players.full_name') }} as player_name_normalized
    from players
),

name_counts as (
    select
        players_normalized.player_name_normalized,
        count(*) as player_count
    from players_normalized
    group by players_normalized.player_name_normalized
),

name_team_counts as (
    select
        players_normalized.player_name_normalized,
        players_normalized.team_id,
        count(*) as player_count
    from players_normalized
    where players_normalized.team_id is not null
    group by
        players_normalized.player_name_normalized,
        players_normalized.team_id
),

unique_name_matches as (
    select
        injuries.player_name_normalized,
        injuries.bref_team_abbreviation,
        players_normalized.player_id,
        'unique_name' as match_method
    from injuries
    inner join players_normalized
        on injuries.player_name_normalized = players_normalized.player_name_normalized
    inner join name_counts
        on players_normalized.player_name_normalized = name_counts.player_name_normalized
    where name_counts.player_count = 1
),

name_and_team_matches as (
    select
        injuries.player_name_normalized,
        injuries.bref_team_abbreviation,
        players_normalized.player_id,
        'name_and_team' as match_method
    from injuries
    inner join teams
        on injuries.nba_team_abbreviation = teams.abbreviation
    inner join players_normalized
        on
            injuries.player_name_normalized = players_normalized.player_name_normalized
            and teams.team_id = players_normalized.team_id
    inner join name_team_counts
        on
            players_normalized.player_name_normalized = name_team_counts.player_name_normalized
            and players_normalized.team_id = name_team_counts.team_id
    where name_team_counts.player_count = 1
),

all_matches as (
    select * from unique_name_matches
    union all
    select * from name_and_team_matches
),

ranked_matches as (
    select
        all_matches.player_name_normalized,
        all_matches.bref_team_abbreviation,
        all_matches.player_id,
        all_matches.match_method,
        row_number() over (
            partition by
                all_matches.player_name_normalized,
                all_matches.bref_team_abbreviation
            order by
                case all_matches.match_method
                    when 'unique_name' then 1
                    else 2
                end
        ) as match_rank
    from all_matches
),

best_matches as (
    select
        ranked_matches.player_name_normalized,
        ranked_matches.bref_team_abbreviation,
        ranked_matches.player_id,
        ranked_matches.match_method
    from ranked_matches
    where ranked_matches.match_rank = 1
)

select
    injuries.player_name,
    injuries.player_name_normalized,
    injuries.bref_player_slug,
    injuries.bref_team_abbreviation,
    injuries.nba_team_abbreviation,
    injuries.update_date,
    injuries.description,
    injuries.source_url,
    injuries.scraped_at,
    teams.team_id,
    best_matches.player_id,
    coalesce(best_matches.match_method, 'unmatched') as match_method
from injuries
left join best_matches
    on
        injuries.player_name_normalized = best_matches.player_name_normalized
        and injuries.bref_team_abbreviation = best_matches.bref_team_abbreviation
left join teams
    on injuries.nba_team_abbreviation = teams.abbreviation
