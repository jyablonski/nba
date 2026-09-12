with transactions as (
    select * from {{ ref('stg_transactions') }}
),

matched as (
    select * from {{ ref('int_transactions_matched') }}
),

participant_rollup as (
    select
        matched.transaction_key,
        count(*) filter (where matched.participant_type = 'team') as team_count,
        count(*) filter (where matched.participant_type = 'player') as player_count,
        count(*) filter (where matched.match_method = 'unmatched') as unmatched_count
    from matched
    group by matched.transaction_key
)

select
    transactions.transaction_key,
    transactions.transaction_date,
    transactions.season,
    transactions.description,
    transactions.source_url,
    transactions.scraped_at,
    -- Counts make "was this a trade" answerable without re-parsing prose: a
    -- signing has one team, a trade has two or more.
    coalesce(participant_rollup.team_count, 0) as team_count,
    coalesce(participant_rollup.player_count, 0) as player_count,
    coalesce(participant_rollup.unmatched_count, 0) as unmatched_count
from transactions
left join participant_rollup
    on transactions.transaction_key = participant_rollup.transaction_key
