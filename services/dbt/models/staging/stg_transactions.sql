with source as (
    select * from {{ source('source', 'transactions') }}
)

select
    source.transaction_key,
    source.transaction_date,
    source.season,
    source.description,
    source.source_url,
    source.scraped_at
from source
