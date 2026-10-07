# modern — the shelves we fetched ourselves

One folder a source. Each holds its scripts, `raw/` (pages as fetched), `text/` (one work a file,
body prose, paragraphs parted by a blank line) and `ledger.jsonl` (one line a work: title, author,
url, words, and for anything skipped the reason). `raw/` and `text/` are not in git; scripts and
ledgers are. Every fetcher skips what is already in `raw/`, so a re-run is a resume. This is one
of three doors text comes in by — the others are `shelf/gpt/` at the project root (a collector
another model wrote for bekh: magazines, podcasts, serials; its `README.md` is its doc, it is
read-only to us) and books by hand (`../data/CLAUDE.md`, `../library.md`). What bit while
fetching is `../PITFALLS.md` 1; size a source before starting on it (1.2).

After anything here changes: `../dedupe` `daily`, then `../sieve` `daily`.

## Read by her already

- **`strangehorizons/`** — the magazine's fiction and poems through its WordPress API:
  `text/` the stories, `poetry/` the poems (their own shelf, `horizons-verse`).
  `uv run --python 3.12 python fetch.py` (arguments name kinds to fetch), then `clean.py`.
- **`fadedpage/`** — 1920–1971 literary prose from Faded Page: Faulkner, Woolf, Lowry, Flann
  O'Brien, O'Connor, McCullers, Waugh, Steinbeck, Dinesen. `picks.tsv` is the selection with a
  reason a book, `fp_get.sh` fetches (one request at a time), `strip.py` cleans, `rescue.tsv`
  what had to be got another way. The shelf is `literary`.
- **`released/`** — fiction its authors serve themselves, one folder an author, fetched by the
  scripts in `_scripts/` and `_scripts2/` (one a site): Rucker (`rucker.py`, `rucker2.py`: the
  complete stories and the free books), Watts (`watts.py`), qntm, Scott Alexander (`unsong.py`),
  Roger Williams (`williams.py`), one Kelly Link story (`link.py`),
  and Wildbow's *Pact* (`wildbow.py`), fetched then and kept out of what she read. `egan/` and
  `stross/` hold a ledger and no text. `_scratch/` is working files, not in git.

## Part of the pile, not read yet

- **`released/shiner/`** — Lewis Shiner's whole backlist from his own site: seven novels out of
  PDF, the stories out of HTML, each ledger line carrying its licence. The novels were pulled with
  `pdftotext -bbox-layout`, because the paragraph indent is the only paragraph signal in those
  PDFs; small-caps acronyms can come out lower-case. Stories that are a novel's chapter under
  another name were measured by eight-word runs and skipped where the novel holds them.
  ```bash
  cd ~/tower/forge/eva-goes-berserk/school/modern/released/shiner
  uv run --python 3.12 python fetch.py > fetch.log 2>&1
  uv run --python 3.12 --with beautifulsoup4 --with lxml python clean.py
  ```
- **`giganotosaurus/`** — one long story a month since 2010, through the site's WordPress API.
  **Its archive carries injected spam in about sixty stories** (links spliced into sentences,
  whole fake paragraphs in look-alike letters); the cleaner removes it and keeps every edited
  paragraph, before and after, in `spam_removed.jsonl`, and what else it cut off the edges in
  `cut_edges.jsonl`. The collector in `shelf/gpt/` fetched the same magazine without that
  cleaning; the dedupe marks that copy rough and this one wins.
  ```bash
  cd ~/tower/forge/eva-goes-berserk/school/modern/giganotosaurus
  uv run --python 3.12 python fetch.py >> fetch.log 2>&1
  uv run --python 3.12 --with beautifulsoup4 --with lxml python clean.py
  ```
- **`wayback/`** — two magazines that no longer exist, out of the Internet Archive.
  `scifiction/`: Ellen Datlow's SCI FICTION (2000–2005) — every original, the reprints first
  published from 1970 on, and Swanwick's Periodic Table short-shorts; `years.json` holds the
  seven first-publication years set by hand. `infinitematrix/`: The Infinite Matrix (2001–2006),
  a few dozen stories and a great many short-shorts; its columns and diaries were not fetched.
  `subterranean/` was enumerated and never fetched (bekh's call, on its size against the wait).
  `wb.py` is the fetching (the CDX API to enumerate, `id_` URLs for pages without the toolbar,
  one request at a time, a minute's back-off on 503/504), `word.py` and each `word/` what the
  archive and the sites said of themselves, `prose.py` the shared cleaning. A stale capture can
  file a page under the wrong story: each page's own title is checked against its work and a
  rejected page is recorded as `foreign_pages` in the ledger.
  ```bash
  cd ~/tower/forge/eva-goes-berserk/school/modern/wayback
  uv run --python 3.12 python enumerate.py
  uv run --python 3.12 python scifiction/fetch.py all
  uv run --python 3.12 python infinitematrix/fetch.py all
  uv run --python 3.12 --with beautifulsoup4 --with lxml --with ftfy python scifiction/clean.py
  uv run --python 3.12 --with beautifulsoup4 --with lxml --with ftfy python infinitematrix/clean.py
  ```
  A crawl of a thousand pages at five seconds a page is an hour and a half of wall clock: start
  it detached with its heartbeat and come back (`../PITFALLS.md` 1.7, 1.8).

How much each source is worth after duplicates and kind is its row in `../dedupe/report.md` and
`../sieve/report.md`, never a number here.
