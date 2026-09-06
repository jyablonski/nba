with predictions as (
    select * from {{ ref('stg_game_predictions') }}
),

games as (
    select * from {{ ref('stg_games_schedule') }}
)

select
    predictions.game_id,
    predictions.as_of,
    predictions.model_name,
    predictions.model_version,
    predictions.home_team_id,
    predictions.away_team_id,
    predictions.model_wp,
    predictions.market_wp,
    games.game_date,
    games.season,
    games.season_type,
    games.status as game_status,
    predictions.scraped_at
from predictions
inner join games
    on predictions.game_id = games.game_id
