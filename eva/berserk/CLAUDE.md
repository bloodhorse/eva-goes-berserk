# berserk — the loom walked by nobody

Nemo writes, nemo reads, bekh reads in the morning. `berserk.py` is the fourth stance of the
instrument in `../`: it makes rooms and artifacts with `loom.py` and streams through `eva.py`,
exactly as the page and the repl do, so everything it walks opens at `https://eva.x` and lands on
the shelf as the same artifact file a hand-made walk would. Read the root `CLAUDE.md` for what we
are hunting.

Nobody's taste is in the loop. At a fork the fan goes back to the same model as a **second
document** — the tail of the page, the branches under it as bare paragraphs in a fresh random
order, and one line: *the one that scared me was the one that began: “* — and the branch the
model quotes back is the branch the document continues on. Those dozen words are the whole human
contribution, they sit in one block at the top of `berserk.py`, and `--ask` is how you swap
"scared" for something else without editing the file. No numbers, no bullets, no brackets and no
quote marks go around a branch: a base model reads every one of those as web furniture and starts
answering the furniture.

**Every branch is shown with the lead on it.** A 35-token branch ends wherever it ends, so the
document nearly always stands mid-sentence and the branches under it open on punctuation — `.`,
`, as it was raining all month`, `, god help us all.` Ask which fragment *began* with something
and a model cannot answer with a comma, so it invents a beginning instead: that is how the first
real closing fan failed, four asks in a row. So the fragment shown is `lead + branch`, where the
lead is the document's unfinished last line, and the tail printed above the fan stops before it so
it is not shown twice. The fragment texts are built once, in `one_ask`, and the same list goes to
the reader, to the substring matcher and to opus — three copies of that string would be three
chances for them to disagree about what the reader was looking at.

The reader runs cool (t 0.7, min_p 0.05) and with **DRY and the repeat penalty off**. That is not
a tuning preference: the reader's entire job is to repeat a passage that is already in its
context, which is exactly what a repetition brake punishes. Turn them on and it paraphrases, a
paraphrase matches nothing, and every fork ends random. A second, warmer call asks it *why* that
one; the answer goes to the ledger and the morning file and is fed back into nothing.

## Turning a quotation into a branch

Two matchers, and the pick used is a flag:

- **substring** always runs: both sides casefolded and whitespace-collapsed, the shared lead
  taken off the front of both, score = longest common prefix over what remains, and 1.0 for a
  quotation sitting anywhere inside a fragment (the reader often starts a line or two in). A match
  needs 0.6, twelve characters and a unique best — a tie is no match, because two fragments
  sharing the quoted opening means the reader named something both of them do. A quotation that is
  **nothing but the lead** is that same non-choice: it fits every fragment by construction, and
  comes back as no match.
- **opus** (`--verify opus`, the default for now) is a **blind** matcher: `claude -p --model opus`
  is shown the quotation and the numbered openings, never the document, never a word about which
  branch is better, and answers `{"index": N}` or `{"index": null}`. Its answer is the one used
  while the machinery is being watched; the substring answer rides beside it and `agree` goes on
  the ledger. Opus failing twice or answering null falls back to substring.
- `--verify none` calls nothing outside llama. `--verify embed` exits saying it isn't built: that
  is the seat opus is keeping warm, because "where did this sentence come from" is a similarity
  question and not a judgement.

## The shape of a run

