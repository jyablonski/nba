with source as (
    select * from {{ source('source', 'reddit_posts') }}
)

select
    source.reddit_id,
    source.subreddit,
    source.title,
    source.author,
    source.score,
    source.num_comments,
    source.created_utc,
    source.permalink,
    source.url,
    source.selftext,
    source.flair,
    source.is_self,
    source.scraped_at
from source
