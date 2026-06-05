-- One row per distinct cleaned genre.
with genres as (

    select distinct genre
    from {{ ref('int_artist_genres') }}

)

select
    md5(genre) as genre_key,
    genre      as genre_name
from genres
