with comments as (
    select * from {{ ref('stg_reddit_comments') }}
)

select
    comments.reddit_id,
    comments.post_reddit_id,
    comments.parent_id,
    comments.author,
    comments.body,
    comments.score,
    comments.created_utc,
    comments.permalink,
    comments.scraped_at
from comments
