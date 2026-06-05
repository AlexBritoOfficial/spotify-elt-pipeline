-- One row per track. A track can appear in many plays, so collapse to the
-- track grain and carry its album + primary-artist attributes.
with tracks as (

    select
        track_id,
        max(track_name)         as track_name,
        max(artist_id)          as artist_id,
        max(album_id)           as album_id,
        max(album_name)         as album_name,
        max(album_type)         as album_type,
        max(album_release_date) as album_release_date,
        max(album_total_tracks) as album_total_tracks,
        max(duration_ms)        as duration_ms,
        bool_or(is_explicit)    as is_explicit,
        max(track_number)       as track_number,
        max(disc_number)        as disc_number
    from {{ ref('stg_plays') }}
    where track_id is not null
    group by track_id

)

select
    md5(track_id)  as track_key,
    md5(artist_id) as artist_key,   -- FK -> dim_artist
    track_id,
    track_name,
    artist_id,
    album_id,
    album_name,
    album_type,
    album_release_date,
    album_total_tracks,
    duration_ms,
    is_explicit,
    track_number,
    disc_number
from tracks
