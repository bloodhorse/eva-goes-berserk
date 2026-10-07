# dedupe

Finds text that repeats across the shelves and writes a copy of the corpus without the repeats. The same
story arrives as a magazine page, a reprint, a chapter of a novel and a section of an anthology; this
tool decides which copy stays, cuts the others out at paragraph edges, and says how much text there
really is. It never changes, moves or deletes a source file.

## Commands

Run from `school/dedupe` (the folder is a small uv project, so numpy comes with it):

```bash
uv run --python 3.12 dedupe.py daily            # scan, plan, apply, report: the whole daily run
uv run --python 3.12 dedupe.py scan             # read new and changed files into state/
uv run --python 3.12 dedupe.py plan             # decide; writes state/plan.jsonl, pairs.jsonl, boilerplate.jsonl
uv run --python 3.12 dedupe.py apply            # write the deduplicated copy into out/<source>/ with out/ledger.jsonl
uv run --python 3.12 dedupe.py report           # write report.md
uv run --python 3.12 dedupe.py lookup page.txt  # runs of 8+ words of page.txt found in the corpus (--json, or - for stdin)
uv run --python 3.12 dedupe.py compact          # merge lookup segments, forget texts no file holds any more
uv run --python 3.12 dedupe.py rebuild          # set the index aside and scan from nothing
uv run --python 3.12 -m unittest discover -s tests -p '*test.py'
```

`--config other.toml` before the command points at another set of roots. Exit code 2 means the run did
not start: another run holds the lock, the config is wrong, or the index was built with other
`[structure]` numbers (then `rebuild`).

## Files

- `sources.toml` — the roots: name, path, glob, kind (`read`, `incoming`, `reference`), priority,
  where titles come from. Its head explains every key.
- `thresholds.toml` — every number a decision rests on, one line of meaning each.
- `state/` — `index.sqlite` (one row per distinct text, keyed by the sha256 of the file's bytes, and
  one row per file with its size and mtime), `segments/` (every shingle of every text, sorted, for
  `lookup`), `plan.jsonl` (one record per file), `pairs.jsonl` (every related pair with its numbers),
  `boilerplate.jsonl`, `skipped.jsonl`, `lock`.
- `out/` — the deduplicated copy, `out/ledger.jsonl` (source file, action, words in, words out,
  reason, counterpart), `out/.trash/<time>/` for outputs a later plan no longer wants.
- `report.md` — the numbers and the lists a person should read.

## How a text is read

A file is cut into paragraphs at blank lines; a paragraph over 200 words is cut further into
sentences, so a book that arrived as one paragraph per page can still be cut inside a page. Words are
normalised one at a time: NFKC (ligatures, full-width forms), case folded, accents dropped, apostrophes
of every shape removed inside a word, soft hyphens and zero-width characters removed, a hyphen at a
line end followed by a lower-case letter joined, every other hyphen, dash and punctuation mark a word
break. Spelling is left alone: *colour* and *color* are two words. Every run of 8 words is hashed to
64 bits, across paragraph breaks, so short paragraphs and lines of verse match through their neighbours.

One shingle in eight (`hash % 8 == 0`) goes into the candidate index. Pairs that share sampled
shingles are then compared exactly, on all their shingles.

## How decisions are made

1. **Boilerplate**, per source. A paragraph is boilerplate when it sits at the head or tail of many
   documents of one source and almost never further in: identical paragraphs, and paragraphs opening
   with the same two words (digits blanked), which catches `© 2019 by …` and `Originally published
   in …`. It is stripped only at the edge, with short lines caught between it and the edge. Everything
   after this works on the body that is left.
2. **Rank**. Every text has a fixed rank: `read` over `incoming`, then source priority, then a
   standalone text over one that contains another, then the longer, then the content hash.
