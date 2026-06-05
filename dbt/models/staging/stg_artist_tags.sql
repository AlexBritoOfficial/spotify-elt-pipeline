-- Unnest the Last.fm toptags array: one row per (artist, tag).
with source as (

    select
        artist_id,
        artist_name,
        payload
    from {{ source('raw', 'artist_tags') }}

),

unnested as (

    select
        s.artist_id,
        s.artist_name,
        tag ->> 'name'         as tag_name,
        (tag ->> 'count')::int as tag_count
    from source s,
         lateral jsonb_array_elements(
             -- guard against artists whose Last.fm response had no tags
             coalesce(s.payload -> 'toptags' -> 'tag', '[]'::jsonb)
         ) as tag

)

select * from unnested
