with source as (
    select * from {{ source('source', 'game_odds') }}
)

select
    source.odds_event_id,
    source.commence_time,
    source.home_team_name,
    source.away_team_name,
    source.game_id,
    source.bookmaker,
    source.market,
    source.home_price,
    source.away_price,
    source.home_implied_wp,
    source.away_implied_wp,
    source.home_market_wp,
    source.away_market_wp,
    source.spread_home,
    source.scraped_at
from source
