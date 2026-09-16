# berserk — the loom walked by nobody

Nemo writes, opus picks, bekh reads in the morning. `berserk.py` is the fourth stance of the
instrument in `../`: it makes rooms and artifacts with `loom.py` and streams through `eva.py`,
exactly as the page and the repl do, so everything it walks opens at `https://eva.x` and lands on
the shelf as the same artifact file a hand-made walk would. Read the root `CLAUDE.md` for what we
are hunting; read `picker.md` for how the reader is told to hunt it.

## The shape of a run

A **cycle** is five **pages** and a **review**. A page is one walk: a seed from `shelf/seeds/`
(rotated by cycle so two nights don't open on the same one) becomes a bare room named
`berserk-cNN-pNN`, then fifteen **forks** of fifteen branches at ~35 tokens each, temperatures
stepped over 1.4–2.4 with xtc on — the levers of `cli/walk/walk.py`, unchanged so the fans stay
comparable with every walk already on the shelf. At every fork `claude -p --model opus`, tools
off, reads the fan against `picker.md` and answers json: `genre`, `pick`, `keep`, `note`. The page
ends on a **closing fan** nobody picks from, only keeps 1–3 endings — which is the fan the room is
standing on when `loom.build_artifact` freezes it, so the artifact is shaped like one saved from
the page. The walk goes up to the sheets site as html (`~/sheets/berserk/<room>.html` on the
mini), a push lands on the phone, and after the fifth page the same reader sees all five documents
whole with their fork notes and says which are **notable**; those get a second copy at the root of
the sheets folder, and `shelf/berserk/cycles/cNN.md` is the report bekh opens in the morning.

Opus is a **sieve, not an author**: nothing it writes enters the document, its genre and note ride
on the chosen node's `meta.berserk` so a fork is readable at eva.x months later. The daemon's only
opinions are structural — branch length, fan width, where the document ends. bekh's notes for a
cycle (`shelf/berserk/notes/cNN.md`, or `--notes <file>`) are appended under the rulebook and
override it where they disagree.

## What it refuses to die of

The interesting failure is not a bad pick, it is a reader that answers prose at 4am. A failed
parse costs one re-ask with the complaint attached; two failures take a random branch, mark the
ledger line `picker_failed: true`, and the walk goes on. A fan that comes back with fewer than two
branches is drawn once more (a 502 from a warm llama is usually a reload), then the page aborts
and the cycle moves to the next one. An artifact name already on the shelf is a 409 and the page
is posted anyway — never an overwrite; a room name already on the shelf stops the page before it
starts. The mini being asleep loses nothing: scp is never fatal, the ledger says `posted: false`.
The picker runs with `cwd` in a temp dir and `CLAUDECODE` stripped from the env, so this repo's
`CLAUDE.md` is not loaded into a reader asked one question about a fan, and a berserk started
from inside a claude session still gets to start one.

## Observable on purpose

It runs for hours with nobody watching, so it keeps a ledger and a heartbeat, and `monitor.py`
only reads them — three signals kept apart: the probe (spinner and clock: the monitor itself is
polling), alive (the heartbeat's age: mint under 3 min, light blue under 10 — one picker call can
be minutes), progressing (the last fork line on the ledger: alive-but-stuck looks nothing like
dead). `state.json` holds the run's pid and is removed on a clean exit only; present with a pid
nobody answers to is the one state that needs a human.

- `shelf/berserk/ledger.jsonl` — a line per fork (`cycle page room fork fan_size pick keep genre
  note picker_failed bits seconds`), a `page` event per page, a `cycle` event per review.
- `shelf/berserk/heartbeat` — one json object rewritten every branch, temp-then-replace.
- `shelf/berserk/state.json` — the run, gone on a clean exit.
- `shelf/berserk/pages/` — the html copies pushed to sheets (gitignored: the artifact is in git).
- `shelf/berserk/cycles/cNN.md`, `shelf/berserk/notes/cNN.md` — tracked.
- `/tmp/eva-berserk.log` — stderr, stamped, from launchd.

```bash
launchctl kickstart gui/$(id -u)/com.bekh.eva-berserk                 # one cycle (five pages + review)
uv run --python 3.12 eva/berserk/berserk.py page --cycle 9 --page 1   # one page by hand, a smoke test
uv run --python 3.12 eva/berserk/berserk.py review --cycle 9          # the review alone, off the ledger
uv run --python 3.12 eva/berserk/monitor.py                           # the dashboard; --once for a frame
```

The agent `com.bekh.eva-berserk` does not run at load and has no KeepAlive: a cycle is a thing you
start. It needs `com.bekh.eva-llama` up, not the loom. Its PATH carries `~/.local/bin` (where
`claude` is) and HOME is set, or the picker fails on every fork and the whole cycle walks itself
at random. Env: `BERSERK_DIR` (default `shelf/berserk/`), `BERSERK_SEEDS` (`shelf/seeds/`),
`BERSERK_SHEETS_HOST` (empty string = post nowhere), `BERSERK_SSH_KEY`, `BERSERK_NTFY` (empty =
no push), plus loom's `LOOM_SITTINGS` / `LOOM_ARTIFACTS` / `LOOM_LLAMA`.

## Tests

`../tests/berserktest.py` runs a real `berserk.py` as a subprocess against the stub llama and a
**fake `claude`** — a three-line script put first on PATH that reads the prompt off stdin, files
it away, and prints the json the rulebook asks for. That is the seam worth faking. It checks the
room stands on the seed, kept flags land, the artifact is a walk of the right number of steps and
reads as the document, the html page holds the escaped text, the ledger has its lines, the report
names the page, state is gone and the heartbeat remains, the picker really saw the rulebook and
the document, a second run refuses the same room, and a picker that never answers json still
completes the cycle with every fork marked. Sheets host and ntfy are the empty string there: a
test run must never scp to the mini or push to bekh's phone.

## State

Built and green against the fakes (2026-09-16); **no real cycle has run yet** — `shelf/berserk/`
has empty `cycles/` and `notes/`, and the monitor says "never run here". The first real cycle is
the next thing: kickstart it in the evening with llama up, read `cycles/c01.md` in the morning,
and judge the picker's genre names against the fans at eva.x before trusting a single "notable".
