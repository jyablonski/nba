with post_flairs as (
    select posts.author_flair from {{ ref('stg_reddit_posts') }} as posts
),

comment_flairs as (
    select comments.author_flair from {{ ref('stg_reddit_comments') }} as comments
),

all_flairs as (
    select * from post_flairs
    union all
    select * from comment_flairs
),

-- Grain is the distinct raw string, not the row: a few hundred values cover
-- every post and comment, so each one is resolved once and joined back.
distinct_flairs as (
    select distinct all_flairs.author_flair
    from all_flairs
    where all_flairs.author_flair is not null
        and btrim(all_flairs.author_flair) <> ''
),

-- team_id comes from the dimension, not the seed: the seed carries the
-- abbreviation and dim_teams stays the single source of the id.
codes as (
    select
        flair_codes.flair_code,
        flair_codes.scope,
        code_teams.team_id
    from {{ ref('nba_reddit_flair_codes') }} as flair_codes
    left join {{ ref('dim_teams') }} as code_teams
        on code_teams.abbreviation = flair_codes.abbreviation
),

teams as (
    select * from {{ ref('dim_teams') }}
),

-- ":lal-1: Lakers" -> raw_code "lal-1", label "Lakers".
parsed as (
    select
        distinct_flairs.author_flair,
        substring(btrim(distinct_flairs.author_flair) from '^:([a-zA-Z0-9_-]+):') as raw_code,
        btrim(
            coalesce(
                substring(btrim(distinct_flairs.author_flair) from '^:[a-zA-Z0-9_-]+:\s*(.*)$'),
                btrim(distinct_flairs.author_flair)
            )
        ) as label
    from distinct_flairs
),

-- A numeric variant is what makes a code an r/nba team badge. Without it the
-- code is a national-team or bandwagon flair, so ":phi:" is Philippines while
-- ":phi-5:" is the 76ers.
keyed as (
    select
        parsed.author_flair,
        parsed.raw_code,
        parsed.label,
        parsed.raw_code ~ '-[0-9]+$' as has_variant,
        lower(regexp_replace(coalesce(parsed.raw_code, ''), '-[0-9]+$', '')) as base_code,
        -- "[SAS] Tim Duncan" -> SAS, the fallback for flairs with no emoji code.
        upper(
            coalesce(substring(parsed.label from '^\[([A-Za-z]{2,3})\]'), '')
        ) as bracket_abbreviation
    from parsed
),

resolved as (
    select
        keyed.author_flair,
        keyed.label,
        case
            when keyed.has_variant and codes.flair_code is not null then 'emoji_code'
            when keyed.raw_code is not null then 'uncoded_emoji'
            when bracket_teams.team_id is not null then 'bracket_abbreviation'
            when label_teams.team_id is not null then 'label'
            when lower(keyed.label) in ('nba', 'r/nba') then 'label'
            else 'unmatched'
        end as match_method,
        case
            when keyed.has_variant and codes.flair_code is not null then codes.scope
            when keyed.raw_code is not null then 'other'
            when bracket_teams.team_id is not null then 'team'
            when label_teams.team_id is not null then 'team'
            when lower(keyed.label) in ('nba', 'r/nba') then 'league'
            else 'other'
        end as flair_scope,
        case
            when keyed.has_variant and codes.flair_code is not null then codes.team_id
            when keyed.raw_code is not null then null
            when bracket_teams.team_id is not null then bracket_teams.team_id
            else label_teams.team_id
        end as flair_team_id
    from keyed
    left join codes
        on codes.flair_code = keyed.base_code
       and keyed.has_variant
    left join teams as bracket_teams
        on bracket_teams.abbreviation = keyed.bracket_abbreviation
       and keyed.raw_code is null
    left join teams as label_teams
        on {{ normalize_player_name('label_teams.nickname') }}
            = {{ normalize_player_name('keyed.label') }}
       and keyed.raw_code is null
)

select
    resolved.author_flair,
    resolved.label as flair_label,
    resolved.flair_scope,
    resolved.match_method as flair_match_method,
    resolved.flair_team_id,
    teams.abbreviation as flair_team_abbreviation,
    teams.team_name as flair_team_name
from resolved
left join teams
    on teams.team_id = resolved.flair_team_id
