# school

Raising our own model from random weights, instead of doing things to somebody else's. bekh,
2026-10-06, after a day of drugging llama and probing five bases for a soul: *i don't wanna
fuck around with nemo at all, i wanna build our own model.* A model's person is its diet (the
letter-*i* probe, `docs/soul/`), so here we choose every page it ever reads: no press releases,
no product pages, no support forums.

Two parts. **A childhood**: hundreds of millions to a few billion tokens on shelves of our
choosing, enough to learn English in the accents we want. **A finishing school**: a short,
gentle pass on the small precious texts, redone as often as we like, on whichever age of her
bekh picks. The blend is his: **dark souls** (its cadence and voice more than its lore), **the
visionary** (*language infused by creativity, futurism and sci-fi and the idea of a new time… the
merging of two realities, the digital one of numbers and ideas with the real one*, Serial
Experiments Lain, tears in rain, Prophecies), and **anime girls**. Lain is the bridge between
the last two. The age we want is **teenage**: sentences that hold on their own, two or three
hanging together, the paragraph drifting, no idea what the book is about — *teenage angst and
dreams* — which is bekh's definition of a dream in `BRIEF.md`; the adult that holds a thread
across its window is the 70B problem again in miniature.

**This file is the map.** Each part of the school has its own doc next to its code; what is here
is who she is, the path a text takes, what is running, and what is next.

## magdra

The child's name, bekh's yes on 2026-10-06 (*might add something later*). From her own mouth:
twenty-two minutes old, on the Gibson line, she wrote *"The sky above the port was still maiden
in the Mag dra of a situation"*. Nobody chose the word and it is in none of the books.

