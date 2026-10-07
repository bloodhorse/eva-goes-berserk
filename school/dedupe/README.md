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
uv run --python 3.12 crosscheck.py all          # the audit: titles, text, losses (or one of the three words)
uv run --python 3.12 -m unittest discover -s tests -p '*test.py'
```

`--config other.toml` before the command points at another set of roots. Exit code 2 means the run did
not start or could not write: another run holds the lock, the config is wrong, the state or the output
is read-only, or the index was built with other `[structure]` numbers or another normaliser (then
`rebuild`).

## Files

- `sources.toml` — the roots: name, path, glob, kind (`read`, `incoming`, `reference`), priority,
  where titles come from, whether boilerplate is stripped, whether the copies are rough. A `[[shelf]]`
  block is a folder of roots (`shelf/gpt/text`): every subfolder is a source, so a new magazine folder
  needs no edit. Its head explains every key.
- `crosscheck.py` — the audit, which shares no matcher with the tool (below).
- `ledgers.py` — reads a root's ledger for titles and for the word that a copy came from a PDF.
- `thresholds.toml` — every number a decision rests on, one line of meaning each.
- `state/` — `index.sqlite` (one row per distinct text, keyed by the sha256 of the file's bytes, and
  one row per file with its size and mtime), `segments/` (every shingle of every text, sorted, for
  `lookup`), `plan.jsonl` (one record per file), `pairs.jsonl` (every related pair with its numbers),
  `boilerplate.jsonl`, `skipped.jsonl`, `lock`, and the audit's `crosscheck.jsonl`,
  `crosscheck-text.jsonl`, `crosscheck-losses.jsonl`.
- `out/` — the deduplicated copy, `out/ledger.jsonl` (source file, action, words in, words out,
  reason, counterpart), `out/.trash/<time>/` for outputs a later plan no longer wants.
- `report.md` — the numbers and the lists a person should read.

## How a text is read

A file is cut into paragraphs at blank lines; a paragraph over 200 words is cut further into
sentences, so a book that arrived as one paragraph per page can still be cut inside a page. Words are
normalised one at a time: NFKC (ligatures, full-width forms), case folded, accents dropped, apostrophes
of every shape removed inside a word (the broken ones too: `don?™t`, `donâ€™t`, `don�t`), soft
hyphens and zero-width characters removed, a hyphen at a line end followed by a lower-case letter
joined, every other hyphen, dash and punctuation mark a word break. Spelling is left alone: *colour* and *color* are two words. Every run of 8 words is hashed to
64 bits, across paragraph breaks, so short paragraphs and lines of verse match through their neighbours.

One shingle in eight (`hash % 8 == 0`) goes into the candidate index. Pairs that share sampled
shingles are then compared exactly, on all their shingles.

## How decisions are made

1. **Boilerplate**, per source, in roots that ask for it (every `incoming` root by default, no `read`
   root: `boilerplate = true` in `sources.toml` turns it on for one). A paragraph is boilerplate when it
   sits at the head or tail of many documents of one source and almost never further in: identical
   paragraphs, and paragraphs opening with the same two words (digits blanked), which catches
   `© 2019 by …` and `Originally published in …`. It is stripped only at the edge, with short lines
   caught between it and the edge. A document that would be left with nothing because its paragraphs
   merely open like a template is left whole. Everything after this works on the body that is left.
2. **Rank**. Every text has a fixed rank: `read` over `incoming`, then source priority, then a clean
   copy over a rough one, then a text that contains another over the one it holds (inside one root the
   whole episode stays and its teaser goes; across roots priority has already decided, so a magazine's
   story is still taken out of an anthology), then the longer, then the content hash. A copy is rough when its root says `rough` or its ledger record names a PDF.
3. **Relations**, from the exact comparison of a pair:
   - *identical file* (same bytes), *identical text* (same paragraphs after normalising);
   - *same work*: each holds at least 75% of the other's shingles, or matched blocks cover at least 85%
     of the words of both (the same text with a word wrong in every other sentence);
   - *contained*: one block of paragraphs of the larger holds at least 80% of the smaller;
   - *shares a work*: neither is inside the other, but a matched block of 800+ words sits in both and
     nearly everything they have in common is inside such blocks (two anthologies with one story). In
     a `container` root half is enough: a casebook quotes the novel it excerpts;
   - anything weaker with real overlap is *partial*.
   A shingle found in 20 or more documents is common: it proposes no pair and is discounted from
   every overlap, and no relation short of identical text counts under 100 matched words.
4. **Read against read is left alone.** A text on a `read` shelf is never dropped, cut or stripped
   because of another `read` text: those shelves are tokenised and their held-out splits would move.
   Such pairs, identical files included, are kept on both sides and listed in their own section of the
   report. `read` still beats `incoming`.
5. **Actions**, walking the incoming texts from the highest rank down. A text is dropped when a kept,
   higher-ranked text is the same work or contains it. Otherwise it is kept, and every block it
   shares with a kept, higher-ranked text is cut out of it. So a standalone story is kept and cut out
   of an anthology; an excerpt of a novel she has read is dropped and the novel is untouched.
6. **Prose only one copy has stays.** Inside a matched block, a run of unmatched paragraphs of 100+
   words is not cut with the block; a copy holding such a run, or 250+ unmatched words in a row
   outside its blocks (an afterword), is not dropped whole: its matched blocks go and the rest is
   written. A reworded line still goes with its block. A rough copy is the exception: nothing inside
   its blocks is spared and it is dropped whole below 1,500 unmatched words, because what only a
   rough copy has is spam, broken encoding and running heads.
7. **Around a cut** of 1,000+ words. Up to four heading-shaped lines directly above it go with it
   (title, byline; a bare year line between them and the story too). A longer run of headings is a
   contents page and stays. In a root marked `container = true`, text between such a heading and the
   cut goes too when it is at most 500 words in 6 paragraphs and names a word of the heading (an
   editor's introduction names the author or the title); and where the heading is given twice (author
   and title, the introduction, the title again), the upper heading and the introduction go when the
   upper block repeats a line of the lower one. Nothing else small is removed: prose stranded between
   two cuts stays whatever its size and is listed in the report; only a stranded run of at most four
   headings goes.
8. **The ambiguous band**. A partial pair where one text holds 20%+ of the other, or 500+ matched
   words, gets no action and is listed with both paths and the numbers.

Every record in `plan.jsonl` says why and against which file. The plan depends only on the config and
on the set of files and their bytes: not on listing order, not on how the scan was split over runs.

## The audit

`crosscheck.py` answers "is the plan right" without the tool's index, shingles or thresholds. It reads
the source files, `out/` and `plan.jsonl`, and compares whole sentences of eight or more words.

- `titles` — a list of works from metadata and ledgers (title, authors), and the story headings inside
  every file over 90 kB: a title line with the author's surname near it, an author line with the title
  in the text under it, or two headings two books share side by side. Every work found in two places
  is judged by its sentences (same text, partial, different), and for the same text the outputs say
  whether one copy went: *caught*, *partly cut*, *missed*, or *read-read*.
- `text` — every two files sharing 20+ sentences of ten or more words, whatever their titles, and the
  same verdict from the outputs. This is the one that needs no title.
- `losses` — every sentence of a cut or dropped file that is in no output file. One alone is a line
  another edition words differently; three in a row are a passage nobody kept, and are listed.

Run it after new books land. A *missed* row is a bug or a different edition: the pair is in
`state/pairs.jsonl` with its numbers.

## Hardening

- A file is known by its size and by the later of its modification and status-change times, so content
  replaced under the same name, size and mtime is read again.
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

A new folder under `shelf/gpt/text` is picked up by the `[[shelf]]` block at priority 45; name it under
`[shelf.priorities]` to rank it, under `rough` if it is a damaged twin of a cleaner root, under `skip`
to leave it out. Anything else: add a `[[source]]` block to `sources.toml`, run `daily`. A book shelf
of anthologies gets `container = true` and a low priority, so the magazines' standalone copies win; a
novel or a single story filed there is treated like any other text (only the introduction rule looks
at the flag). To retire a root,
remove its block: its outputs move to `out/.trash/` at the next `apply`.

## Known limits

- Only verbatim text is found. A new translation or a revision that rewords most sentences (a podcast
  reading against the magazine text, in one case of the audit) lands in the ambiguous band or nowhere.
- A text under 8 words has no shingles and matches only as identical text; a work under 100 words is
  never cut out of a container, and a teaser of under 100 words stays beside the story it opens.
- A glued paragraph is cut at sentence ends found by punctuation, so a title glued to a first line
  goes or stays with that line.
- Headings are recognised by shape (one short capitalised line with no closing full stop, not opening
  with a dash). The title of a cut story stays behind where the layout defeats that: a byline ending in
  a full stop, a heading set above a long introduction.
- An editor's introduction longer than the limit, or one that names neither author nor title, and an
  afterword or author's note below a cut story, stay in the container.
- A passage spared from a cut, or the last line of a cut story that the kept copy words differently,
  stays as an orphan paragraph. The report lists them.
- Editorial apparatus (a Summation, Honorable Mentions) is unique text and is not removed; the report
  gives its size per book where the ledger or the text marks it.
- Chains are approximate: a text is always dropped or cut against a kept text it was compared with
  directly, but that kept text may itself have had a span cut for a third. The `losses` audit is the
  check on this.
- The common-shingle discount is estimated from the one-in-eight sample.
- `lookup` reports the corpus as scanned (sources, not `out/`), names at most five documents per run,
  and verifies each run word for word against the source file as it is now.
- `rebuild` leaves the old index in `state/before-rebuild-<time>/`; trash it when the new one is good.
