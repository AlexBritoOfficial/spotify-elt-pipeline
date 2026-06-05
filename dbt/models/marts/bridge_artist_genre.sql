-- Many-to-many bridge: each artist to their top-N cleaned genres,
-- carrying the rank and the underlying Last.fm tag count.
select
    md5(artist_id) as artist_key,   -- FK -> dim_artist
    md5(genre)     as genre_key,    -- FK -> dim_genre
    genre_rank,
    tag_count
from {{ ref('int_artist_genres') }}
