-- A seeded conference must be a complete 1-10 bracket: ten teams, ten distinct
-- seeds. A partial set would mean play-in games were mis-classified.
with playoff_seeds as (
    select * from {{ ref('int_playoff_seeds') }}
)

select
    playoff_seeds.season,
    playoff_seeds.conference,
    count(*) as seeded_teams,
    count(distinct playoff_seeds.playoff_seed) as distinct_seeds
from playoff_seeds
group by playoff_seeds.season, playoff_seeds.conference
having count(*) <> 10 or count(distinct playoff_seeds.playoff_seed) <> 10
