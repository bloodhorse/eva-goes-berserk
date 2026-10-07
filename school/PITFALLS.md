# pitfalls

Everything that bit while raising magdra, in the order the work happens: find text, cut it,
tokenise it, mix it, ready a machine, start, run. **Read the stage you are about to enter.** Each
entry says what happened, how to catch it, and what to do instead. When something new bites, put
it where it belongs and rewrite the entry if it already exists — this is a map of holes, not a
diary.

The two that cost the most, so nobody skips them:

- **Half the Gutenberg text had no paragraphs, and she read 0.95 billion tokens that way** before
  anyone measured a shelf instead of reading its first page (2.1).
- **Nine magazines out of nine turned out to block AI crawlers or forbid scraping in their
  terms**, found only after three fetch agents were out (1.1).

## 1. Finding text

**1.1 Know what a site says before the agents leave.** "Free to read" was taken for "nobody
minds" and a shelf was promised on it; every magazine checked turned out to have a position, and
three fetch agents were already out when it was looked up. What goes on her shelves is bekh's
call (`CLAUDE.md`, where the text comes from) — the point here is to have the facts first, and
to have all three of them: on 2026-10-07 Beneath Ceaseless Skies was reported "open" from its
robots.txt alone, while every response it sends carries `x-robots-tag: noai`. The three places a
position lives, in one minute:

```bash
S=example.com
curl -s -L -m 15 https://$S/robots.txt | grep -i -E -A1 'GPTBot|CCBot|ClaudeBot|anthropic|Google-Extended|ai-train'
curl -s -I -L -m 15 https://$S/ | grep -i -E 'x-robots-tag|tdm'
curl -s -o /dev/null -w '%{http_code}\n' -m 15 https://$S/.well-known/tdmrep.json
```

Then the terms of use and any "anti-scraping" or AI policy linked from the footer. A blocklist of
named AI crawlers does not stop a plain user-agent, so a fetch "obeying robots.txt" goes straight
through it; say in the brief what the agent should do when it finds one, or it will decide alone.
What was found (2026-10-06):

- **Block AI crawlers in robots.txt**: Clarkesworld, Uncanny, The Dark, Greg Egan, Charles
  Stross, Karl Schroeder, Small Beer Press and lcrw.net (Kelly Link's collections), Escape Pod /
  PodCastle / PseudoPod (their text is CC BY-NC-ND — an email could settle it), Royal Road, AO3,
  Wattpad, SpaceBattles, Sufficient Velocity, Baen, Reddit.
- **Forbid it in their terms**: Lightspeed and Nightmare (a written anti-scraping policy),
  Reactor / Tor.com (terms name AI training), Apex, Smashwords, Weightless Books, Electric
  Literature, Orion's Arm.
- **`x-robots-tag: noai` on every response**: Beneath Ceaseless Skies.
- **Nothing posted**: Strange Horizons (an editorial says they would block scrapers if they had
  the people). Taken, by bekh's call, through its open API.
- **Open or offered**: Faded Page, rifters.com (Watts, CC), rudyrucker.com (he asks to be
  trained on), qntm.org, unsongbook.com and slatestarcodex.com, localroger.com, Wildbow's blog.
- **Not wanted**: the SCP wiki (bekh does not like the writing).

**1.2 Count before promising, and size a source before arguing for it.** The guess was "40–60
million tokens of modern weird fiction". What arrived was 40 million tokens, three quarters of it
literary prose from 1920–1971. A size said before the sources are checked gets planned on. Send
the census (what exists, how big, what it allows) before the fetch, and say an estimate is an
estimate every time it is repeated. The sizing is one line of arithmetic — years × issues a year
× stories an issue × words a story × 1.39 tokens a word — and it comes before the opinion: The
Infinite Matrix was defended on its names (Gibson, Sterling, Le Guin) and kept in a crawl for
twenty more minutes; five years at a story or two a month is a third of a million words, and
what came back was 32 stories and 150 short-shorts, 0.4 M tokens, the famous names having
written columns there, which the brief excluded. SCI FICTION (five years, a story a week, long
ones) was 3.4 M and paid for the trip. The tokens-a-word figure is her own tokenizer on the
library: 5.4 M words came out as 7.5 M tokens.

**1.3 There is no clean bulk source of modern strange prose; there is a pile to be gathered.**
`docs/research/text-sources-2026-10-06.md` is the survey: every careful corpus stops at 1930,
hobbyists train on web crawls, the famous book sets were scraped or pirated. Do not spend
another day looking for the trick. What exists, and what each turned into, is in
`docs/research/text-sources-2026-10-07.md`: the magazines' own archives, the podcasts'
transcripts, author-released backlists, dead magazines in the Wayback Machine, web serials, and
anthologies fetched by hand; still untried, Harvard's Institutional Books (gated,
non-commercial; the unrenewed American books of 1930–63). How much of it there is now is the
last table of `dedupe/report.md`, never a number in a doc.

**1.4 Public-domain traps.** An unrenewed magazine issue can hold individually renewed stories
(*If* from March 1952, *Galaxy* from October 1950), so each story needs its own check;
Gutenberg's volunteers did that work for what is on the sci-fi shelf. The Internet Archive's
pulp scans are OCR in two columns with adverts mixed in (`pd2/REPORT.md`, the verdict). A
Creative Commons release can be withdrawn: one of Kelly Link's two was.

