-- Calendar date dimension: one row per day, spanning the full years that
-- appear in the play history. Built data-driven (no hardcoded range) so it
-- grows automatically as more plays land.
with bounds as (

    select
        date_trunc('year', min(played_at))::date                                as start_date,
        (date_trunc('year', max(played_at)) + interval '1 year - 1 day')::date  as end_date
    from {{ ref('stg_plays') }}

),

date_spine as (

    select generate_series(b.start_date, b.end_date, interval '1 day')::date as date_day
    from bounds b

)

select
    -- smart integer key (YYYYMMDD) — the classic date-dimension convention
    to_char(date_day, 'YYYYMMDD')::int          as date_key,
    date_day,
    extract(year    from date_day)::int         as year,
    extract(quarter from date_day)::int         as quarter,
    extract(month   from date_day)::int         as month,
    trim(to_char(date_day, 'Month'))            as month_name,
    extract(day     from date_day)::int         as day_of_month,
    extract(isodow  from date_day)::int         as day_of_week,   -- 1=Mon … 7=Sun
    trim(to_char(date_day, 'Day'))              as day_name,
    (extract(isodow from date_day) in (6, 7))   as is_weekend
from date_spine