A **cycle** is five **pages**. A page is one walk: a seed from `shelf/seeds/` (rotated by cycle so
two nights don't open on the same one) becomes a bare room named `berserk-cNN-pNN`, then fifteen
**forks** of fifteen branches at ~35 tokens each, temperatures stepped over 1.4–2.4 with xtc on —
the levers of `cli/walk/walk.py`, unchanged so the fans stay comparable with every walk already on
the shelf. The page ends on a **closing fan** nobody continues from: the quoted branch is *kept*
instead of taken, which is the fan the room is standing on when `loom.build_artifact` freezes it,
so the artifact is shaped like one saved by hand from the page. The walk goes up to the sheets
site as html (`~/sheets/berserk/<room>.html` on the mini), a push lands on the phone, and
`shelf/berserk/cycles/cNN.md` is the report bekh opens in the morning: the settings and the ask,
a table per page (bits, forks, matched, widened, random, how often opus and substring agreed),
then every fork as `“quote” — why`, then **the wished pile**.

The quotation and the why ride on the chosen node's `meta.berserk` with `used`, so a fork is
readable at eva.x months later without the ledger open beside it.

## What it refuses to die of

The interesting failure is not a bad pick, it is a reader that quotes a branch that was never
drawn. Three asks, each with the fan shuffled again (shuffled because a base model has a position
bias, so a retry on the same order is not a second opinion); then the fan is **widened once** —
fifteen more branches under the same node, which is cheaper than an arbitrary line — and asked
once more; then a random branch, `outcome: "random"`, `reader_failed: true`, and the walk goes on.
Every quotation that matched nothing is kept on the ledger under `wished` and collected at the
bottom of the report, because **a branch described and not drawn is the most interesting thing
this machine makes**.

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

- `shelf/berserk/ledger.jsonl` — a line per fork (`cycle page room fork closing fan_size attempts
  widened order quote why substring opus agree used outcome pick keep bits seconds reader_failed
  wished`, where `order` is the shuffled branch ids exactly as the reader saw them and `pick` and
  `keep` are ids in it), a `page` event per page, a `cycle` event per cycle.
- `shelf/berserk/heartbeat` — one json object rewritten every branch, temp-then-replace.
- `shelf/berserk/state.json` — the run, gone on a clean exit.
- `shelf/berserk/pages/` — the html copies pushed to sheets (gitignored: the artifact is in git).
- `shelf/berserk/cycles/cNN.md` — tracked.
- `/tmp/eva-berserk.log` — stderr, stamped, from launchd.

```bash
launchctl kickstart gui/$(id -u)/com.bekh.eva-berserk                 # one cycle, five pages
uv run --python 3.12 eva/berserk/berserk.py page --cycle 9 --page 1   # one page by hand
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
`READER_MODE` — `"quote"` answers an ask with the first fourteen words of one of the fragments in
its own prompt, `"garbage"` answers a sentence that is in no branch. Without it a stub would only
ever exercise the failure path, since berserk's reader is asked for a quotation and not for a
line. Fourteen and not eight because a fragment opens on the lead, and a quotation short enough
to be nothing but the lead matches every fragment and therefore none.

It checks the lead by hand on the first closing fan's own openings — that it is the unfinished
last line, that it is shown once per fragment and not above them as well, that a fragment is
matched through it and that quoting the lead alone is no match — and then, end to end: the room
stands on the seed, the quote and `used` and the shuffled `order` land on every
ledger row, the artifact is a walk of `forks+1` steps that reads as the document, the closing fan
keeps exactly one and takes nothing, the reader's request really went out with `dry_multiplier 0`,
`repeat_penalty 1.0` and xtc off, the matcher's prompt held the quotation and **not** the document,
opus and substring agree, `--verify none` never starts `claude` at all (the fake writes a file the
moment it runs, and that file must not exist), a matcher answering prose falls back to substring, a
reader that never matches widens once per fork and finishes the cycle with a full wished pile, the
report names the page and the quotes, state is gone and the heartbeat remains, and a second run
refuses the same room. Sheets host and ntfy are the empty string there: a test run must never scp
to the mini or push to bekh's phone.

## State

Built and green against the fakes (2026-09-16), and three single-fork pages have run against real
nemo on the `relay-roll` seed. Before the lead, the closing fan failed four asks in a row and kept
a random branch; **with** the lead it matched in both runs since — once at score 1.0 on
`the boy joshua, nine years,` (*"i knew i'd seen him before, on a list of the disappeared"*), once
through opus on `she cannot stop walking,`. The first fork of that seed went random in both, and
for a reason worth knowing: `relay-roll` ends `…for this the parish\ncalled her the`, so the lead
is a three-word sentence fragment, which still does not read as a *beginning* — the reader answers
with invented sentence-openings (`the witches of the marsh`, `there was a girl.`) instead of
quoting. The fix helped the long lead and not the short one.

The one real opus call on the ledger **disagreed** with the substring matcher and was used:
opus said fragment 0, substring scored 0.167 and refused, `agree: false`. Opus matched on sense —
a woman who cannot stop walking against a branch ending *"she will look you straight in the face
and answer, without stopping"* — where the letter was not there. That is the behaviour to watch
when the embedding model takes the seat, because it will be looser still.

**No real cycle has run yet** — `shelf/berserk/cycles/` is empty and the monitor says "never run
here". The first one is the next thing: kickstart it in the evening with llama up, read
`cycles/c01.md` in the morning, and read the wished pile before the walks — a reader that keeps
describing branches nobody drew is telling us more about the ask line than the walks are.
