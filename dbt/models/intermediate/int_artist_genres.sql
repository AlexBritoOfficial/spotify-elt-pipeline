-- Turn messy Last.fm folksonomy tags into clean, ranked genres per artist.
--
-- Pipeline: normalize case/punctuation -> collapse duplicates -> drop
-- non-genre noise (denylist seed, the artist's own name, decade/number tags)
-- -> keep the top-N by tag count.
with tags as (

    select * from {{ ref('stg_artist_tags') }}

),

denylist as (

    select tag_name from {{ ref('non_genre_tags') }}

),

normalized as (

    select
        artist_id,
        artist_name,
        tag_count,
        -- lowercase; turn -, +, / into spaces; collapse whitespace runs
        trim(regexp_replace(
            regexp_replace(lower(tag_name), '[-+/]', ' ', 'g'),
            '\s+', ' ', 'g'
        )) as genre
    from tags

),

deduped as (

    -- "Hip-Hop", "hip hop", "hip+hop" all collapse to one genre per artist;
    -- keep the strongest tag count as the signal.
    select
        artist_id,
        max(artist_name) as artist_name,
        genre,
        max(tag_count)   as tag_count
    from normalized
    group by artist_id, genre

),

cleaned as (

    select
        d.artist_id,
        d.artist_name,
        d.genre,
        d.tag_count
    from deduped d
    left join denylist dl on d.genre = dl.tag_name
    where dl.tag_name is null                  -- drop denylisted stopwords
      and d.genre <> lower(d.artist_name)      -- drop the artist's own name as a tag
      and d.genre !~ '^[0-9]{2,4}s$'           -- drop decade tags: 80s, 90s, 00s, 1990s
      and d.genre !~ '^[0-9]+$'                -- drop pure-number tags
      and length(d.genre) > 1                  -- drop single-char noise

),

ranked as (

    select
        artist_id,
        artist_name,
        genre,
        tag_count,
        row_number() over (
            partition by artist_id
            order by tag_count desc, genre
        ) as genre_rank
    from cleaned

)

select *
from ranked
where genre_rank <= {{ var('max_genres_per_artist') }}
