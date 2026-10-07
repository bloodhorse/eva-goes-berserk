# Magazine shelf

Resumable collection from Clarkesworld, Lightspeed, Nightmare, Uncanny,
Beneath Ceaseless Skies, Infinity Plus, Escape Pod, PodCastle, PseudoPod,
GigaNotoSaurus, The Dark, Fireside, Fantasy Magazine, The Deadlands,
Apex Magazine, and selected author-hosted web serials. All paths default to
this directory.

## What Claude should ingest

- `text/<source>/*.txt`: UTF-8 story bodies with paragraph breaks.
- `metadata/<source>/*.json`: matching titles, authors, URLs, extraction details,
  index descriptions/classes, and word counts.
- `raw/<source>/*.html.gz`: original HTTP response bodies, including index pages.
- `fragments/<source>/*.html.gz`: extracted HTML bodies; useful when plain text
  loses formatting that matters.
- `manifest.sqlite3`: authoritative durable job ledger and event history.
- `manifest.jsonl`, `failures.jsonl`, `summary.json`: exports updated when a run ends.

**Validation, language checks, completeness checks, publication-date filtering,
corpus deduplication, and training-set assembly are deliberately absent.** Those
belong to Claude's existing pipeline. Word counts describe extracted files, not
accepted training data. No model-token counts are claimed.

The collector tracks requested URLs to support resuming. Different URLs containing
the same story remain separate files. Reprints, poetry in fiction listings, and
Infinity Plus novel extracts are retained. Infinity Plus metadata includes
`is_excerpt_hint` and the index description; these are hints, not classifications.
Some works on Infinity Plus predate 1970. Web publication dates do not establish
the original publication date.

## Run

Dependencies are already installed here. The `uv venv` and `uv pip install`
commands below are setup instructions for a fresh copy of these tools.

```sh
cd /Users/bekh/tower/forge/eva-goes-berserk/shelf/gpt
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# Resume unfinished discovery/downloads; completed URLs are not fetched again.
uv run --no-project --python .venv/bin/python python collect.py crawl

# The 2026 expansion can also be run alone.
uv run --no-project --python .venv/bin/python python collect.py crawl --sources escapepod podcastle pseudopod giganotosaurus thedark fireside fantasy deadlands apex
uv run --no-project --python .venv/bin/python python collect.py crawl --sources katalepsis necroepilogos pale pact worm ward twig

# Only one source. Source selection follows the subcommand.
uv run --no-project --python .venv/bin/python python collect.py crawl --sources infinityplus

# Revisit indexes to discover newly published stories.
uv run --no-project --python .venv/bin/python python collect.py crawl --refresh-indexes

# Retry failures and resume pending jobs.
uv run --no-project --python .venv/bin/python python collect.py retry

# Rebuild story text/metadata/fragments from saved successful responses, offline.
uv run --no-project --python .venv/bin/python python collect.py extract

# Queue explicit story URLs, then resume the source's pending queue.
uv run --no-project --python .venv/bin/python python collect.py fetch infinityplus https://www.infinityplus.co.uk/stories/universallanguage.htm

# One probe, or a separate continuous read-only monitor.
uv run --no-project --python .venv/bin/python python monitor.py
uv run --no-project --python .venv/bin/python python monitor.py --watch 30 --until-finished
```

`--root /absolute/path` selects a separate shelf. Global options precede the
subcommand. `--delay 0.75` sets the pause after each successful HTTP response per
worker; default is 1.5 seconds. There is one network worker per source by
default; `--workers-per-source 2` allows two concurrent workers per selected
source. `crawl --limit 10` processes at most ten jobs per worker, including
index jobs.

Only one collector can write a shelf at a time; an advisory lock prevents
accidental simultaneous runs. Stop with Ctrl-C or SIGTERM. The current network
request may take up to its timeout to finish. Restarting recovers interrupted
jobs. Do not delete the SQLite ledger to resume a run.

## Discovery and extraction