3. **Relations**, from the exact comparison of a pair:
   - *identical file* (same bytes), *identical text* (same paragraphs after normalising);
   - *same work*: each holds at least 75% of the other's shingles;
   - *contained*: one block of paragraphs of the larger holds at least 80% of the smaller;
   - *shares a work*: neither is inside the other, but a matched block of 800+ words sits in both and
     nearly everything they have in common is inside such blocks (two anthologies with one story);
   - anything weaker with real overlap is *partial*.
   A shingle found in 20 or more documents is common: it proposes no pair and is discounted from
   every overlap, and no relation short of identical text counts under 100 matched words.
4. **Actions**, walking the texts from the highest rank down. A text is dropped when a kept,
   higher-ranked text is the same work or contains it. Otherwise it is kept, and every block it
   shares with a kept, higher-ranked text is cut out of it. So a standalone story is kept and cut out
   of an anthology; an excerpt of a novel she has read is dropped and the novel is untouched.
   A copy that holds an unmatched block of 1,500+ words is never dropped whole: only its matched
   blocks go.
5. **Around a cut**. Up to four heading-shaped lines directly above a cut of 1,000+ words go with it
   (title, byline). In a root marked `container = true`, an editor's introduction between such a
   heading and the cut goes too (up to 500 words in 6 paragraphs), and so does a second heading block
   above it. Unmatched text left between two cuts, or between a cut and the file's edge, is removed
   when it is 80 words or less; longer remnants stay and are listed in the report.
6. **The ambiguous band**. A partial pair where one text holds 20%+ of the other, or 500+ matched
   words, gets no action and is listed with both paths and the numbers.

Every record in `plan.jsonl` says why and against which file. The plan depends only on the config and
on the set of files and their bytes: not on listing order, not on how the scan was split over runs.

## Hardening

- A file modified in the last 90 seconds waits for the next run. A file that is empty, not UTF-8,
  binary, over 64 MB, without a single word, gone, or changed while being read is skipped with its
  reason in `state/skipped.jsonl`; a file skipped for its content is not read again until it changes.
- A root that cannot be listed forgets nothing: its files stay in the index for that run.
- The index is committed in batches inside sqlite transactions; a segment file is written and
  renamed before the transaction that names it. `plan`, `report` and the ledger are written to a
  temporary file and renamed. Kill any command at any moment and run it again.
- `state/lock` holds the pid of the running command; a second run refuses to start, and a lock whose
  pid is dead is cleared.
- `apply` checks each source file's sha256 against the plan. A file that changed after the scan is
  not written (`stale` in the ledger) until the next scan and plan.

## Adding a root

Add a `[[source]]` block to `sources.toml`, run `daily`. A book shelf of anthologies gets
`container = true` and a low priority, so the magazines' standalone copies win. To retire a root,
remove its block: its outputs move to `out/.trash/` at the next `apply`.

## Known limits

- Only verbatim text is found. A new translation, a heavy rewrite, or OCR bad enough to break most
  8-word runs is invisible.
- A text under 8 words has no shingles and matches only as identical text; a work under 100 words is
  never cut out of a container.
- A glued paragraph is cut at sentence ends found by punctuation, so a title glued to a first line
  goes or stays with that line.
- Headings are recognised by shape (one short capitalised line with no closing full stop). A story's
  last short section under such a line, sitting right above a story that is cut, would be taken for
  an introduction; this is why introductions are removed only in `container` roots, and every such
  cut is in the plan with its word count.
- An editor's introduction longer than the limit, and an afterword or author's note below a cut story,
  stay in the container.
- Chains are approximate: a text is always dropped or cut against a kept text it was compared with
  directly, but that kept text may itself have had a span cut for a third.
- The common-shingle discount is estimated from the one-in-eight sample.
- `lookup` reports the corpus as scanned (sources, not `out/`), names at most five documents per run,
  and verifies each run word for word against the source file as it is now.
- `rebuild` leaves the old index in `state/before-rebuild-<time>/`; trash it when the new one is good.
