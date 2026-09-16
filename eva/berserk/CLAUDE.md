# berserk — the loom walked by nobody

Nemo writes, nemo reads, bekh reads in the morning. `berserk.py` is the fourth stance of the
instrument in `../`: it makes rooms and artifacts with `loom.py` and streams through `eva.py`,
exactly as the page and the repl do, so everything it walks opens at `https://eva.x` and lands on
the shelf as the same artifact file a hand-made walk would. Read the root `CLAUDE.md` for what we
are hunting.

Nobody's taste is in the loop. At a fork the same model is asked which branch it means, and the
branch it names is the branch the document continues on. The frame lines that ask it are the
whole human contribution: they sit in one block at the top of `berserk.py`, and `--ask` swaps
the line without editing the file. No numbers, no bullets, no brackets and no quote marks go
around a branch anywhere in any of this: a base model reads every one of those as web furniture
and starts answering the furniture.

## The three pickers

`--picker` decides how the question is put, and which one finds anything is **open** — bekh
settles it by reading pages, not by argument.

- **about** (the default) — the fan goes back as a **second document**: the tail of the page,
  every branch under it as a bare paragraph in a fresh random order, and one line — *the one
  that scared me was about*. The answer is a **description**, so there is nothing to match
  letter for letter and the resolver has to say which branch is being described. One call per
  fork.
- **margin** — no reader of the fan at all. One short note per branch, each written with only
  that branch in front of the model (*reading this, what scared me was*), and then one blind
  pick over the notes alone. n calls instead of one, and no branch can lose for sitting
  eleventh in a list of fifteen. Every note is kept on the ledger whichever one is picked.
- **quote** — the fan as one document again, answered by **quoting** a branch back (*…was the
  one that began: “*). The only form whose answer can be checked against the text with no
  judgement anywhere in the loop, which is why it survives as the control.

**Every branch is shown with the lead on it, in all three.** A 35-token branch ends wherever it
ends, so the document nearly always stands mid-sentence and the branches under it open on
punctuation — `.`, `, as it was raining all month`, `, god help us all.` Ask which fragment
*began* with something and a model cannot answer with a comma, so it invents a beginning instead:
that is how the first real closing fan failed, four asks in a row. So the fragment shown is
`lead + branch`, where the lead is the document's unfinished last line, and the tail printed above
it stops before it so it is not shown twice. The fragment texts are built once per fork, and the
same list goes to the reader, to the substring matcher and to opus — three copies of that string
would be three chances for them to disagree about what the reader was looking at.

The reader runs cool (t 0.7, min_p 0.05) and with **DRY and the repeat penalty off**. That is not
a tuning preference: a reader's job is to say back something that is already in its context, which
is exactly what a repetition brake punishes. Turn them on and it paraphrases, a paraphrase matches
nothing, and every fork ends random. The margin note is the one call that really is writing, so it
runs at 1.0 — and so does the second, warmer call that asks about/quote *why* that one; the why
goes to the ledger and the morning file and is fed back into nothing. Margin has no why: the note
is already the reason.

## Turning what was said into a branch

Two matchers, and the pick used is a flag:

- **substring** always runs: both sides casefolded and whitespace-collapsed, the shared lead
  taken off the front of both, score = longest common prefix over what remains, and 1.0 for a
  quotation sitting anywhere inside a fragment (the reader often starts a line or two in). A match
  needs 0.6, twelve characters and a unique best — a tie is no match, because two fragments
  sharing the quoted opening means the reader named something both of them do. A quotation that is
  **nothing but the lead** is that same non-choice: it fits every fragment by construction, and
  comes back as no match.
  Under **about** it will mostly say nothing at all — a description is not in the text it
  describes — and that is the expected reading, not a fault: it is there as the witness, logged
  beside opus so the two can be compared later. Margin has no substring matcher: there is nothing
  to match a note against.
- **opus** (`--verify opus`, the default) is **blind**: `claude -p --model opus` is shown what the
  reader said and the numbered openings — or, under margin, the numbered notes and nothing else —
  never the document, never a word about which branch is better, and answers `{"index": N}` or
  `{"index": null}`. Its answer is the one used; the substring answer rides beside it and `agree`
  goes on the ledger. Opus failing twice or answering null falls back to substring.
- `--verify none` calls nothing outside llama: about and quote walk on the substring answer,
  **margin takes a random branch** and logs every note, with a line in the log saying so.
  Inventing a heuristic there ("the longest note", "the most adjectives") would be smuggling in a
  taste nobody chose. `--verify embed` exits saying it isn't built: that is the seat opus is
  keeping warm, because "which one is this" is a similarity question and not a judgement.

## The shape of a run