**1.5 Books fetched by hand arrive in batches of about thirty, and a third of them are wrong.**
Of 62 files from one night's fetching, nine were the wrong language or the wrong book and six
were not the format their name said. Budget for that: the converter's gates catch it, but the
re-fetch list has to go back to bekh (`library.md` keeps it).

**1.5b A download's name is a claim, and the text is the evidence.** The fetcher
(`~/tower/ephemeral/booox/`, a title list in, files out) matches by title, and what it brings
back under a title has been: another volume of the same series (a file named *Fourteenth Annual
Collection* held the Fifteenth, one named *Twelfth* the Seventeenth), an epub whose every
chapter is the same error page ("sorry something went wrong loading your content", 53k words of
front matter and nothing else), a zip of loose text files named `.epub`, RTF named `.txt`, one
story of five thousand words under an anthology's title, a PDF of volume two of a two-volume
book, and a novel nobody asked for. Establish what a file is from inside it: a Dozois annual
opens "Summation: <year>"; an anthology's contents page lists the stories that should then be
found in the text. The cheap alarm is the word count against the kind's norm (an annual is
280–370k words, an Infinity book about 97k, a novel 60–150k): a book at a tenth of its norm is
not that book. The converter's own duplicate check (`books.py`: same title and editor, or a
near-identical fingerprint) is what caught the two mislabelled annuals — and the same rule would
eat a real sibling volume whose metadata gives only the series title, so read every `DUP` line
it prints and check the pair by their opening pages.

**1.5c For fetching by hand, the anthology is the unit.** A year's-best is about 300k words in
one file against 90k for a novel, already chosen by an editor, and it brings the print
magazines' best (Asimov's, F&SF, Interzone) that no web archive holds. The cost is that its
stories also arrive as magazine pages and in other anthologies; that is what `dedupe/` is for
(2.9), and without it an anthology shelf cannot be sized. One series per genre per year: Dozois,
Hartwell and Strahan reprint the same stories in the same year.

**1.6 Fetching, once a source is chosen.**
- Look for a ready dump on Hugging Face first (none existed for any magazine; it is a two-minute
  check).
- Use an API if the site has an open one: Strange Horizons' whole archive was 31 requests
  through its WordPress API instead of 3,000 page loads. The price was authors — the API has no
  byline field — which training does not need.
- Keep the raw responses (`modern/<source>/raw/`): the cleaner gets rewritten, the server
  should be asked once.
- An agent that started before a correction reached it will have fetched something. Ask every
  agent what it fetched and have it trashed; three of them had.
