with matched as (
    select * from {{ ref('int_transactions_matched') }}
),

transactions as (
    select * from {{ ref('stg_transactions') }}
)

select
    matched.transaction_key,
    transactions.transaction_date,
    transactions.season,
    matched.participant_type,
    matched.direction,
    matched.bref_slug,
    matched.display_name,
    matched.player_id,
    matched.team_id,
    matched.team_abbreviation,
    matched.player_name,
    matched.match_method,
    matched.scraped_at
from matched
inner join transactions
    on matched.transaction_key = transactions.transaction_key
