# THE WORLD — Monday 23 November 2026

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/oso161x/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/oso161x/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A one-day newspaper front page that sums up **23 November 2026** in a
single image. Built for the make.fun competition
`news-image-20261123` ("Sum up 23 November's world news in one image").

## The image

`main.py` (Python 3.13, standard library only, no network) composes a
1024×1024 front page and writes it to
`$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output/entry.png`):

- **Masthead** — THE WORLD, Monday 23 November 2026.
- **The day in UTC** — an 8-event timeline strip (early hours: a boy
  pulled alive from the Dymer rubble … afternoon: the G20 closes in
  Johannesburg).
- **Three lead stories**, each with a photo, headline, deck and a
  CONFIRMED source tag:
  1. COP31 collapses with no deal (Antalya, Turkey — BBC).
  2. Russian strike kills 11 in Dymer (AP / Reuters).
  3. Ukraine sinks Russian warship off Libya (Benghazi — BBC /
     France 24).
- **WHERE IT HAPPENED** — a world map with 13 numbered dots for the
  biggest stories, with a printed key.
- **DATE CHECK** — the audit, printed on the page: 8 big stories
  **LEFT OUT** because they belong to another day (the Las Vegas GP,
  Liverpool 4–0 Man Utd, the G20 declaration, Hong Kong's election,
  the 'El Chapo Isidro' capture, Denmark's expulsion of Russia's
  envoy, the Peru and Banda Sea quakes) and 6 **NOT YET** (Spain's
  election, Thanksgiving, the Ayodhya–Janakpur train's first run, the
  Qatar GP, NATO's statement on Poland, the US market open).
- **12 illustrated minis** (Iran's missiles hit Bahrain, the G20
  closes with no handover, Modi's Nepal package, Seoul's first woman
  spy chief, the Nikkei's AI sell-off, the Khartoum drone strikes,
  24 killed in South Sudan, the Houthis' Saudi refinery claim, the
  Democrats' House win, Nvidia's probes, the Banten factory fire,
  Eisenkot's "Jewish terrorism" condemnation).
- **The rest of the day** — 36 more one-line stories, each with a green
  (CONFIRMED) or amber (REPORTED) dot.
- **Markets** — Monday in Asia, labelled as such (Nikkei −5.06%;
  the S&P 500 figure is Friday's close, labelled Friday's close).
- **Footer** — every source named.

Totals: **51 stories · 7 regions** (Middle East, Europe, Asia-Pacific,
South Asia, Africa, The Americas, Global) **· 17 fields** (climate,
conflict, diplomacy, trade, energy, technology, sport, science, health,
culture, crime, disasters, politics, markets, space, defence, society).

## How it works

`main.py` is a deterministic compositor. It decodes the PNG panels and
pre-rendered text strips in `assets/` (photos generated for this entry;
text rendered with DejaVu Serif / DejaVu Sans at build time), lays them
out with fixed geometry, and writes the page with a small
standard-library PNG reader/writer (fixed filter, fixed zlib level, no
timestamps). Two runs produce the same bytes.

```sh
python3 main.py            # writes $MAKEFUN_OUTPUT_DIR/entry.png
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
```

Verified: two runs byte-identical (sha256
`97ec06f5b0c3df7c42b4bcbecad60068b53f38ff64b1c25a9fc9400becfbaa32`
for the final build), 746,354 bytes (≤ 1 MiB), 1024×1024 PNG.

## Sources and confidence

Every story was checked against live reporting on 23 November 2026
(UTC) and is dated to that day. CONFIRMED means verified by the named
source; REPORTED means as reported that day, not yet independently
verified. Claims are labelled as claims (e.g. Iran's account of the
Bahrain strikes, the Houthis' refinery claim, the nuclear-satellite
report). The US market figure is labelled Friday's close. The full
per-story audit is in `SUBMISSION.md` (working file, not in this
repository).

## Licence

MIT — see `LICENSE`.
