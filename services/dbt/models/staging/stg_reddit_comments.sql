with source as (
    select * from {{ source('source', 'reddit_comments') }}
)

select
    source.reddit_id,
    source.post_reddit_id,
    source.parent_id,
    source.author,
    source.body,
    source.score,
    source.created_utc,
    source.permalink,
    source.scraped_at
from source
