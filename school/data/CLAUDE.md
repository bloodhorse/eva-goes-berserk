# data — turning files into shelf text

The tools that make text out of what arrives and shelves out of text: the ebook converter, the
health verdict, the assembler of a run's shelves, and the old cutters of the Gutenberg shelves.
Second and fifth stages of the path (`../CLAUDE.md`); the dedupe and the sieve sit between them
(`../dedupe/CLAUDE.md`, `../sieve/CLAUDE.md`). What bit is `../PITFALLS.md` 2 and 3.

## `books.py` — an ebook to body text

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run --python 3.12 --with mobi --with pymupdf --with beautifulsoup4 --with lxml \
  python data/books.py ~/tower/ephemeral/booox/souls_lain_library --out inbox/anth
uv run -q --python 3.12 --with mobi --with pymupdf --with beautifulsoup4 --with lxml python -m unittest data/books_test.py
```

It reads every `.epub`, `.mobi`, `.azw3`, `.pdf` and `.txt` in the folder it is given and writes
one `<slug>.txt` per book into `--out`, with `ledger.jsonl` beside them: one line per source file
— status (`ok`, `skipped`, `duplicate`, `error`), title, author, words, every section kept and
every section dropped with its reason, warnings, and for an annual its `year` or `volume`. The
dependencies are named on the command line because the script is run bare.

**Two output folders, kept apart on purpose.** `inbox/clean/` is the library, bekh's books chosen
one at a time; **she has read those exact files and her held-out set was cut from them, so they
are never re-converted**, whatever a later fix would improve — report what a fix would change and
leave the files. `inbox/anth/` is the anthologies and year's-bests, other editors' taste in bulk.
The converter writes wherever `--out` points and does not know one kind from the other.

What it does, in the order it matters when something goes wrong:

- **It checks what a file is.** Magic bytes and language before anything else: an `.epub` that is
  plain text, a zip of scanned pages, RTF or HTML named `.txt`, a book in the wrong language are
  `skipped` with the reason. `inbox/skip.txt` (in the folder given, else `school/inbox/`) lists
  file names never to convert.
- **It drops packaging by label.** Sections whose nav label, landmark, file name or first heading
  says front or back matter (contents, copyright, introduction, about the author, acknowledgments,
  notes) go, each recorded. Two guards since 2026-10-07: an `epub:type` such as `footnotes`
  describes a section only when its element holds at least 90% of the section's text (a footnote
  block at a chapter's end used to take the chapter), and a matter word on a file's first line
  cannot drop more than 5,000 words. Real footnote apparatus still goes.
- **Per-book fixes are in `FIXES`**, keyed by slug: `start` / `end` / `end_after` patterns that
  trim a book to its body, `sub` substitutions, and **`keep`** — a list of heading patterns for
  sections the label rules would drop and the book needs (a story titled "… (Excerpt)", a story
  with "Book Club" in its name, Sterling's "Preface from Mirrorshades" in the casebook). When the
  ledger shows a dropped section that is a story, the answer is a `keep` line, not a looser rule.
- **It names a book by what the text says.** The slug is surname, the first words of the title,
  then for a series the year the volume covers (a Dozois annual opens "Summation: <year>"), else
  the annual's ordinal, else a volume number (`…-v08`). The file name and the epub's metadata are
  claims; five of eighteen Dozois files were mislabelled. All library slugs are unchanged by this
  rule and a test holds them.
- **It checks for duplicates** against what the ledger already holds: the same title and author,
  or a near-identical fingerprint, and the shorter copy loses — except that books of one series
  with different years or volume numbers are never each other's duplicates (the rule ate six
  annuals before that), and of two copies of one book the one carrying a scanner's or proofer's
  note loses whatever its length.
- **mobi and PDF.** A KF8 mobi is converted as the epub inside it; an old-format mobi is split on
  page breaks and its matter judged by heuristics only. **A PDF is the last resort**: one
  paragraph a page, running heads, hyphens at line ends; the ledger says so in a warning.

**To convert again.** It skips every source already in the ledger. `--force` redoes *every* file
in the folder given, so to redo a few, point it at a scratch folder of symlinks to just those
files with `--force` (slugs stay stable). An `error` line counts as done: take it out of the
ledger before the next run. A book caught mid-download is recorded as `skipped` and stays that
way until its ledger line is removed.

**Read every run's output**: the `SKIP`, `DUP` and `ERROR` lines it prints; in the ledger, every
dropped section over 1,500 words (front matter is short, a story is not); the word count against
the kind's norm (an annual 280–370k, an Infinity book about 97k, a novel 60–150k); the first and
last 500 characters of a new book. Then the health verdict below, then `dedupe.py daily` — two
minutes after the conversion, not sooner (`../dedupe/CLAUDE.md`).

`pages.py <dir> <first> <last> <out>` joins a book that arrived as scanned-page `.txt` files; it
carries whatever was pencilled in the margins of the copy that was scanned.

## `health.py` — the verdict on a folder of text

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run -q --python 3.12 python data/health.py <dir> [<dir> …]
```

