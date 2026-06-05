-- One row per artist. Universe = every artist seen in plays (primary artists)
-- OR enriched via Last.fm tags (featured/album artists), so the bridge and
-- fact tables never reference an artist that's missing here.
with from_plays as (

    select distinct artist_id, artist_name
    from {{ ref('stg_plays') }}
    where artist_id is not null

),

from_tags as (

    select distinct artist_id, artist_name
    from {{ ref('stg_artist_tags') }}
    where artist_id is not null

),

unioned as (

    select artist_id, artist_name from from_plays
    union
    select artist_id, artist_name from from_tags

),

artists as (

    select
        artist_id,
        max(artist_name) as artist_name
    from unioned
    group by artist_id

),

primary_genre as (

    select artist_id, genre as primary_genre
    from {{ ref('int_artist_genres') }}
    where genre_rank = 1

)

select
    md5(a.artist_id) as artist_key,
    a.artist_id,
    a.artist_name,
    g.primary_genre
from artists a
left join primary_genre g on a.artist_id = g.artist_id
