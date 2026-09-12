with posts as (
    select * from {{ ref('stg_reddit_posts') }}
),

comments as (
    select * from {{ ref('stg_reddit_comments') }}
),

post_documents as (
    select
        'post' as document_type,
        posts.reddit_id as document_reddit_id,
        posts.reddit_id as post_reddit_id,
        posts.created_utc,
        concat_ws(' ', posts.title, posts.selftext) as raw_text
    from posts
),

comment_documents as (
    select
        'comment' as document_type,
        comments.reddit_id as document_reddit_id,
        comments.post_reddit_id,
        comments.created_utc,
        comments.body as raw_text
    from comments
    where
        comments.body is not null
        and comments.body not in ('[removed]', '[deleted]')
),

documents as (
    select * from post_documents
    union all
    select * from comment_documents
)

select
    documents.document_type,
    documents.document_reddit_id,
    documents.post_reddit_id,
    documents.created_utc,
    -- Padded with a leading and trailing space so a whole-token match in
    -- fct_reddit_entity_mentions is a plain substring test: ' celtics ' cannot
    -- match inside "celticsfan". normalize_player_name is reused on free text on
    -- purpose — the needle and the haystack have to be normalized identically, or
    -- "Michael Porter Jr." in a title never matches the dimension's suffix-stripped
    -- name.
    concat(' ', {{ normalize_player_name('documents.raw_text') }}, ' ') as search_text
from documents
