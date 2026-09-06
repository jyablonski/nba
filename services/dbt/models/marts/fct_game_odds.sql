with odds as (
    select * from {{ ref('stg_game_odds') }}
)

select
    odds.odds_event_id,
    odds.commence_time,
    odds.home_team_name,
    odds.away_team_name,
    odds.game_id,
    odds.bookmaker,
    odds.market,
    odds.home_price,
    odds.away_price,
    odds.home_implied_wp,
    odds.away_implied_wp,
    odds.home_market_wp,
    odds.away_market_wp,
    odds.spread_home,
    odds.scraped_at
from odds
