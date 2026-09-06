-- Match BRef remaining-contract rows to NBA person_ids without a cartesian join.
-- 1) unique_name: exactly one stg_players row shares the normalized name
-- 2) name_and_team: name is ambiguous, but exactly one player has that name on the
--    mapped NBA team (requires source.players.team_id, usually from --enrich)
-- Otherwise match_method = unmatched and player_id is null.
with players as (
    select * from {{ ref('stg_players') }}
),

teams as (
    select * from {{ ref('stg_teams') }}
),

contracts as (
    select * from {{ ref('stg_player_contracts') }}
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
        contracts.bref_player_slug,
        contracts.bref_team_abbreviation,
        contracts.season,
        players_normalized.player_id,
        'unique_name' as match_method
    from contracts
    inner join players_normalized
        on contracts.player_name_normalized = players_normalized.player_name_normalized
    inner join name_counts
        on players_normalized.player_name_normalized = name_counts.player_name_normalized
    where name_counts.player_count = 1
),

name_and_team_matches as (
    select
        contracts.bref_player_slug,
        contracts.bref_team_abbreviation,
        contracts.season,
        players_normalized.player_id,
        'name_and_team' as match_method
    from contracts
    inner join teams
        on contracts.nba_team_abbreviation = teams.abbreviation
    inner join players_normalized
        on
            contracts.player_name_normalized = players_normalized.player_name_normalized
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
        all_matches.bref_player_slug,
        all_matches.bref_team_abbreviation,
        all_matches.season,
        all_matches.player_id,
        all_matches.match_method,
        row_number() over (
            partition by
                all_matches.bref_player_slug,
                all_matches.bref_team_abbreviation,
                all_matches.season
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
        ranked_matches.bref_player_slug,
        ranked_matches.bref_team_abbreviation,
        ranked_matches.season,
        ranked_matches.player_id,
        ranked_matches.match_method
    from ranked_matches
    where ranked_matches.match_rank = 1
)

select
    contracts.bref_player_slug,
    contracts.player_name,
    contracts.player_name_normalized,
    contracts.bref_team_abbreviation,
    contracts.nba_team_abbreviation,
    contracts.season,
    contracts.salary,
    contracts.is_fully_guaranteed,
    contracts.remaining_guaranteed,
    contracts.player_age,
    contracts.source_url,
    teams.team_id,
    best_matches.player_id,
    coalesce(best_matches.match_method, 'unmatched') as match_method
from contracts
left join best_matches
    on
        contracts.bref_player_slug = best_matches.bref_player_slug
        and contracts.bref_team_abbreviation = best_matches.bref_team_abbreviation
        and contracts.season = best_matches.season
left join teams
    on contracts.nba_team_abbreviation = teams.abbreviation