| Source | Entry points | Story body |
| --- | --- | --- |
| Clarkesworld | `https://clarkesworldmagazine.com/category/text/`, archive pagination | `.story-text` |
| Lightspeed | `https://www.lightspeedmagazine.com/fiction/`, archive pagination | `#content .single_entry.entry-content` |
| Nightmare | `https://www.nightmare-magazine.com/fiction/`, archive pagination | `#content .single_entry.entry-content` |
| Uncanny | `https://www.uncannymagazine.com/type/fiction/` and `/type/reprints/`, archive pagination | `article.type-article .entry-content` |
| BCS | `https://beneath-ceaseless-skies.com/issues/YYYY/`, 2008 through the current year, yearly pagination | `.bcs-story-content` |
| Infinity Plus | `https://www.infinityplus.co.uk/stories/indexaf.htm`, `indexgm.htm`, `indexnz.htm` | table cell containing the heading, with a legacy layout fallback |
| Escape Pod / PodCastle / PseudoPod | home-page archive and pagination | episode story heading through story end, excluding show notes and commentary |
| GigaNotoSaurus / The Dark | fiction category and pagination | story content container |
| Fireside | `/magazine` issue listing, short-story entries only | `.story-body` |
| Fantasy Magazine | fiction category and pagination at Psychopomp | `.entry-content` |
| The Deadlands | issue index and issue tables of contents | `.dl-story__body` |
| Apex Magazine | publisher article sitemaps | `.apex-story__body` |
| Katalepsis, Necroepilogos, Pale, Pact, Worm, Ward, The Wandering Inn | chapter tables of contents | chapter content container |
| Twig | chapter categories in the site's navigation menu | `.entry-content` |

Discovery uses story listings, not whole-domain traversal. Infinity Plus also
follows links within `/stories/` to collect separately linked chapter pages;
these remain separate files. BCS audio companions are not text-story URLs.
Off-site Infinity Plus links are not followed. Downloaded
pages are cached before extraction, so parser changes do not require refetching.
Successful response bodies, failed HTTP response bodies, and original URLs are
retained. Missing story containers become logged extraction failures.

Apex's sitemaps mix fiction and nonfiction; metadata flags this, and Claude's
downstream pipeline decides what to keep. The Deadlands issue tables can also
include poetry and nonfiction. Reactor's original-fiction archive returned
Cloudflare HTTP 403 to this collector and is not configured as a source.
These free-to-read archives do not grant a blanket reuse licence.
The Wandering Inn table of contents was discovered, but sampled chapter requests
returned an empty shell or HTTP 403 during this run. It remains in the job ledger
for inspection and is excluded from default `crawl`/`retry` source selections.
The older Escape Artists archives contain audio-only episodes, announcements,
and reviews; these remain visible as failed story jobs when no text body exists.
Ward's stale `glow-worm-0-03` link is still in the ledger; the corrected
`glow-worm-0-3` chapter was collected separately.

At the end of the October 7 expansion, the new sources had 7,990 story/chapter
files and 32,350,040 extracted words. Combined with the original six magazines,
the shelf had 13,289 text files and 61,456,842 extracted words. These are raw
counts before Claude's filtering and deduplication. The authoritative current
counts are always in `summary.json`.

The HTML-to-text renderer preserves paragraph boundaries, inline text adjacency,
line breaks, and common section breaks. Known site-template sharing widgets,
author bios, and subscription blocks are excluded from extracted fragments.
Some editorial notes and copyright lines may remain; downstream cleanup decides
what to retain. The untouched raw page remains available in every case.

## Progress and failure handling

`heartbeat.json` is written every five seconds during a crawl. `monitor.py`
reports three separate signals: its own `probe_at`, the collector's heartbeat
age, and each source's age since a completed job. A fresh heartbeat with old
progress can mean a slow request or retry backoff, not a dead process. A finished
run may still have failures or pending jobs; inspect the counts and source phases.

Network errors and selected HTTP errors get up to three attempts with backoff.
Three consecutive 403/429/503 job failures stop that source, leaving its remaining
queue pending. There is no authentication, paywall handling, CAPTCHA solving,
proxy rotation, or alternate identity. Failed jobs retain their error and status.

The initial collection's event output is in `collector.log`; expansion events
are in `collector-extra.log`, local re-extraction in `collector-reextract.log`,
and the Ward link fix in `collector-ward-fix.log`. Historical errors
there remain even if a subsequent run succeeds. Use the current ledger or exported
`failures.jsonl` for unresolved failures. Finder tags are applied to generated
artifacts on macOS. Acquiring a public page does not establish a reuse license.
