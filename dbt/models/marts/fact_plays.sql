-- Fact table. Grain: one row per play event (a single listen).
with plays as (

    select * from {{ ref('stg_plays') }}

)

select
    md5(played_at::text) as play_key,
    md5(track_id)        as track_key,    -- FK -> dim_track
    md5(artist_id)       as artist_key,   -- FK -> dim_artist
    played_at,
    played_at::date      as played_date,
    duration_ms,
    context_type,
    1                    as play_count    -- additive measure
from plays
where track_id is not null
