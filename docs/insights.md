# Sample insights

Generated from the `analytics` star schema (Phase 3) over the current ~50-play
sample. Reproduce with:

```bash
docker compose exec -T postgres psql -U postgres -d spotify -f - < sql/analysis/insights.sql
```

> Note: this is a small personal sample, so treat the numbers as a demonstration
> of the **data model**, not a statistically meaningful taste profile.

---

## Headline

| total_plays | distinct_tracks | distinct_artists | total_hours |
|---|---|---|---|
| 50 | 49 | 43 | 3.3 |

## Top genres by plays

Genres come from cleaned Last.fm tags via the artist↔genre bridge, so a single
play can count toward each of an artist's (up to 3) genres — totals exceed 50 by
design.

| genre | plays |
|---|---|
| rock | 30 |
| classic rock | 17 |
| hip hop | 12 |
| alternative rock | 12 |
| rap | 11 |
| alternative | 7 |
| pop | 5 |
| grunge | 5 |
| southern rock | 4 |
| new wave | 3 |

## Top artists by plays

| artist | primary_genre | plays |
|---|---|---|
| Creedence Clearwater Revival | classic rock | 4 |
| Larry June | rap | 2 |
| Foo Fighters | rock | 2 |
| Nipsey Hussle | hip hop | 2 |
| The Doors | classic rock | 2 |

## Most-played tracks

| track | album | plays |
|---|---|---|
| Everlong | The Colour And The Shape | 2 |
| Sunday Bloody Sunday – Remastered 2008 | War (Remastered) | 1 |
| Can't Stop | By the Way (Deluxe Edition) | 1 |

## Listening by weekday (`dim_date`)

| day | weekend? | plays | minutes |
|---|---|---|---|
| Wednesday | no | 18 | 65.7 |
| Thursday | no | 32 | 133.3 |

## Plays by album release decade

Shows the date-aware reach of the model — the listening sample spans seven
decades of recorded music.

| decade | plays |
|---|---|
| 1960s | 8 |
| 1970s | 6 |
| 1980s | 7 |
| 1990s | 12 |
| 2000s | 7 |
| 2010s | 5 |
| 2020s | 5 |
