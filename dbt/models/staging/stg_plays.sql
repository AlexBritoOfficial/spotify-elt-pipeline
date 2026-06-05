-- Flatten raw.plays JSONB into one tidy row per play event.
with source as (

    select
        played_at,
        ingested_at,
        payload
    from {{ source('raw', 'plays') }}

),

flattened as (

    select
        -- a play event's natural key: you can't play two tracks at once
        played_at,
        ingested_at,

        -- track
        payload -> 'track' ->> 'id'                             as track_id,
        payload -> 'track' ->> 'name'                           as track_name,
        (payload -> 'track' ->> 'duration_ms')::int             as duration_ms,
        (payload -> 'track' ->> 'explicit')::boolean            as is_explicit,
        (payload -> 'track' ->> 'track_number')::int            as track_number,
        (payload -> 'track' ->> 'disc_number')::int             as disc_number,

        -- album
        payload -> 'track' -> 'album' ->> 'id'                  as album_id,
        payload -> 'track' -> 'album' ->> 'name'                as album_name,
        payload -> 'track' -> 'album' ->> 'album_type'          as album_type,
        payload -> 'track' -> 'album' ->> 'release_date'        as album_release_date,
        (payload -> 'track' -> 'album' ->> 'total_tracks')::int as album_total_tracks,

        -- primary artist (first entry in the artists array)
        payload -> 'track' -> 'artists' -> 0 ->> 'id'           as artist_id,
        payload -> 'track' -> 'artists' -> 0 ->> 'name'         as artist_name,

        -- listening context (playlist / album / artist radio / etc.)
        payload -> 'context' ->> 'type'                         as context_type,
        payload -> 'context' ->> 'uri'                          as context_uri
    from source

)

select * from flattened
