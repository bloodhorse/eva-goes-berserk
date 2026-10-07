# sieve

The stage after the deduper. It reads the deduplicated copy of every `incoming` source (`dedupe/out/<source>/`),
decides what kind of text each file is, cuts the wrappers and the editors' apparatus that are not the story, and
writes each kind to its own tree. Its report's fiction column is what a training recipe counts on. It never
changes a file under `dedupe/` or any source, and it never reads a `read` shelf.

It is the fourth stage of the path a text takes to a shelf (`../CLAUDE.md`, the path). What reads its output
is `../data/shelves.py`, which builds a run's shelves from `out/fiction/` and `out/mixed/` (the prose) and
`out/verse/` (the poems, their own small shelf: bekh's word is that poems are in). `out/nonfiction/` and
`out/stub/` are kept and feed nothing. Why kind is a stage of its own is `../PITFALLS.md` 2.10.

## Commands

Run from `school/sieve` (a small uv project; numpy comes with it only because the deduper's modules are imported):

```bash
uv run --python 3.12 sieve.py daily       # plan, apply, report, review: the whole run after a dedupe
uv run --python 3.12 sieve.py plan        # decide; writes state/plan.jsonl, skipped.jsonl, run.json
uv run --python 3.12 sieve.py apply       # write out/<kind>/<source>/… and out/ledger.jsonl
uv run --python 3.12 sieve.py report      # write report.md
uv run --python 3.12 sieve.py review      # write review.md: the unsure band and a sample of everything else
uv run --python 3.12 sieve.py overrides   # what each entry of overrides.toml matched in the current plan
uv run --python 3.12 -m unittest discover -s tests -p '*test.py'
```

`--config other.toml` before the command points at another setup. Exit code 2: another run holds `state/lock`, a
config or override file is wrong, there is no plan yet, or the state or output cannot be written.

The daily order is `cd ../dedupe && uv run --python 3.12 dedupe.py daily`, then `daily` here. `report.md` names the
dedupe plan it was made from (time, records) and says so if the deduper's files moved while the plan was being made.

## Files

- `sieve.toml` — where the deduper is, each source's profile, which sources come from a fiction-only index, the
  report's piles, where a site prints its own label in the raw HTML, and the per-book switches.
- `thresholds.toml` — every number and every pattern, one line of meaning each.
- `overrides.toml` — hand judgments, each with its reason. The plan obeys them and the report counts them.
- `state/plan.jsonl` — one record per file: `kind`, `why`, `evidence` (signal, value, weight), `shape` (the rates),
  `cuts` (paragraph spans with a reason and a word count), `words`, `words_cut`, `words_out`, the file's sha256;
  for a book, `sections`. `state/run.json` — when, how long, and which dedupe plan. `state/skipped.jsonl` — files
  that could not be read (gone, not UTF-8, no text). `state/labels.json` — a cache of labels read from raw pages.
- `out/<kind>/<source>/<path>` and `out/ledger.jsonl` (source file, kind, words in, words out, cuts with reasons,
  action). `out/.trash/<time>/` holds outputs a later plan no longer wants.
- `report.md`, `review.md`.

## Kinds

| kind | what it is | how it is written |
|---|---|---|
| `fiction` | a story, a chapter, or a book of stories | with its cuts applied: the training candidate |
| `mixed` | a book whose essays are kept on purpose | with its cuts applied; the report splits its words into fiction and essays kept |
| `unsure` | signals disagree | with its cuts applied, in its own tree; kept until someone reads it |
| `nonfiction` | interview, review, editorial, column, essay, notice | whole |
| `verse` | a poem | whole |
| `stub` | a failed extraction, show notes, a teaser, the opening paragraph of a podcast story, a remnant the deduper left | whole |

A paragraph is a block between blank lines; cuts are spans of paragraphs. Anything not clearly something else is
fiction. Dropping a story is the expensive mistake, keeping an essay the cheap one, and the numbers lean that way.

## How a file is judged

In this order, the first that fires decides:

1. **Verse by label**: the page or its metadata says poem (`label_verse`, `class_verse`).
2. **Tiny**: under `tiny_words` words.
3. **Verse by shape**: lines average at most `max_line_words_mean` words and either most words stand in stanzas
   (paragraphs of two or more short lines) or most lines are short and end without punctuation. On a fiction-only
   shelf this gives `unsure` instead. A prose poem has prose lines and stays fiction.
4. **Stub**: what the deduper left of a much longer file; a short file that ends by pointing elsewhere or that its
   index calls an excerpt; a short notice by its title; any podcast page under `podcast_words`.
5. **Non-fiction against fiction**, two scores. Non-fiction: the title says so (`title_nonfiction_strong`, weaker
   hints, notices), the page's label or class, the address, question-and-answer structure (repeated speaker labels),
   the rate of words about writing and publishing, of bibliography, of an editor addressing readers, a low rate of
   story-telling words, a byline that mostly writes columns in that source. Fiction: the source is a fiction-only
   index, the page's classes or label say fiction, a ledger calls it a story, a high narrative rate, paragraphs
   that open with speech, no talk about writing, length. The difference decides: at least `decide_min` is
   `nonfiction`, at least `unsure_min` is `unsure`, anything less is `fiction`. A story told as letters, as a
   transcript or as a review has the costume but not the talk about writing, and stays.

Every fired signal is in the record with its value and weight.

## Edge cuts

Only at the head and tail of a file (`zone_paragraphs`), only what is recognisably a wrapper, never more than
`head_max_words` or `tail_max_share`, and never if it would leave under `min_body_words`:

- from a marker line in the second half to the end: `comments` (“3 Comments”, “Leave a Reply”), `author-bio`
  (“About the Author”), `author-note` (“Author's Note”, “Story Notes”, “Footnotes”, “Afterword”);
- walking in from the end: `credit` (first published, ©, translated by), `nav`, `pitch` (Patreon, newsletter; it must
  also address a reader), `author-bio` (a paragraph that scores as one: name first, biography verbs, bibliography),
  `outro` (podcasts: the show's own names and production words);
- walking in from the head: `content-warning`, `credit`, `nav`, `pitch`, `host-intro`.

Serial chapters are cut by structure: what follows the chapter's `Previous Chapter / Next Chapter` line is the
author's note (`author-note`, `pitch`), what stands before such a line at the head is an announcement or a content
warning. A line with a quotation mark in it is never navigation.

## Anthologies

A book is cut into sections and each section judged; the book as a whole is `fiction`.

- **Boundaries**: the converter's ledger (`inbox/anth/ledger.jsonl`, `sections_kept[].start`, found in order in the
  deduplicated text), headings that name apparatus (`apparatus_titles`), a run of more than `heading_run_max`
  headings (a contents page), and a heading with a byline whose next paragraph names that author.
- **Apparatus by title** is cut to the next boundary: `summation`, `honorable-mentions`, `acknowledgments`,
  `contents`, `copyright`, `also-by`, `bibliography`, `dedication`, `introduction`. A Summation that reaches a
  stretch of narrative before any boundary stops there (flagged in the report). “Introduction”, “Foreword” and
  the like in the middle of a book are apparatus only if the text under them reads as editorial.
- **Editorial by its rates**: a section that talks about writing, tells nothing and has no speech is cut as
  `introduction` before the first story and `editor-note` after it (a stricter line after the first story).
- **Headnotes**: between a story's heading and its first paragraph. A paragraph counts when it names the heading's
  author (with a capital) and has any other mark, or has two marks without the name (a presenting phrase, bibliography
  words, talk about writing); paragraphs that follow one go with it while they present the story or name the
  author. Where the title is printed twice, everything between is the note. Never a paragraph that opens with speech.
- **The title and byline lines of a story stay.** A heading whose story the deduper took is cut with its note
  (`orphan-heading`). Small leftovers before the first story and after the last go as `front-matter`, `back-matter`.
- **`keep_essays`** in `[books.<slug>]` (shell wildcards allowed): essays, introductions and headnotes are marked
  `nonfiction-kept` and stay; contents, permissions, acknowledgments and the like still go; the book is `mixed`.
  On for *Storming the Reality Studio* and *Digital Rapture*; off by default.
- A book left with no story at all is `nonfiction`.

## Overrides

`overrides.toml` forces a kind for a path (wildcards) or a title pattern, or forces a span to be cut or kept. Spans
are found by the opening words of their first and last paragraph, so they survive a dedupe run that renumbers
paragraphs; one that no longer finds its words is listed under “Overrides that could not be applied”, and an entry
that matches no file under “matched no file”. Every judgment made by reading a file is an entry there, the ones
that only confirm the signals too, so a change of thresholds cannot silently flip a file somebody has read.

## Hardening

- The plan depends only on the config and on the files and their bytes: not on directory order, not on the number
  of worker processes (`jobs`). `plan` twice gives the same bytes.
- `plan`, `report`, `review`, the ledger and every output file are written to a temporary file and renamed.
- `state/lock` holds the pid of the running command; a second run refuses to start and a dead pid's lock is cleared.
- A file that is gone, not UTF-8 or empty is listed in `state/skipped.jsonl` and left out.
- `apply` checks each file's sha256 against the plan. A file the deduper rewrote after the plan is `stale`, one it
  removed is `missing`; neither is written, and `apply` says to plan again. Outputs the plan no longer names move
  to `out/.trash/`. A second `apply` writes nothing.

## Known limits

- An essay that never talks about writing (a personal essay about a film, a city, a death) reads like a first-person
  story to these signals and is kept as fiction unless the page labels it. On apex, where the page carries no such
  label, about one fiction file in fifty was such an essay before the overrides.
- A fictional document in an essay's clothes that does talk about books (a story as a book review, as library
  rules) can score as non-fiction where the site does not file it as fiction; the ones found are overrides.
- Verse is recognised by its lines. A poem set as prose paragraphs is fiction; a story set in very short lines is verse.
- Every podcast page under 300 words is a stub. Most are the opening paragraph of a story whose text the site does
  not carry; a complete story that short goes with them.
- Headnotes: in books with long, many-paragraph notes (Hartwell, Cramer, the Big Book of Science Fiction) the tail of
  a note can stay; in the PDF-derived and broken annuals (1998, 2010, “-23”) about a third of the notes are missed;
  a story whose heading lost its byline keeps its note. Author biographies printed after a story are not looked for.
- A book that arrived as glued paragraphs (*Digital Rapture*) cannot be segmented and is kept whole.
- A book converted from a PDF is one paragraph a page, with running heads fused into sentences. It cannot be
  segmented either, so it comes out as `fiction`, whole, with its Summation and every editor's note still in it
  — fifteen books on 2026-10-07 (the Datlow and Windling annuals, *Semiotext(e) SF*). Nothing here flags them;
  `../data/shelves.py` picks them out by the ledger's PDF mark and holds them on a shelf of their own
  (`anth-rough`), out of the mix until bekh says otherwise or an epub replaces them.
- Edge cuts need a marker or a recognisable paragraph. A note with neither stays; a wrapper longer than the limits
  stays and is listed in the report.
- Only the head and tail of a magazine file are looked at: an advertisement in the middle of a story stays.
- The label read from raw HTML is site-specific (`[html_labels]`): deadlands prints the kind, apex prints its
  first tag, which is only sometimes the kind.
