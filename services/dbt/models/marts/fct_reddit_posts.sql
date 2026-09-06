with posts as (
    select * from {{ ref('stg_reddit_posts') }}
)

select
    posts.reddit_id,
    posts.subreddit,
    posts.title,
    posts.author,
    posts.score,
    posts.num_comments,
    posts.created_utc,
    posts.permalink,
    posts.url,
    posts.selftext,
    posts.flair,
    posts.is_self,
    posts.scraped_at
from posts