Paragraph median and 90th percentile, glued books (a paragraph over 20,000 characters), shredded
ones, nested folders (`prep.py` skips them silently), dirt (urls, image file names, copyright
lines, Gutenberg boilerplate), files under 300 words. Run it on any folder before it is
tokenised: half the Gutenberg text went in glued and nobody saw it for two runs.

**What it cannot see.** Text out of a PDF: a page is about 3,000 characters, far under the glue
alarm, so a book of page-shaped paragraphs with running heads fused into sentences passes. A blurb
or another writer's afterword (the converter's ledger is where those show). Spam injected as
prose (`../modern/CLAUDE.md`, GigaNotoSaurus). A `LOOK: DIRT` on a clean shelf is usually a
"www." inside a story: read the hits.

## `shelves.py` — a run's new shelves

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run -q --python 3.12 --with tokenizers python data/shelves.py build --deep   # assemble, cut held-out sets, check them, print the table
uv run -q --python 3.12 --with tokenizers python data/shelves.py count <folder> [<folder> …]                              # words, tokens and tokens a word with her tokenizer
uv run -q --python 3.12 --with tokenizers python data/shelves.py reject <shelf> <work> [<work> …] --reason "…"            # move works out of a held-out set by hand
```

It reads the sieve's plan and `sieve/out/` and writes `shelves/day4/<shelf>/` (not in git;
rebuilt in under a minute, `--deep` longer): `train/` and `heldout/`, one work a file,
`manifest.jsonl` (source path, title, author, words, tokens, split), `heldout.txt`, and
`summary.json` at the top with every shelf's files, bytes, sha256, words and tokens — the numbers
a recipe and a runbook quote. Which sources make which shelf is at the top of the file
(`MODERN`, `SERIALS`, `ANTH`); anthologies are cut into stories along the sieve's sections and
*Pact* into chapters; a book out of a PDF is picked out by its ledger line and held on
`anth-rough`.

- **Held-out sets are cut by whole works, before she has read a word, and they are sticky.** A
  seeded hash of each work's key picks about 1% of a magazine shelf's works, more of a small one;
  the chosen keys are saved in `heldout.txt` and a rebuild keeps them. Pieces of books are keyed
  by a hash of their opening words, so a re-conversion does not shuffle the list.
- **The contamination check.** Every eight-word run of every held-out work is looked for in every
  training file of the run and in every read shelf whose text is on the mac (`READ_ROOTS`);
  `--also LABEL=FOLDER` adds a folder (the host's sci-fi text was streamed in that way). A
  held-out work that shares text is moved to training and listed in `heldout-rejected.txt`; the
  verdict and the pairs are `shelves/day4/contamination.json`. Not checked: the light novels and
  the fan fiction, whose text is on the host only.
- **Tokens are counted with her tokenizer** (`models/bins/fantasy.tokenizer/`), every file whole,
  chunked and closed the way `prep.py` does it; the counter reproduces the host's totals for the
  library and Strange Horizons to the token. Tokens a word differ by shelf — about 1.45 for the
  magazines and anthologies, 1.59 for the serials, 1.41 for the library — so a size is a count,
  never words times a constant (`../PITFALLS.md` 3.6).
- The trainer draws random offsets, so document order does not matter and nothing is shuffled.

`prep.py` (the kit, `../scratch/`) then tokenises each shelf twice on the training host,
`train/` into `<shelf>.bin` and `heldout/` into `<shelf>.val.bin`, both with `--val-frac 0`; the
order and the checks are in `../night/day4-RUN.md`.

## The Gutenberg cutters

`cut.py` and `base.py` chose the books of the fantasy, sci-fi and base shelves out of
`sedthh/gutenberg_english`. **`cut2.py` is the cut that is used**: it takes the ids those two
chose and cuts the same books again with the paragraphs right (`cut2.tsv` has every book's mode,
paragraph count and longest paragraph), running each through `recut.py`, which drops image
captions (`p029.jpg (285K) Full Size`), Gutenberg boilerplate and urls. It ran on ds-dev2, where
the 11 GB source is (`/opt/llama/magdra/data/gutenberg/`); 24 books (0.64% of the text) still
have a paragraph over 20,000 characters and 90 books of verse keep their lines. `jsonl2dir.py
<src> <out> <field>` turns a jsonl shelf into the flat folder `prep.py` wants; `build3.sh` is a
tokenising batch as it ran on the first box (`build5.sh`, on ds-dev2 only, made `bins2/`);
`peek.py` looks into a parquet dump.