A **cycle** is five **pages**. A page is one walk: a seed from `shelf/seeds/` (rotated by cycle so
two nights don't open on the same one) becomes a bare room named `berserk-cNN-pNN`, then fifteen
**forks** of fifteen branches at ~35 tokens each, temperatures stepped over 1.4–2.4 with xtc on —
the levers of `cli/walk/walk.py`, unchanged so the fans stay comparable with every walk already on
the shelf. The page ends on a **closing fan** nobody continues from: the quoted branch is *kept*
instead of taken, which is the fan the room is standing on when `loom.build_artifact` freezes it,
so the artifact is shaped like one saved by hand from the page. The walk goes up to the sheets
site as html (`~/sheets/berserk/<room>.html` on the mini), a push lands on the phone, and
`shelf/berserk/cycles/cNN.md` is the report bekh opens in the morning: the settings (the picker
among them) and the ask, a table per page (bits, forks, matched, widened, random, how often opus
and substring agreed), then every fork in whatever the picker said — a quotation in quote marks,
a description in none, a margin note on its own — and then **the wished pile**, which only the
pickers that read the whole fan have.

What the picker said rides on the chosen node's `meta.berserk` with `used`, so a fork is
readable at eva.x months later without the ledger open beside it.

## What it refuses to die of

The interesting failure is not a bad pick, it is a reader that names a branch that was never
drawn. Under about and quote: three asks, each with the fan shuffled again (shuffled because a
base model has a position bias, so a retry on the same order is not a second opinion); then the
fan is **widened once** — fifteen more branches under the same node, which is cheaper than an
arbitrary line — and asked once more; then a random branch, `outcome: "random"`,
`reader_failed: true`, and the walk goes on. Every answer that resolved to nothing is kept on the
ledger under `wished` and collected at the bottom of the report, because **a branch described and
not drawn is the most interesting thing this machine makes**. Margin has none of that: its notes
are written once against the branches that exist, so there is nothing to reroll and nothing to
wish for — either the resolver picks a note or the branch is chance.

A fan that comes back with fewer than two branches is drawn once more (a 502 from a warm llama is
usually a reload), then the page aborts and the cycle moves to the next one. An artifact name
already on the shelf is a 409 and the page is posted anyway — never an overwrite; a room name
already on the shelf stops the page before it starts. The mini being asleep loses nothing: scp is
never fatal, the ledger says `posted: false`. The matcher runs with `cwd` in a temp dir and
`CLAUDECODE` stripped from the env, so this repo's `CLAUDE.md` is not loaded into a reader asked
one question about a quotation, and a berserk started from inside a claude session still starts.

## Observable on purpose

It runs for hours with nobody watching, so it keeps a ledger and a heartbeat, and `monitor.py`
only reads them — three signals kept apart: the probe (spinner and clock: the monitor itself is
polling), alive (the heartbeat's age: mint under 3 min, light blue under 10 — one matcher call can
be minutes), progressing (the last fork line on the ledger: alive-but-stuck looks nothing like
dead). `state.json` holds the run's pid and is removed on a clean exit only; present with a pid
nobody answers to is the one state that needs a human. It shows the last fork's quotation and
which matcher was used, and counts `reader_failed` as reader failures.

- `shelf/berserk/ledger.jsonl` — a line per fork (`cycle page room fork picker closing fan_size
  attempts widened order quote why substring opus agree used outcome pick keep bits seconds
  reader_failed wished`, where `order` is the branch ids exactly as the reader saw them — shuffled
  under about and quote, fan order under margin — and `pick` and `keep` are ids in it; margin adds
  `notes`, one per branch in that same order, and `pick_note`, which note the branch taken
  carried), a `page` event per page, a `cycle` event per cycle.
- `shelf/berserk/heartbeat` — one json object rewritten every branch, temp-then-replace.
- `shelf/berserk/state.json` — the run, gone on a clean exit.
- `shelf/berserk/pages/` — the html copies pushed to sheets (gitignored: the artifact is in git).
- `shelf/berserk/cycles/cNN.md` — tracked.
- `/tmp/eva-berserk.log` — stderr, stamped, from launchd.

```bash
launchctl kickstart gui/$(id -u)/com.bekh.eva-berserk                 # one cycle, five pages
uv run --python 3.12 eva/berserk/berserk.py page --cycle 9 --page 1   # one page by hand
uv run --python 3.12 eva/berserk/berserk.py cycle --cycle 9 --pages 2 --forks 5 --fan 5 --picker margin
uv run --python 3.12 eva/berserk/berserk.py page --cycle 9 --forks 1 --fan 8 --verify none
uv run --python 3.12 eva/berserk/monitor.py                           # the dashboard; --once for a frame
```

The agent `com.bekh.eva-berserk` does not run at load and has no KeepAlive: a cycle is a thing you
start. It needs `com.bekh.eva-llama` up, not the loom. Its PATH carries `~/.local/bin` (where
`claude` is) and HOME is set, or the blind matcher fails on every fork — which now costs the walk
nothing but a fallback to substring. Env: `BERSERK_DIR` (default `shelf/berserk/`), `BERSERK_SEEDS`
(`shelf/seeds/`), `BERSERK_SHEETS_HOST` (empty string = post nowhere), `BERSERK_SSH_KEY`,
`BERSERK_NTFY` (empty = no push), plus loom's `LOOM_SITTINGS` / `LOOM_ARTIFACTS` / `LOOM_LLAMA`.

## Tests

`../tests/berserktest.py` runs a real `berserk.py` as a subprocess against the stub llama and a
**fake `claude`** put first on PATH. The stub grew the seam that makes this testable at all:
`READER_MODE`. It answers by the shape of the prompt's last line, which is all a markerless
reader document has: the quote ask gets the first fourteen words of a fragment (fourteen and not
eight because a fragment opens on the lead, and a quotation short enough to be nothing but the
lead matches every fragment and therefore none), the about ask gets ten words of a fragment
*minus its first word* — a description, not a quotation, so the resolver has to do the work — and
a margin ask gets a note naming that fragment's third word, which is the first word that differs
between branches. `"garbage"` answers a sentence that is in no branch. Without the seam a stub
would only ever exercise the failure path.

One class per picker, because they fail differently. It checks the lead by hand on the first
closing fan's own openings — that it is the unfinished last line, that it is shown once per
fragment and not above them as well, that a fragment is matched through it and that quoting the
lead alone is no match. Then, end to end: the room stands on the seed; the answer and `used` and
the `order` land on every ledger row; **about** resolves through opus and takes the branch that
really does share the most words with the description, and its resolver prompt says "describing"
and holds no document; **margin** writes one note per branch, hands the resolver the notes and
nothing else (no document, no branches), takes the branch under the note it picked, and with
`--verify none` goes random while keeping every note; **quote** matches letter for letter, and
opus and substring agree. Plus: the artifact is a walk of `forks+1` steps that reads as the
document, the closing fan keeps exactly one and takes nothing, the reader's request really went
out with `dry_multiplier 0`, `repeat_penalty 1.0` and xtc off, `--verify none` never starts
`claude` at all (the fake writes a file the moment it runs, and that file must not exist), a
resolver answering prose falls back to substring, a reader that never resolves widens once per
fork and finishes the cycle with a full wished pile, the report prints each picker's answer in its
own shape, state is gone and the heartbeat remains, and a second run refuses the same room. Sheets
host and ntfy are the empty string there: a test run must never scp to the mini or push to bekh's
phone.

## State

Built and green against the fakes (2026-09-16). **Two real cycles have run, on purpose, to be
compared** — `c80.md` (about) and `c81.md` (margin), two pages each, five forks of five branches,
both `--verify opus`, both on the sheets site. The numbers: about, 10 of 12 forks resolved, 2
random, **23 wished-for lines**, opus and substring agreed **0 of 10** (expected — a description
is not in the text it describes); margin, 12 of 12 resolved, none random, nothing wished for,
one attempt each, ~25s a fork against about's 35–60.

What the pages actually show, which is the part that decides this:

- **about** picks like half a choice. When it lands it lands hard — a description of *the "fresh
  air for fresh men." the hospital* took the branch that says *the back page about "fresh air for
  fresh men" as it applied* — and when it misses it takes a branch with nothing to do with what it
  said. It has one structural virtue nobody designed: **it never picked a thin branch.** All
  twelve picks ran 145–193 characters, because a description cannot describe an empty branch, so
  the empty ones cannot win.
- **margin** writes the best prose in the whole machine and then picks badly. The notes are real
  reactions — *the word "adjudged" — as if it was some kind of*, *that it sounded like my wife, as
  I do not have a* — and they are worth reading on their own. But the note is written about the
  **lead and the document**, not about what the branch adds, so an empty branch gets a note as
  full as any other: 3 of 12 picks were branches of zero characters and 4 more were wiki footers
  (*Unless otherwise stated, the content of this page is licensed…*). The resolver was asked for
  the most pronounced reaction and got it; the reaction just was not about the branch.

The other half of that: `berserk-c81-p02` drew 18 of its 30 branches under 25 characters, because
the document had already drifted onto a web page and nemo had nothing to add there. Margin does
not defend against that drift; about does, by accident.

Also on the record, from the earlier single-fork smokes: the **lead** fixed the closing fan that
had failed four asks in a row, and a real opus call once overruled the substring matcher on sense
(*she cannot stop walking,* against a branch ending *"she will look you straight in the face and
answer, without stopping"*), which is the looseness to watch when the embedding model takes the
seat. And the **why call loops** — DRY is off for it too, and it comes back *what if i died? what
if i died? what if i died?* The brakes-off rule is about the reading call; the why is writing and
should probably get its brakes back.

Next is bekh's call, not the machine's: read the four pages, decide whether either picker is
choosing, and — if margin's notes are the prize — whether the note should be written about the
*branch alone* rather than the branch under the whole document.