- Agents add sources nobody named (Wildbow's Pact, Scott Alexander) and tag files with Finder
  tags. Read each ledger for what is in it beyond the brief.
- A WordPress site usually answers `/wp-json/wp/v2/posts?categories=<n>`: GigaNotoSaurus's 180
  stories were ten requests. A custom post type may not be exposed (Beneath Ceaseless Skies'
  stories are not in `wp/v2/types`), and then the sitemap lists the pages.
- Text gathered by another hand comes with its own doc. `shelf/gpt/` is a collector another
  model wrote (its `README.md` is the doc, its `summary.json` the counts per source): read what
  it says it did *not* do — there, validation, language, dates, deduplication and kind were all
  left to us (2.9, 2.10).

**1.7 A rate-limited crawl is wall-clock, not work.** SCI FICTION was about 1,100 pages; at one
request every four seconds (5.5 in practice) that is over an hour before a word is cleaned, and
the agent that started the fetcher sat on it for three hours and thirteen minutes of a session
for 3.8 M tokens of text. The tokens spent waiting are few; the session's attention is not. A
crawl is launched detached, resumable (skip what is already in `raw/`), with a heartbeat file
(time, count, total, the url in hand), and the agent hands back; the cleaning is a second,
short job when the pages have landed.

**1.8 The Wayback Machine, for a magazine that no longer exists.** What worked
(`modern/wayback/`, `wb.py` and each source's `fetch.py`):
- Enumerate with the CDX API
  (`https://web.archive.org/cdx/search/cdx?url=<prefix>*&output=json&filter=statuscode:200&filter=mimetype:text/html&collapse=urlkey`)
  and fetch `https://web.archive.org/web/<timestamp>id_/<url>` — `id_` returns the page as it
  was served, without the archive's toolbar.
- One request at a time; the API throws 503 and 504 often and once a "Temporarily Offline"
  page, and a sixty-second back-off carried every one of them. The CDX query for a large
  prefix can time out for good (Subterranean's later years never enumerated).
- The index page of the dead site is the census: count its links before fetching, and report
  recovered against indexed, with the missing listed by title. The archive can hold more than
  the index does (131 "classics" folders against 103 listed, and a 118-piece series the index
  never mentioned).
- **A capture can be a stale copy of another page.** The first capture of one story's opening
  page was the second page of a different story, and half of "Abimagique" was filed under "The
  Emperor"; it was found by the dedupe's audit, not by the fetcher. Check every page's own
  title against the work it is being joined to, and record the rejected ones in the ledger.
- Stories were split over several pages under names nobody would guess (`index2.html`,
  `newman01.html`, `waldrop2.1.html`, a root page that is really page one): join by the links on
  the page, never by a filename pattern.
- A reprint's first-publication year is printed only on its page, and may be a collection's
  date; a year set from memory goes in a file of its own (`scifiction/years.json`) so it can be
  seen and checked.
- Pages of that age are windows-1252 served as something else; repair the encoding in the
  cleaner (2.11).

## 2. Cutting and cleaning

**2.1 Measure a shelf by its paragraphs, never by its first page.** `sedthh/gutenberg_english`
marks a paragraph four ways: a blank line after *every* line with the paragraph break shown by
the blank being *absent* (most books); the same with a double blank; no blank lines at all;
one line per paragraph. The first cut (`data/cut.py`) knew one of them. 3,505 of 7,320 books
went in as whole chapters or whole novels in one paragraph — *Count Hannibal*, 600 KB, was four
paragraphs with 515 dialogue turns run together. Nobody saw it for two runs because the opening
of a glued book looks like prose. The check, on any folder of text, before it is tokenised:

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run -q --python 3.12 python data/health.py <dir> [<dir> …]
```

It prints files, size, the median and 90th-percentile paragraph, how much of the text sits in
glued books, what dirt is left, and `OK` or `LOOK: …` (exit 1). `GLUED` — paragraphs were lost.
`SHREDDED-OR-VERSE` — the median paragraph is under 60 characters: either verse, or every
wrapped line became a paragraph. `NESTED` — folders `prep.py` will skip. `DIRT` — the counts on
the line above; two hits inside a story's own prose are not dirt, two thousand are. The old
fantasy shelf answers `GLUED, DIRT`, a third of it glued, 46,165 page markers.

The cut that is used is `data/cut2.py` (same books, by the id lists the first cut chose). It
names a mode for every book in `cut2.tsv`: `doubled`, `plain`, `filled` (no blank lines; breaks
found from short lines that end a sentence), `lines` (one line per paragraph), and `-verse` on
any of them (most lines start with a capital: the line breaks are kept). 24 books still have a
paragraph over 20,000 characters.

**2.2 Every change to the paragraph rules gets sampled per mode.** Three rules looked right and
were wrong on real books: "narrow lines are verse" kept the hard line breaks of 992 books, most
of them pulp prose set in magazine columns; "not tightly wrapped means one line per paragraph" turned wrapped books
into a paragraph per line; "a short line ends a paragraph" split sentences in half. After
touching `clean()`: count the modes, then read three random books from each mode at their
middle, with `¶¶` printed for a paragraph break and `⏎` for a kept line break. A mode whose
count jumps by hundreds is a misfire.

**2.3 Audit a filter by its largest removals.** The first caption filter dropped any paragraph
that mentioned Project Gutenberg. In a glued book a paragraph was the novel: 5.8 MB of prose went
with 73 licence lines, *News from Nowhere* and *Vathek* among it. `data/recut.py` writes
`<out>.recut.tsv` (book, paragraphs touched, characters lost): sort it by the last column and
look at the top before believing the total. A filter that should remove captions and removes
megabytes has eaten a book.

**2.4 Unbounded patterns stall on runs of dots.** `\S*\.(jpg|png)` ran for minutes on books with
long rows of full stops. Every quantifier in a cleaning pattern gets a bound (`{0,60}`).

**2.5 A check that looks at the wrong folder still prints numbers.** A verification loop used
`set -- $pair` in zsh, which does not split words; the grep ran over the whole data directory
and reported "3,195 left" for a shelf that had none. A check prints the path it measured, and a
number that does not move after a fix is a broken check before it is a broken fix.

**2.6 Dirt that has actually shown up.**
- Image captions from illustrated Gutenberg editions, mid-sentence: `p029.jpg (285K) Full Size`.
  She wrote them.
- Gutenberg licence blocks, `***END OF THE PROJECT GUTENBERG EBOOK …***`, transcriber's notes,
  urls.
- Page markers: `[Pg 41]`, a page number alone on a line, and `p. 99` fused to the next word.
- Publisher adverts at the end of a book (five Faded Page books still have them).
- Author bios and "originally published in" at the end of magazine stories (a handful survive
  in Strange Horizons; a stricter rule cut real sentences).
- Text that came through a PDF: broken paragraphs at page ends, running headers (Watts's sixteen
  stories).
- Things that are not fiction inside a fiction tag: essays among Scott Alexander's stories, an
  early draft beside the final version (qntm), a Middle English glossary on the fantasy shelf
  (Gutenberg 42713 — the subject filter lets reference works through).
- Books left out on purpose: *Finnegans Wake* (it would wreck a small model's vocabulary).

**2.6b An ebook is whatever the file actually is.** Of 62 files bekh fetched, four `.epub`s were
plain text in Spanish or Italian, one was a RAR with a Word document inside, one a Word document,
two were zips of scanned-page `.txt` files, two `.txt`s were RTF and HTML, six books were in the
wrong language and two were the wrong book. The first pass of the converter called all 53 it
could open "ok". Check the magic bytes and the language before anything else; `books.py` does
now. Scanned-page zips convert well (`data/pages.py`) but carry whatever was written in the
margins of the copy that was scanned: *Riddley Walker* came with a reader's pencil notes, and in
a book whose spelling is wrong on purpose they cannot be told from the text.

**2.7 An ebook is half packaging, and the health check cannot see it.** The first conversion of
bekh's six left the cover line, the back-cover blurb, "Books by" pages with 873 words of praise
and a 4,534-word afterword by another writer in *Neuromancer* — on the shelf she reads most
often. Pattern counts do not catch a blurb. `data/books.py` writes `inbox/clean/ledger.jsonl`
with every section it dropped and why: read that for each new book, and the first and last 500
characters of its text. What the converter gets wrong: an unlabelled introduction by someone
else is kept; a book packed into one or two files is judged line by line only; footnotes are
removed even where they are part of the fiction; front matter labelled in another language
slips through; an edition that lost its scene breaks (*Count Zero*, *Mona Lisa Overdrive*)
cannot get them back — a better edition can. What the first forty anthologies added
(2026-10-07):
- **It took stories for footnotes.** The full *Big Book of Cyberpunk* lost about 50,000 words —
  seven whole stories and the section introductions — dropped under an `epub:type` note reason,
  because the test for note apparatus matched an element that only *contained* notes. The repair
  belongs in `books.py` (`preclean` and wherever a section is judged to be notes); whether it has
  landed is `git log --oneline -3 data/books.py`. The catch, on any ledger, whatever the fix: list
  every dropped section over 1,500 words and look at it — front matter is short, a story is
  not.
- **It died on its own cleaning.** Removing a tag while walking the list of tags leaves the
  removed tag's children in the list with no attributes; two epubs crashed on it. Fixed; a crash
  is written to the ledger as `error`, and the converter then calls that file done — take the
  `error` lines out of the ledger before running it again.
- **mobi and PDF now have real files behind them.** An old-format mobi is split on page breaks
  and its matter judged by heuristics only (the three Infinity books came through clean). A PDF
  is the last resort: one paragraph per page, running heads, hyphens at line ends; when an epub
  of the same book exists, get it.
- **A slug says nothing when a series shares a title.** Sixteen Dozois annuals came out as
  `dozois-year-s-best-science`, `-2` … `-13`; which volume a file is has to be read from its
  ledger line, and the numbers are the order of arrival.
- **Things land in the wrong folder.** A novel (*Ubik*) arrived among the anthologies; the
  converter writes wherever `--out` points and does not know a library book from an anthology.
- **Dependencies are named on the command line**, since the script is run bare:
  `uv run --python 3.12 --with mobi --with pymupdf --with beautifulsoup4 --with lxml python data/books.py <folder> --out <dir>`.

**2.8 Nothing cleaned is deleted.** A new cut goes beside the old one, and to the archive
(`bek@100.69.218.90:/srv/music/school-archive/`). The Gutenberg source itself had been left out
of the archive and lived only on the borrowed box; it is public (`sedthh/gutenberg_english`, 11
GB) and now also in `/opt/llama/magdra/data/gutenberg/`.

**2.9 The same story arrives four times, and where it does was guessed wrong.** A magazine page,
a podcast's transcript, a year's-best, the author's collection, a chapter of the novel it grew
into. The guess was that the magazines would overlap each other heavily; measured, twelve
magazines lose about 1% to each other (they publish originals, and reprint from print), the
three podcasts about a sixth, the anthologies about a fifth — and an anthology's share rises
as more magazines arrive, so its size is not known until the pile is whole. Duplication is
mostly *inside* a file (a story in a book), so dropping whole files cannot do it.
`dedupe/` does: eight-word shingles over every shelf, a plan of drops, paragraph-span cuts and
boilerplate strips, a clean copy built from the plan in `dedupe/out/`, sources never touched
(`dedupe/README.md`). A cold pass over everything is about a minute, a daily one seconds:

```bash
cd ~/tower/forge/eva-goes-berserk/school/dedupe && uv run --python 3.12 dedupe.py daily   # scan, plan, apply, report.md
uv run --python 3.12 crosscheck.py all                                                   # the audit, below
```

What bit while building it, each of which the next cleaning tool will meet again:
- **"Almost no duplicates" is also what a weak matcher reports.** The first run's low numbers
  were true, and nobody could know that from the tool. The audit shares no code with the
  matcher: every title-and-author found in two places, every pair of files sharing twenty whole
  sentences, and every removed sentence that survives in no output (`crosscheck.py titles | text
  | losses`); and once, forty real stories planted back under seventeen kinds of damage
  (re-wrapped, hyphenated, British spelling, half the sentences edited, a new ending, one
  paragraph per PDF page, inside a 300k-word book). Two independent scrapes of one source are a
  free audit when they turn up: both copies of GigaNotoSaurus had to pair 180 for 180.
- **The cut is safer than what is done around the cut.** The matcher never removed unique
  prose; the rules for tidying after it did — a 444-word Pynchon excerpt taken for the next
  story's introduction, a contributor list taken for a heading, an editor's 78-word note
  removed for being small, a sign-off line taken for a title. Now an introduction goes only if
  it names the story it introduces, and nothing goes for being small. Audit a remover by what
  it takes *beside* its target.
- **Shelves she has already read are never rewritten.** The first plan cut read shelves
  against each other (a Watts novel lost its opening to the story it grew from, a Maugham
  volume 84k words to another book): their held-out sets were cut from those exact files and
  their bins exist. A later cleaning pass reports overlaps between read shelves and leaves both
  alone; what she has read beats what is incoming, and every incoming-against-read hit is the
  contamination check, in its own section of the report.
- **Prose only one copy has, stays.** A copy is dropped whole only when the other holds
  everything in it; a revised ending, an afterword, a hundred words the kept copy lacks, keep
  that part of the file.
- **A clean copy beats a rough one, by rule.** A PDF extraction or a scrape with dirt in it
  ranks below a clean copy of the same work whatever arrived first (`rough` in `sources.toml`).
- **Same name, same size, same mtime, new content** was served stale forever; the index is
  keyed by the bytes now. And fifty thousand tiny files that open alike were all stripped as
  "boilerplate" until that was bounded.
- **Its limits**: verbatim only (a translation, a text reworded in most sentences, heavy OCR
  damage are different texts to it); works under a hundred words are never cut from a book; and
  the big shelves on ds-dev2 (Gutenberg, the light novels, the fan fiction) are not in its
  index, so a pre-1930 story inside a modern anthology is not checked against them.
  `dedupe.py lookup <file>` — every run of eight words a page shares with the corpus, with its
  source — is the recitation meter's engine, with the same blind spot.

**2.10 A folder of "stories" is not all stories, and duplication is not the sieve for it.** A
collector files whatever the site lists under fiction. By cheap signals, about a quarter of
Apex's files are interviews, reviews and columns; a third of The Deadlands' are poems; the three
podcasts hold hundreds of pages under 300 words that are show notes for an episode with no
transcript; extraction stubs exist (a Clarkesworld story of 21 words, an Infinity Plus entry of
47); a year's-best opens with 10–27 thousand words of "Summation" on the year in publishing,
closes with "Honorable Mentions", and puts an editor's note on the author before every story;
web-serial chapters carry author's notes, vote lines and next-chapter links, and some whole
files are announcements. A low average length per file is the first sign (Apex 2,700 words,
Deadlands 1,500) — and Fireside's 2,000 is flash fiction, so the sign is a question, not an
answer. Kind is its own stage after the dedupe (`sieve/`, with its README once it is there):
fiction, non-fiction, verse, stub, each kept in its own tree so nothing is decided by deletion,
and unsure means keep — a lost story costs more than a kept essay.

**2.11 A scraped archive can be poisoned, and broken characters hide a text from a matcher.**
GigaNotoSaurus's archive has injected SEO spam in about sixty stories: casino, loan and
locksmith links as sentences appended to real paragraphs, clauses spliced into real sentences,
whole fake paragraphs in Latin letters swapped for Cyrillic look-alikes. `health.py` sees none
of it (it is prose-shaped). Catch it by outbound links inside a story body and by mixed-script
words; the cleaner there keeps every edited paragraph, before and after, in
`modern/giganotosaurus/spam_removed.jsonl`. A grep for the spam's words afterwards will hit the
stories' own casinos and locksmiths — read the hits. Mojibake is the quiet cousin: a copy with
`don?™t` in every contraction sat at 75–77% shingle overlap with its clean twin, in the band
where nothing was decided. Repair encoding in the cleaner (ftfy did, on the Wayback pages),
and normalise apostrophes of every shape, the broken ones too, before comparing anything.

**2.12 Check the tool that checks.** Two of this stage's instruments were wrong in ways that
looked like findings: a `stat`'s last-read date (5.8) and an open robots.txt (1.1). A verdict
from one signal gets its second signal before it is said aloud.

## 3. Tokenising

**3.1 `prep.py` reads a flat folder of `.txt` and nothing else.** Nested folders and `.jsonl`
are skipped without a word. `health.py` says `NESTED`.

**3.2 The bins and the checkpoint carried the box's paths.** Each `<name>.json` stores an
absolute tokenizer path, and so does every save; on another host the trainer died at its first
sample and the exporter at every snapshot. `train.py` and `export_hf.py` now fall back to the
`.tokenizer/` folder beside the bin — but a copy of the kit from before 2026-10-06
(`kit-before-20261006/`) does not.

**3.3 Held-out numbers do not survive a re-cut, and a small shelf's alarm watches one corner.**
`prep.py` holds out every hundredth document (or 4 MB piece of a long one); a shelf with fewer
than a hundred gets its last 1% instead, so `picks` is watched through the end of one book and
`released` through two files. A shelf that is cut again gets a new held-out set: fantasy 3.46
before and 3.14 after are not a gain.

**3.4 Tokenise where the run will be.** The bins have to end on the training host, the mac has
no room, and the source is 11 GB. The venv there needs `pyarrow` for the cut.

**3.5 rsync carries the repo's file modes.** `scratch/export.sh` was not executable in the
repo; copied over a working kit it gave `Permission denied` on the first export. After sending
the kit: `chmod +x export.sh guard.sh run3.sh`.

## 4. The mix

**4.1 Work out the readings before a run.** A shelf read more than about five times is being
memorised. Readings = the shelf's share of the weights × the run's tokens ÷ the shelf's tokens.
At `day2`'s weights a two-billion-token run would have read bekh's six books 10.6 times and the
cyborg corpus 11 — nobody had multiplied it out. On the training host:

```bash
cd /opt/llama/magdra && python3 - "bins2/fantasy.bin:2000 bins/anime.bin:2100" 2e9 <<'EOF'
import json, sys
mix = [(p.rsplit(":", 1)[0], float(p.rsplit(":", 1)[1])) for p in sys.argv[1].split()]
total = sum(w for _, w in mix)
for path, w in mix:
    n = json.load(open(path[:-4] + ".json"))["train_tokens"]
    r = w / total * float(sys.argv[2]) / n
    print(f"{path:28} {n/1e6:8.1f} M tok  {100*w/total:5.1f}%  read {r:5.1f}x  {'MEMORISING' if r > 5 else 'ok'}")
EOF
```

**4.2 A shelf's share is capped by its size.** Chosen prose cannot be turned up by weight: at
four readings over two billion tokens, each 1% of her diet needs 5 million tokens, about thirty
novels. The way to make good writing louder is more of it.

**4.3 What is read last colours the voice more than what is mixed in thin.** Thirty hand-picked
books at 1% for fifty hours do less than the same books as a third of a short last pass. They
belong to the finishing school.

**4.4 A recipe gets inherited instead of decided.** "The same mix, two billion more" came down
a handoff as a job; the mix was 58% light novels, fan fiction and ballast and 3% of what bekh
had picked. Say the mix back in shares and readings before every run, even when it is "the
agreed one".

**4.5 One author can take a shelf without anyone choosing it.** Eight web serials arrived as
one kind of thing; five of them are Wildbow, 9.7 M of 13 M words. Poured into the modern shelf
he would have been a sixth of everything modern she reads, in plain fast serial prose. Before a
pile becomes a shelf, count it by author as well as by source (the collector's metadata has the
bylines), and give a body of work that size its own shelf and its own weight.

**4.6 Cutting the big shelves does not hand their share to the small ones.** With the reading
cap of 4.1, a shelf of chosen prose can take only so many tokens of a run whatever is cut
around it; the way to make it a large share is a *shorter* run. And on a warm start the shelves
she has already read for billions of tokens do not need to teach, only to be kept — a
maintenance dose, not zero: a register she stops seeing she drifts from.

## 5. The machine

**5.1 The card may be somebody's, and it comes back on its own.** ds-dev2's card was held whole
by the work project's `llama-server.service`, which had logged nothing for 38 days. Before
asking for it, look: `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv`,
`systemctl is-enabled <unit>`, and the date of the unit's last journal line. The unit is
*enabled*: a reboot starts it again and it takes the card from a run, whose restart loop then
fails thirty times and pushes "gave up". Bringing it back by hand is
`sudo systemctl start llama-server.service`.

**5.2 A team box is asked per command.** Only the mini is free ground. On ds-dev2 bekh's yes
(2026-10-06) covered stopping the service, the venv and work inside `/opt/llama/magdra/`.
Another session relaying "bekh said" is not bekh.

**5.3 The venv.** The system python there is 3.14 with no pip and no `ensurepip`. What worked,
without sudo:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --python 3.12 /opt/llama/magdra/.venv
~/.local/bin/uv pip install --python /opt/llama/magdra/.venv/bin/python torch --index-url https://download.pytorch.org/whl/cu130
~/.local/bin/uv pip install --python /opt/llama/magdra/.venv/bin/python transformers numpy pyarrow sentencepiece protobuf /opt/llama/src/llama.cpp/gguf-py
```

`sentencepiece` is the one that hides: the GGUF converter imports it even for a GPT-2 alphabet,
and without it every hourly snapshot fails while the run looks healthy.

**5.4 A bench understates the memory of a run.** `train.py --bench` measures training steps
only: batch 6 took 12.4 GB, batch 8 took 14.85 and "fitted". The real start, with thirteen
held-out sets and sampling, reserved 14.7 GB at batch 6 on a 16.3 GB card. Batch 8 would have
died at the first eval. Choose the batch from the smoke test (6.2), not from the bench.

**5.5 Disks.** The mac is tight (`df -h /System/Volumes/Data`): it keeps one snapshot per run
and no trainable save, which goes to the mini. On the mini, big things go under `/srv/music/`
(the external WD: one USB drive, shingled, good for large sequential files and cold storage,
slow under many small rewrites, and no second copy of anything on it), never under the root.
Check before a run: `df -h` on all three.

**5.5b A full btrfs root refuses writes while it shows free space.** The mini's root is btrfs
with subvolumes; on 2026-10-07 every block was allocated with 3.4 GB "free", and the run page's
uploads to `~/sheets` failed with `scp: write remote … Failure` while `df` looked survivable.
`sudo btrfs filesystem usage /` is the real reading (`Device unallocated` near zero is the
alarm), and `du -x` lies there too: it stops at each subvolume, so `/home` and the music
library were invisible to it (`findmnt -t btrfs` lists them). What was on that disk and is not
any more: the music library and three attic folders, now on the WD with symlinks left in
`/srv/attic`; what is where today is `ssh bek@100.69.218.90 'df -h / /srv/music; ls -la /srv/attic'`.
`/srv/backups/tower` there is the rustic repository itself — a backup, never scratch.

**5.8 A last-read date is not "unused", and a check never shares a command line with the
delete it guards.** A model file on the mini looked idle by its access time (five days) and
was called unused. `nemo.service` loads it once at start and then sleeps: the date said nothing.
The command that deleted it began with a grep for services naming the file — which printed the
service — and went on to the `rm` on the same line. Ask who *opens* a file (`grep -rl <name>
/etc/systemd/system ~/.config/systemd`, `pgrep -af <name>`, `lsof`), read the answer, and only
then send the destructive command, as a second command. A deleted file can be copied back out
of `/proc/<pid>/fd/` only while a process still holds it open; this one did not, and the file
came back from the mac's copy, checked by sha256.

**5.6 Borrowed iron vanishes.** The box was lent for days and its time ran out mid-run. Whatever
exists only there is copied off before the next thing starts, not after.

**5.7 Remote hosts have no Trash.** Test leftovers (`runs/smoke`, `runs/.exporttest-…`) stay
until bekh says delete for good; name them so they are recognisable.

## 6. Starting a run

**6.1 A warm start's rate must be well under the old run's peak.** `day2` first started at
2e-4 and knocked every held-out number up a quarter point; 8e-5 with 300 warm-up steps
recovered half of it in twenty-five minutes. Never 2e-4 on a model that already reads.

**6.2 Smoke-test the real start path.** Forty steps with the real `--init`, every shelf of the
mix, batch and accum as planned, prompts on, into `runs/smoke`:

```bash
cd /opt/llama/magdra && .venv/bin/python train.py --data $MIX --out runs/smoke --init ckpt-7896.pt \
  --batch 6 --accum 4 --lr 8e-5 --warmup 300 --steps 40 --log-every 10 --eval-every 20 \
  --ckpt-minutes 1000 --prompts prompts.txt --compile > runs/smoke.log 2>&1; echo "exit $?"
grep -E "^INIT|^DATA|Traceback|Error|DONE" runs/smoke.log | cut -c1-400; grep "^step" runs/smoke.log | tail -1
```

It has to end in `DONE`, list every shelf with a token count in `DATA`, print a held-out number
for each shelf, write `samples.jsonl`, and stay under the card's memory. It caught nothing on
2026-10-06 only because the path problem (3.2) had been fixed an hour before.

**6.3 Test an export before the run, and know that exports differ by host.**

```bash
cd /opt/llama/magdra && mkdir -p runs/exporttest && ln -sf ../../ckpt-7896.pt runs/exporttest/ckpt.pt \
  && ./export.sh runs/exporttest q8_0 > runs/exporttest.log 2>&1; echo "exit $?"
```

A fresh export of `ckpt-7896.pt` on ds-dev2 matched the box's `model-7896` tensor for tensor,
but ds-dev2's files set `add_bos_token` and the box's did not: a prompt served from a new
snapshot begins a document, one from night1 or day2 continues mid-stream. Fans drawn from the
two are not the same experiment.

**6.4 `run3.sh` takes the mix from outside.** It refuses to start without `MIX` and `HOURS`;
once bekh has said yes to a mix, write both into the file so the run's recipe is in git.
`--init` is read only while the run folder has no `ckpt.pt`.

**6.5 A yes to the mix is not a yes to the run.** Say the plan back with the measured speed, the
batch, the hours and the readings per shelf; bekh starts runs on numbers he has seen for that
machine.

## 7. While it runs

**7.1 Stopping the trainer stops everything.** SIGTERM makes the trainer save and exit, the
wrapper exits with it, the guard sees that and shuts down, and the watcher and the puller end on
`guard down`. To change prompts or recipe mid-run: stop, wait for `STOPPED` and `guard down`,
move `runs/<name>.guard.log` aside, start all five again. Done once on ds-dev2 (2026-10-07,
to add seeds at step 911): the stop took a minute including the guard's last snapshot, the
resume kept the plan (`RESUME from … step=911 total=84103`). Two things the chain does not do
by itself: the puller is asleep for six hours and never sees `guard down`, so the mac's watcher
and puller are killed by pid; and the mac's own copy `night/<name>/guard.log` still says
`guard down`, so it is moved aside too before the watcher starts again. The trainer reads
`prompts.txt` only at start — new seeds need this whole dance.

**7.2 The clock is not in my head.** Hours pass between bekh's messages. Read the run
(`night/mon.py <run> --once`) before saying anything about it; two wrong statements in one day
came from assuming no time had passed.

**7.3 The page shows her worst face.** The run page's samples are drawn at temperature 1 from
all 50,000 tokens. bekh and Claude both called her bad from those; the same snapshot through the
loom's sampler wrote whole sentences. Judge from the loom, and do not oversell her either.

**7.4 Each shelf's held-out number is the memorising alarm — read against its own noise.** A
shelf that turns and climbs while the others fall is being recited. Watch them separately; the
average hides it. But every eval is a different random draw of the held-out set, so each shelf
has a swing of its own: in `day3` the big shelves moved ±0.03 from eval to eval, the small new
ones ±0.015, and net core ±0.1 (its held-out set is 54k tokens). The first night of `day3`
produced three "two rises in a row" that were all noise or drift (lain, base, the library), and
one low-priority push that should not have been sent. The rule that survived: a shelf has to
rise two evals running by more than its own swing, and a shelf she has read less than once
cannot be reciting. The overall number's rhythm was two evals down, one a little back, the floor
lower each time.

`night/turn.py <run>` applies that rule (last three evals against the three before, against
1.5 × the shelf's own median move; `turned` is rising twice over; exit 2). On its first real
call it said fantasy had `turned` at step 25,000 (3.049, up three hundredths over six evals
while the overall number made a new low) and one eval later fantasy read 3.025 and the flag was
gone: a slow wobble with one noisy eval on top. The run was left alone, on three grounds that
held — the move was 1% of the loss, she had read under one pass of that shelf in the run, and
the same evals showed other shelves taking what fantasy gave (trade, in a model with a fixed
budget). So a `turned` is a reason to look and never by itself a reason to act: for `day4`,
where the trainer is meant to act on it, the verdict has to stand for a second eval first, and
the detector's minimum is one fluke away from a false alarm for as long as an outlier low (her
2.977 at 16,000) sits in its window. Push once for a turn and say in the watcher's prompt what
would count as worse; a flag that pushes every hour teaches bekh to ignore the phone.
**The missing instrument is training loss per shelf**: held-out rising while that shelf's
training loss falls is memorising, both drifting together is trade, and the trainer logs one
training loss for the whole mix, so the two cannot be told apart yet.

**7.4b The trainer's speed is a fifty-step window.** `status.json`'s `tok_per_s` and `eta`
cover the last fifty steps; when a save, an eval and the samples fall in that window the line
reads 8.9k instead of 11.9k and the eta jumps fifteen hours, and the page repeats it. The
log's own `elapsed` deltas are the truth (1:43 per fifty steps, every line). Three checks in a
row happened to land on such windows before anyone looked at the deltas. An end time is
arithmetic on the newest log line (now + its `eta`, in UTC), done each time it is said: one
written into a doc goes stale, and one worked out in the head came out seven hours wrong.

**7.5 Only the newest snapshot exists.** By bekh's word the guard deletes the older ones. An age
worth keeping has to be copied aside while it is the newest.

**7.5b The loom's server loads a file once.** `eva.x` fans on whatever `llama-server` on 8086
had when it started, not on `models/<run>/model-latest-q8_0.gguf` as it changes under it; the
walk at step 911 was made that way on purpose, and a day later the loom was still her at step
911. Restart the server for a new hour (`school/CLAUDE.md`, watching and running) until the job
that follows her exists.

**7.6 The mac's half needs the mac.** `watch.sh` and `pull_ckpt.sh` run under `caffeinate`, need
the VPN up and `KEY` in the environment they are started from; when the mac sleeps the page
goes stale while the run is fine. The trainable save crosses the VPN at 4.3 GB a time —
that is why it goes every six hours and not every hour.

**7.7 The hourly look is part of the run.** The bad learning rate was caught by bekh asking,
not by a monitor, so a run is looked at on a clock. It began as every twenty minutes and bekh
cut it to hourly on 2026-10-07: the numbers that matter are the per-shelf evals, one every
thousand steps and about thirty-five minutes, so two checks in three had nothing to say and
said it into his chat. At twelve past the hour a check sees two new evals and the hourly
snapshot with its pull. It is a session cron at `12 * * * *` (`/loop 1h` asks first whether to
make it a cloud schedule — no: it needs this machine's VPN and key; the prompt is in
`school/CLAUDE.md`): it fires only while the session is idle, so a check lands late when
we have been talking, and it dies with the session — a fresh session re-arms it. The report is
five lines, one when nothing moved outside its band. What is given up is the dead-trainer alarm:
the look is the only thing that pushes when the trainer dies, and the worst case is now an hour
of cold card.

## 8. Hands and tools

- **zsh does not split unquoted variables.** `$S host cmd` with `S="ssh -i …"` is one word and
  fails; `set -- $pair` leaves `$2` empty; `$B:path` is a modifier — write `"${B}:path"`. Use
  arrays, or write the command out.
- **`pkill -f` kills the shell that runs it** when the pattern is in its own command line. Kill
  by pid.
- **A foreground command gets about five minutes.** Anything longer on a remote host starts
  under `nohup` with a log that ends in a marker (`BUILD5-DONE`), and is waited for with
  `timeout 420 tail -n +1 -f <log> | grep -m1 <marker>`.
- **A build gets a second agent whose only job is to break it.** The dedupe's builder passed
  its own 61 tests and its own reading; the breaker found unique prose lost around the cuts, a
  stale-file bug and a wipe-out on tiny files, and proved the headline number true by a method
  the builder did not own. Give the breaker the claim to attack first and forbid it the tool's
  own matcher.
- **Tell a running agent when its ground moves.** Sources kept arriving under two agents;
  a message naming the new folders (and which of them are a free test) cost a line and saved a
  re-run. Do not change a root under an agent mid-run without saying so.
- **Agents**: every spawn names `model: 'opus'`; a job with a long wait in it (a crawl, a
  training run) runs detached with a ledger and a heartbeat and the agent hands back, since an
  agent held on a sleeping command holds the session's clock too (1.7); they could not write `.md` into
  the shared checkout, so reports come back as text (the untracked `.claude/settings.json` with
  `worktree.bgIsolation: none` is what lets the main session write in the checkout at all); the brief says what to do at a site that blocks crawlers (1.1),
  "no git", "no code comments" and "write only under …".
- **Count what an agent reports.** `wc -w` over its folder agreed with every report to within
  3%; that is the cost of knowing.
