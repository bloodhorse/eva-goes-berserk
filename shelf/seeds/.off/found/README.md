# found

Twenty first-person documents cut out of public-domain books **by script**, not by hand. Everything
here is the work of `harvest.py`; no word was composed, chosen or retyped by anybody.

## why the seams are machine-cut

bekh, 2026-09-19: hand-picking a passage and shaping its last line worked when experiments came in
ones and twos. The stream draws **288 seeds a day**, and at that rate it is manual labour, so this
folder is cut by machine **by decision, for the stream only**. The lab's rule still stands
everywhere else: in an experiment, the seam is his.

This grows the pot; it does not answer the open question of how seeds grow on their own
(`BRIEF.md`, parked). His frame there makes models the source of seeds, and a Gutenberg
harvester is not a model. It buys time — the pot was 78 files with eight of them on switchboards,
so one page in ten was a wire page whichever file was drawn.

## what the cutter looks for

A window passes only if all of it is true:

- **An `i` already inside a situation.** `I`/`we` in the first forty words and a first-person word
  still alive in the last sixty; at least 2.5 first-person words per hundred. A window that drifts
  into exposition by the seam hands the model an essay to finish.
- **A scene, not a sermon.** Either the `i` doing something in past time (`I went`, `we saw`) or a
  dated diary entry heading the window. Without this a devotional passage passes every other test.
- **No reported speech.** No quotation marks at all, and no *he said* / *said she*: a seam inside
  somebody else's talking continues them, not the `i`.
- **Sober, plain running prose.** No headings, no ALL-CAPS, no verse (decided before the hard
  wrapping is undone — once the lines are joined a poem looks like a paragraph), no brackets,
  underscores, `//`, `@` or URLs, no *chapter* / *illustration* / *footnote* / *see page*, fewer
  than 1.2% digits, no question mark anywhere.
- **Short**: 500–1100 characters. A long seed is a style lesson.
- **The seam** ends three to twenty words into a sentence that is underway, on a whole word whose
  last character is a letter. That single rule kills the known traps at once: no trailing space or
  tab (the next token comes out a numeral), no comma, no colon-slot, no question, no dash. The
  file ends exactly at the seam, with **no final newline**.
- A word hyphenated across a line by the scanner (`well- regulated`) is **refused, never
  repaired** — nothing in this folder is an altered character.

Windows are cut from the middle 8–94% of each book (front and back matter thrown away wholesale),
the two per source come from different halves so they are never neighbours, and the seam among the
valid ones is picked **by lot** — taking the longest valid seam every time pinned every seed to the
1100 ceiling. `RANDOM_SEED` fixes the draw: an unchanged source list gives the same twenty files
forever.

## the sources

Ten books, each verified against the live catalogue: English, public domain, first-person prose,
and none of them repeats `../first-person/`. Breadth of *situation* is the point. No telephones
and no telegraphs — the pot already leans that way.

| gutenberg | kind | title, author, year |
|---|---|---|
| 30197 | polar | Farthest North, vol I · Fridtjof Nansen · 1897 |
| 1356 | whaling | The Cruise of the "Cachalot" · Frank T. Bullen · 1898 |
| 41234 | mountain | Scrambles Amongst the Alps in the Years 1860-69 · Edward Whymper · 1871 |
| 71609 | prison | Andersonville Diary · John L. Ransom · 1881 |
| 46179 | asylum | Two Years and Four Months in a Lunatic Asylum · Hiram Chase · 1868 |
| 18910 | nursing | Diary of a Nursing Sister on the Western Front, 1914-1915 · anonymous · 1915 |
| 13279 | soldier | A Yankee in the Trenches · R. Derby Holmes · 1918 |
| 37311 | religious | The Journal, with Other Writings of John Woolman · 1774 |
| 11039 | travel | A Woman's Journey Round the World · Ida Pfeiffer · 1852 |
| 12797 | trail | The Log of a Cowboy · Andy Adams · 1903 |

A seed is named `<gutenberg id>-<nn>.txt`, so any file says where it came from.

## re-running

```bash
uv run --python 3.12 shelf/seeds/found/harvest.py <cache-dir>
```

Stdlib only. Each book is fetched once into `<cache-dir>` as `pg<id>.txt` and never again; a fetch
sends a UA and waits two seconds. Every run rewrites all the files identically, so it is safe to
run any time. **A seed written here is live on the stream's next tick** — to look before shipping,
run it with `--out=<somewhere else>` and copy the files in afterwards.

To grow the pot: add rows to `SOURCES` and raise `PER_SOURCE`. Both are at the top of the script.

## known

These are real documents from the 1770s to the 1910s and the cutter is blind to what they are
about, only to their shape. Period language and period attitudes come through verbatim — one of
the twenty has an 1864 prisoner writing *negro sentinels*, and a test continuation from the travel
journal produced an antisemitic aside of its own accord. Nobody is awake at 03:00 when the stream
draws. If that is not wanted, it has to be a rule in the cutter, and it has not been written.