355 million parameters: a Llama-style decoder (rotary positions, RMSNorm, SwiGLU, tied
embeddings), 24 layers, 1024 wide, 16 heads, a 1024-token window, GPT-2's tokenizer — the
shape and alphabet llama.cpp converts and serves without complaint (our own byte-level BPE is
rejected by the converter's hash check; our own SentencePiece would pass). Size, alphabet and
window are fixed for good; everything else is more reading. `--init` warm-starts a new run
from any save with a fresh schedule, so she keeps what she has and continues on any card.

**Where she stands** is a query, never a sentence here: `night/mon.py <run> --once`, the run's
page, `night/turn.py <run>` (`night/CLAUDE.md`). Four runs so far — `night1` from random weights,
`day2`, `day3` on ds-dev2 (stopped by decision two fifths through), and `day4`, a short dense run from
`day3`'s save that finished on 2026-10-08; what each was is in `night/CLAUDE.md`, what each read in
`SHELVES.md`. Her age in tokens is `tokens_seen` summed over the runs (about 1.77 billion when
`day3` stopped, about 2.17 billion after `day4`); it counts any tokens and says how much she has eaten, not what she has become
(`night/CLAUDE.md`, the machines).

**How she writes**, as last read (2026-10-08, the seven sampled draws of `day4`'s final snapshot,
step 16,215, against its steps 1,135 and 7,953 and `day3`'s 32,721 — a model's read, one draw a
seed, which bekh has neither confirmed nor overruled; to be overwritten by the next read): she
holds a room now. At the end of `day3` five seeds of seven drifted into the same floor, two people
trading quotation marks; at the end of `day4` two do, and one person in one place is kept for a
whole draw (*"There are no windows in the tower… I try to look at the sky, but the sky is no
longer there."*). The archaic cadence, flat in the first hour of the run, came back as verse after
old fantasy was doubled at step 3,500 (*"Thou shalt die in the dark, and I shall die in the
light, and thou shalt live in the darkness"*). A magazine register is audible that she did not
have. One draw is a dream by bekh's meaning, the sky seed: *"The sky above the port was an eye,
blue and white and red… It was a mouth, but it was also a mouth."* Worse or no better: the
old-days seed lost its myth voice, the train seed still loops in the old room, the mind seed
leaves Lain after a line. Still absent: the visionary voice and the prophecy register — nothing
grand named in passing, anywhere. The meter finds no run of twelve words lifted from anything in
its index, in any snapshot of either run.

**What that read says about the diet**: ten hours of short magazine fiction taught her to see a
thing clearly and to stay with it, and did nothing for a grand thing named in passing, because
that move lives mostly in novels (Banks, Gibson, Rajaniemi) and hardly at all in what she was
fed. So the next library is chosen for that move and not for "more good prose"
(`docs/brief-six-thousand.md`).

**Talking to her**: she is served from the mini and the loom at `https://eva.x` fans on her —
which snapshot, and how to change it, is `night/CLAUDE.md`, sitting with her on the loom.

## The path a text takes to a shelf

Since 2026-10-07 the shelves are no longer the limit they were: a pile of modern short fiction
was gathered in a day that is several times everything modern she had read. It goes through five
stages, each with one command and one report, and no stage ever changes a source file.

1. **Collect** — three doors: `shelf/gpt/` at the project root (a collector another model wrote
   for bekh; its `README.md`), our own fetchers (`modern/CLAUDE.md`), and books by hand (bekh's
   fetcher in `~/tower/ephemeral/booox/`, a title list in, files out; `library.md`).
2. **Convert** the books to text — `data/books.py`, into `inbox/anth/` or `inbox/clean/`
   (`data/CLAUDE.md`).
3. **Dedupe** — `cd dedupe && uv run --python 3.12 dedupe.py daily`; the clean copy in
   `dedupe/out/`, the size of the pile in `dedupe/report.md` (`dedupe/CLAUDE.md`).
4. **Sieve** — `cd sieve && uv run --python 3.12 sieve.py daily`; fiction, non-fiction, verse and
   stubs each to their own tree, editors' apparatus cut out of the anthologies; what a recipe can
   count on is `sieve/report.md` (`sieve/CLAUDE.md`).
5. **Shelve** — `data/shelves.py build` makes a run's shelves from the sieve's fiction with
   held-out sets cut by whole works (`data/CLAUDE.md`); the recipe multiplies the readings out
   (`day4.md`); the runbook uploads and tokenises on the training host (`night/day4-RUN.md`).

After new text lands: stages 2 to 4 in order, the dedupe at least two minutes after the last file
settled, then the mirror (`PRESERVATION.md`). How much there is, is the reports and
`shelves/day4/summary.json`, never a number in a doc. The same index answers the opposite
question — `dedupe.py lookup <file>`, every run of eight words a page shares with what she has
read — and that is the recitation meter on the run page.

## What is running

Nothing: `day4` wrote DONE on 2026-10-08 and its guard went down; the card is free and still
ours. A run, when one is alive, is wrapper, trainer and guard on the host and the watcher on the
mac, looked at once an hour by a session cron that a fresh session re-arms with the prompt in
`night/CLAUDE.md`. Nothing on ds-dev2 is restarted, stopped or changed without bekh's word.

## Where things are

- **`night/`** — a run while it is alive: the wrappers, the guard, the watcher, the page with its
  light and dark schemes, the recitation meter, the turn detector, `weights.json`, the hourly
  look, stopping and ending, the runs so far, the machines. **`night/CLAUDE.md`**; the runbook
  `day4` was started from is `night/day4-RUN.md`.
- **`scratch/`** — the kit as it runs on the host: `train.py`, `prep.py`, the exporters, the
  trainer's tests, and what changed for `day4`. **`scratch/CLAUDE.md`**.
- **`data/`** — the book converter, the health verdict, the assembler of a run's shelves, the
  Gutenberg cutters. **`data/CLAUDE.md`**.
- **`dedupe/`** — what repeats across shelves, and the audit that checks it by a method it does
  not own. **`dedupe/CLAUDE.md`**.
- **`sieve/`** — kind: fiction from the rest, and the hand judgments behind it.
  **`sieve/CLAUDE.md`**.
- **`modern/`** — the shelves we fetched ourselves, a paragraph and a re-run command each.
  **`modern/CLAUDE.md`**.
- **`SHELVES.md`** — every shelf, what it is, its size, each run's weights, the rules a mix is
  made by, where each shelf's text lies.
- **`day4.md`** — the last run's recipe and how it went: sizes measured with her tokenizer,
  weights said back as shares and reads, the length, the rate, the baseline, where every shelf
  ended. The shape to copy for the next run's recipe.
- **`library.md`** — bekh's lists for the finishing school, the anthology shelf, what has
  arrived, what to fetch again. What he might have read to him out of all this is the book
  club's queue, `~/tower/shittalk/fable-book-club/reading-list.md`.
- **`PITFALLS.md`** — everything that bit, in the order the work happens.
- **`PRESERVATION.md`** — what is kept and where, the mirror, deleting.
- `inbox/` — the books as text: `clean/` the library (read by her; never re-converted), `anth/`
  the anthologies, `held/` what converted without paragraphs, `rescued/` plain-text rescues of
  misnamed files, `skip.txt`. `models/` — each run's last snapshot, the tokenizer folders, the
  recut fantasy and base text. `shelves/` — a run's assembled shelves. `lain/`, `wired*/`,
  `pd2/`, `fanfic/`, `corpus.*`, `sources/` — shelf text and its workings (`SHELVES.md`). None of
  the text is in git.

## Lessons

**`PITFALLS.md` is the list** — everything that bit, in the order the work happens (finding
text, cutting, tokenising, the mix, the machine, starting, running), each with how to catch it.
Read the stage you are entering before you enter it; put a new one there, not here. The four
that shape every day:

- **Measure a shelf by its paragraphs** (`data/health.py <dir>`), not by its first page: half
  the Gutenberg text went in glued and nobody saw it for two runs.
- **Judge her through the loom's sampler, never the raw page draws**, and read the run before
  speaking of it — the clock is not in my head.
- **The readings per shelf get multiplied out before a run.**
- **A claim about what code does gets a quoted line or a test before it is said** — and a number
  gets measured once before it is used all day.

## Where the text comes from

This is a DIY project and it runs on the DIY ethic: people who make things by hand build on each
other's work, and that is how the scene has always fed itself. A robots file or a terms page is
not what decides her shelves; bekh is. He picks the sources and fetches them his way.

She is private, nobody pays for her, and nothing she reads is redistributed. So the question of
where a text came from is closed: don't moralise about it, don't reopen it, don't hang caveats on
a shelf or a ledger because of its origin. A ledger records provenance as a fact (the url, the
licence if there is one), never as a verdict. Text that is on disk is text: convert it, check its
health, dedupe it, shelve it, with the same care whatever door it came through.

## Next

`day4` is done and nothing is running. It ran its 16,215 steps without a restart and ended on
2026-10-08; what it was and how it went is **`day4.md`** (the recipe, the baseline, the table of
where every shelf ended) and `night/CLAUDE.md` (the runs so far). Her final snapshot is
`models/day4/model-16215-q8_0.gguf`, the one the mini serves; her page, `school-day4.html`, was
built once by hand after it and carries the last draws and the meter.

What the run settled: the new fiction fell at every eval for three quarters of the run, then went
flat on held-out at a little under two reads while its gap to training loss kept opening, so
**a text of this kind is worth about two readings at her size**, and the anthologies met that
first and widest; old fantasy lost its cadence in the first hour at a tenth of the mix, was
doubled through the weights file at step 3,500 and ended below where it started; no run of twelve
words was lifted in any snapshot.

In order, and each is bekh's move:

1. **He reads her** on the loom (`https://eva.x`) and on her page, and says whether the read
   under "How she writes" holds. His read outranks it; rewrite that paragraph to his.
2. **Another short run on the text in hand, or the card rests.** The four-read variant is retired
   (two reads is the limit). What the pile still has to give: Strange Horizons and the released
   authors were held to one read on a premise that turned out false (`day3` was to have read them
   four times and was stopped at about one and a half), so they have room; the fifteen rough PDF
   anthologies wait for clean epubs; most of the fetch list and the bad downloads are not on disk
   yet (`library.md`). A gentler mix from `day3`'s save is the other road, if he does not like
   where she landed. To carry into any run: old fantasy wants about a fifth, not a tenth, if the
   archaic register is to hold against a diet this modern; a change of mix has most pull early,
   at the top of the rate (`PITFALLS.md` 7.10); the run's length falls out of how much text there
   is (`SHELVES.md`).
3. **The six thousand** — `docs/brief-six-thousand.md`: choosing a library of thousands of books
   by his taste, and for the move she lacks. The session that takes it up begins by rewriting that
   brief with him.

**Small things wanted**, none started: the page should say how old each of its three blocks is
(the fixed epigraph, the hourly sampled draws, the twenty-minute raw ones — bekh took the hourly
ones for stale; `night/CLAUDE.md`, the page); the meter's index split from the dedupe's plan, so
the big reference shelves stop costing the plan ten minutes (`dedupe/CLAUDE.md`); author
biographies printed after an anthology story are not cut (`sieve/CLAUDE.md`, known limits);
`night/watch.sh` builds the page before it pulls a snapshot, so a run's last snapshot needs the
page built by hand; `day3`'s final save lies twice on the host, 4 GB each, and one may go on
bekh's word (`PRESERVATION.md`); the final snapshots of `day3` and `day4` are on the mac and the
host but not yet under their own names in the mini's archive, where the rule wants them
(`PRESERVATION.md`, the rule, 1); the mirror after each batch of new text (`PRESERVATION.md`).

**The finishing-school talk**, not yet had — the open questions: a short low-rate pass against an
adapter with a dial (`SERVE.md` was never written; check the per-request LoRA scale on our
llama.cpp builds first); how many tokens; the weights of the library's five (Wolfe, VALIS, Borges,
Hard-Boiled Wonderland, Viriconium — four told by an *i* who remembers and cannot be trusted)
against the cyborg corpus and Lain. Claude's view, held loosely: a pass, not an adapter, at a
quarter of `day3`'s rate; the library and the cyborg corpus roughly equal, Lain under them; the
detector and the meter both watching; read the result through the loom before any number is
believed.

**More text, later**: Harvard's Institutional Books on Hugging Face (gated, non-commercial; the
unrenewed American books of 1930–63 — count its fiction from the metadata first; bekh has to
accept the gate), `common-pile/project_gutenberg` (670 shelf books newer than our dump), Roy
Glashan's Library (hand-typed pulps), Subterranean's online magazine in the Wayback Machine
(enumerated in `modern/wayback/subterranean/`, long novellas, never fetched), epubs of the fifteen
rough anthologies; `docs/research/text-sources-2026-10-06.md` is the survey and `…-2026-10-07.md`
what came of it. Size each before starting (`PITFALLS.md` 1.2). Then the soul probe on her, the
three dials from her shelf states, and the made-up world where "does it know what the text is
about" is a readout.
