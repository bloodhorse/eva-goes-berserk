# stream — the machine dreaming with nobody there

One short passage every five minutes, written by nemo, picked by nobody. bekh opens his phone at
a random moment, reads down from the newest into the night, marks what moved him, puts the
phone down. That is the whole instrument, and it is the brief's mission taken literally: *a
dream machine that runs on the mac perpetually and writes dreams on its own… he won't read
everything; the point is knowing the machine is dreaming and looking in from time to time.*

The loom is the lab bench and this is not it. No fan, no picker, no resolver, no reader in the
loop. The only choices made here are made by lot — which seed, which heat — and the only hand
that ever touches a page is bekh's mark on it afterwards, which acts on the **next** page's
seed and never on generation. Read the root `CLAUDE.md` for what we are hunting and `BRIEF.md`
for why picking is not where the hunt is.

`stream.py` writes, `interpreter.py` reads what was written and marks it up, `monitor.py`
watches both, two plists are the clock, and the page is `../front/stream.html`, served by the
loom at `/stream`.

## The calls, and what breaks if each one goes

- **One page, one process; launchd is the loop.** `stream.py --once` writes one page and exits;
  the plist's `StartInterval` of 300 fires it again. A `while True` with a sleep in it would
  have to survive a closed lid, a lost GPU and a reboot — launchd already knows how. Take this
  out and a crash becomes a dead stream instead of one missing page.
- **A failed run is a ledger line and exit 0.** llama down, no seed, an empty answer: a row, a
  heartbeat, exit 0. launchd backs a job off when it exits non-zero, so a stream that punished
  itself for a busy GPU would stop dreaming quietly and nothing would say so.
- **A page is a room.** Bare room (no header, no speaker names, no stop strings), root = the
  seed verbatim, one model node = the page, filed at `stream/<YYYY-MM-DD>/<HHMM>`. It is a room
  and not a new file format so that everything already built reads it: the loom opens it, a whole
  day opens as one picture at `https://eva.x/#canvas=stream/<date>`, and the marks are the same
  `/api/mark` the canvas uses. A day is a folder because the names are timestamps and sort
  chronologically — which is what lets `/api/stream` page backwards without opening a file.
  A name taken (a hand run inside the timer's minute) gets `-2`.
- **`meta.logprobs` is flat, and `probs` is never written.** One number per token — the chosen
  token's logprob — reduced before the room hits the disk. The other stances keep llama's full
  tables, which are ~300 KB a room; 288 rooms a day of those would be a gigabyte a week. The
  flat list is still enough for the one thing anything here wants off them, the surprise curve.
  `n_probs: 1` is the minimum that makes llama answer with probabilities at all.
- **Seeds by lot, two pots, a weighted coin.** A starred tail weighs what one seed weighs,
  capped at half the draws: p(pot B) = min(0.5, |B| / (|A| + |B|)). A flat fair coin would let
  the *first* star seed 144 pages a day from the same 600 characters — stasis on day one; no
  cap would let a month of stars crowd the shelf's seeds out. Pot A is every `.txt` under `shelf/seeds/`,
  recursively, skipping anything over ~12k characters (measured in bytes, which can only
  over-count — the error is on the side of skipping, never of a prompt llama silently truncates
  the front off). Pot B is the tails of pages bekh **starred**: seed plus page, the last ~600
  characters, cut forward to a sentence start and back to a sentence end. Pot B is what makes
  this a machine rather than a shuffle, and `kept` rather than `good` on purpose — the circle
  means "i wouldn't keep it", and feeding it back would drift the stream toward the merely nice.
  Empty pot B = pot A. The seed's identity (`seeds/short/x.txt` or `tail:<room>`) is on the node
  and on the ledger row.
- **Trailing spaces and tabs are stripped from the very end of a seed, newlines are not.** A
  document ending on a space makes the next token a numeral, measured 2026-09-16. A seed that
  ends on a newline means it.
- **Temperature by lot in [1.8, 2.5]**, min_p 0.08, top_k 0, top_p 1.0, repeat_penalty 1.05,
  repeat_last_n 512, n_predict **170**, no stop strings — the wire rooms' sampler. 170 and not
  the 350 it shipped with: bekh cut it on 2026-09-19 after reading the first live ones — they
  felt long to him, and what he pictures is half a page, a separator, the next passage, on and
  on. (A side effect, not his reason: a genre locks in over length, so a shorter passage spends
  less of itself on furniture.) `N_PREDICT` in `stream.py` is the only place it is
  written — the plist sets no override. 1.0 is nemo's
  default and shows nothing; this build applies temperature LAST, so min_p cuts the absurd tail
  before the heat flattens what survived, which is why 2.5 is still a sentence. Everything not
  named is eva's room default, DRY above all: base models loop, and a hot page with no brake on
  repetition is one sentence said nine times.
- **The filter is a column, not a knife.** `FILTERS` in `stream.py` — urls, html, markdown
  headers and links, bylines, blog chrome, `chapter N`, copyright, bracket tags, @handles,
  hashtags. A page that trips one is **written to the shelf like any other** with
  `meta.flag = "<rule>"`; the reader hides it, `?all=1` shows it with a `filtered: <rule>` line.
  The list is one obvious place on purpose and is **audited against bekh's marks later** — how
  many pages he marked did it flag? — so false positives cost one page behind a query string
  and are expected.
- **Ledger and heartbeat, berserk's shapes.** `shelf/stream/ledger.jsonl`, a row per run (ts,
  room, seed, temperature, tokens, tps, flag, seconds — or `error` and a null room);
  `shelf/stream/heartbeat.json`, rewritten every run with `ts`, `last_ok`, `room`, `ok`.
  `last_ok` survives a failed run, or one unreachable llama would look like a stream that never
  ran.
- **Additive routes only.** `GET /stream` serves the page, `GET /api/stream` serves the pages
  and the status. Marks go through the **existing** `/api/mark` — a second mark route would be
  a second place the at-most-one rule lives.
- **The reader is phone-first**, which is the one place this project's "the page is a desktop
  page" law does not apply: that law is about the loom. No model name, no sampler, no seed name
  — a reader who can see the temperature is reading an experiment and not a dream.
- **The reader is one continuous scroll, newest at the top.** Passage, thin rule, passage;
  scrolling down goes back into the night and an IntersectionObserver near the bottom lazy-loads
  the next batch through `?before=<room>&n=`, stopping for good when `more` is false. It was a
  pager for a day — one passage, older/newer buttons — and that was wrong: a pager makes him
  **ask** for each passage, and the point is that the machine is already dreaming and he is
  looking in. Each passage shows the seed whole in the quiet tone, then the model's text, then
  its own `○/●` `☆/★` and a quiet time at its foot. The status line stays pinned.
- **Ragged ends are trimmed in the DISPLAY only.** A hard stop at 170 tokens lands mid-sentence
  nine times in ten, so the page cuts the model's text back to the last `[.!?…]` plus whatever
  closes over it — unless that would drop more than ~40% of it, or there is no sentence end at
  all, in which case it is shown whole. In the page's js and never in the api, because the raw
  text is the evidence of what nemo wrote: `?raw=1` is the same request with the trim off.
- **New passages never move the text.** The 60s poll prepends in place when he is at the very
  top; when he is scrolled down they are **held back** and only a quiet `new` appears in the
  status line, which scrolls up and drops them in when tapped.
- **The look is a placeholder.** The loom's palette, a thin rule, nothing else. Its own job.
- **The mac serves it, and nothing else does.** There is no mirror fallback: when the mac is
  off there is no stream, by decision (bekh, 2026-09-19).

## The interpreter — a second voice beside the stream

The stream is verbose, so bekh wanted it **anchored by a reader**: somebody who takes the dreams
seriously, is keen on reflections and symbols, is lucid and calm about the process and is *in
the game*, who writes a short reading of each small stretch and **underlines**, inside the
passages, what touched him. A reading every **two** passages for now — his words: to be more
exposed to it while testing.

`interpreter.py` is that reader: Claude Opus through the cli, headless, one call per run, the
same invocation `berserk.py` uses (`claude -p --model opus`, prompt on **stdin**, no tools,
`cwd` in a temp dir, `CLAUDECODE` out of the env so this repo's `CLAUDE.md` is not loaded in
front of a dream). One-shot like the worker, its own agent on the same 300s clock, and most
runs find fewer than two new passages and exit having done nothing.

- **The persona is `interpreter.txt`, bekh's file.** The code reads it and never writes it.
  Everything appended after it — the output shape, the memory, the material — is plumbing he
  should not have to see in his prompt, which is the whole reason for the split.
- **Tags, not json**: `<reading>…</reading>` then `<passage n="1">…</passage>` per passage,
  because the answer is full of `<mark>` and a tag inside a json string is an escaping question
  nobody needs to get right at 3am. Parsed leniently — a reading with no passages is still a
  reading.
- **The newest EVERY, never a backlog.** Each run takes the newest unflagged passages above the
  watermark (the newest room any reading has covered) and only if there are `EVERY` of them.
  If it was down for an hour, the twelve passages it missed stay unread: the stream is
  disposable and a reading of an hour-old stretch is not what the page is for.
- **Its memory is its own last four readings**, in the prompt, oldest first. Nothing else
  carries from one call to the next.
- **No checker, by decision (bekh, 2026-09-19).** Its copy of the dream is stored verbatim,
  tags and all, and is never corrected — *a mistake in the copy is another prophecy*. The room
  on the shelf is never written to by this process.
- **His slips are shown, in red.** A word diff runs once at write time between the raw dream
  and his copy with the tags stripped, and is stored as render-ready segments: `new` for words
  that are his and not the machine's, `gone` for the machine's words he dropped, shown struck
  through where they were dropped, his underlines riding on top of either. Words and not
  characters — a character diff of prose is unreadable — and whitespace tokens all compare
  equal, so reflowing a paragraph is not a slip. `new`/`gone` counts go on the ledger row, so a
  month of them says how faithfully he re-types.
- **The page renders every segment through `textContent`.** Only `<mark>` was ever read as a
  tag, and that was done here; anything else he typed, `<script>` included, arrives as
  characters and leaves as characters.
- **The `marks` toggle is the comparison.** On by default, remembered in `localStorage` inside a
  try/catch; off shows the raw dream exactly as the shelf holds it. Readings are always shown —
  an inset above their block on a phone, a right-hand column top-aligned with the block's head
  at ≥900px, the same node either way.

Storage, all under the gitignored `shelf/stream/`:
`readings/<YYYY-MM-DD>/<HHMM>.json` = `{ts, rooms (newest first), reading, marked, segments,
model, seconds}`, and one `kind: "reading"` row per run on the shared `ledger.jsonl` (the
worker's rows are `kind: "page"`; rows written before either existed have no kind, so everything
reading that file treats a missing kind as a page). Failures — no cli, a timeout, an
unparseable answer — are a ledger row and exit 0, the worker's law.

```bash
uv run --python 3.12 eva/stream/interpreter.py --once     # one reading, now, by hand
cp eva/stream/com.bekh.eva-stream-interpreter.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream-interpreter.plist
launchctl kickstart gui/$(id -u)/com.bekh.eva-stream-interpreter
launchctl bootout gui/$(id -u)/com.bekh.eva-stream-interpreter
```

It needs `claude` logged in on this machine, and nothing else — not llama, not the loom. Log:
`/tmp/eva-stream-interpreter.log`. Env: `STREAM_READ_EVERY` (2), `STREAM_READ_MEMORY` (4),
`STREAM_READ_TIMEOUT`, `STREAM_PERSONA`.

## Nothing here is in git

`shelf/sittings/stream/` and `shelf/stream/` are both gitignored. **Stream rooms are disposable
and untracked** — 288 pages a day written by nobody, most of them read once or not at all, and
the project's dry-run law says a lost page is an acceptable loss.

**What survives is what bekh stars.** Checked, not assumed: a `kept` through `/api/mark` on a
stream room runs the same `sync_artifact` a fan does, and on a one-node room it really does
write `shelf/artifacts/<hex>.json` — `by: "star"`, one step, 0.0 bits (a fan of one is no
choice), `prompt` the seed and the step's `took` the page. So the text of a starred page lives
in a tracked, pushed file even after the room is gone. Taking the star off moves that artifact
to `shelf/artifacts/.trash/`, as everywhere else. That behaviour is the loom's and was not
changed for the stream.

## Running it

```bash
uv run --python 3.12 eva/stream/stream.py --once     # one page, now, by hand
uv run --python 3.12 eva/stream/monitor.py           # the dashboard; --once for a frame
```

The agent — loaded on the mac since 2026-09-19 (`launchctl print gui/$(id -u)/com.bekh.eva-stream`
says whether it still is):

```bash
cp eva/stream/com.bekh.eva-stream.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream.plist
launchctl kickstart gui/$(id -u)/com.bekh.eva-stream      # don't wait 5 min for the first one
launchctl bootout gui/$(id -u)/com.bekh.eva-stream        # stop dreaming
launchctl bootout gui/$(id -u)/com.bekh.eva-stream; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream.plist   # after editing the plist
```

It needs `com.bekh.eva-llama` up. It does **not** need the loom agent to write pages — only to
read them at `https://eva.x/stream`. And `loom.py` changed, so the running loom serves the old
routes until `launchctl kickstart -k gui/$(id -u)/com.bekh.eva-loom`. Log: `/tmp/eva-stream.log`.

Env: `STREAM_DIR`, `STREAM_SEEDS`, `STREAM_INTERVAL`, `STREAM_N_PREDICT`, `STREAM_TEMP_LO`,
`STREAM_TEMP_HI`, plus loom's `LOOM_SITTINGS` and `LOOM_LLAMA`. The loom reads `STREAM_DIR` and
`STREAM_INTERVAL` too, and `LOOM_STREAM_PAGE` for a doctored copy of the page.

## Reading the monitor

`monitor.py` never writes. Three signals, kept apart, because conflating them is how a dead run
looks busy:

1. **the probe** — the spinner and the clock move, so this process is polling and not frozen;
2. **alive** — the heartbeat's age. Under one interval + a minute is mint; under two is light
   blue (one turn missed, usually the GPU busy with a census); past that the timer is not
   firing;
3. **progressing** — when a page LAST LANDED, off `last_ok`. A heartbeat ticking every five
   minutes with nothing under it is the alive-but-stuck state and says so in pink: *beating but
   writing nothing*. That is llama down, or every page coming back empty.

Under it: pages on the ledger, how many the filter flagged, how many runs wrote nothing, the
heat and length of the last forty, and the last eight runs one line each.

## Tests

`../tests/streamtest.py`, against `stub_llama.py`, a **fake `claude`** first on PATH (as
berserktest does it) and scratch dirs, never the real shelf. The worker and interpreter halves
run in-process; the api half is a real `loom.py` in a subprocess, as loomtest drives it. What it holds: the room shape and the flat `logprobs` with no `probs`
anywhere; the lot between the two pots and `good` not being `kept`; an over-large seed never
entering the pot; the trailing space gone from the room AND from the wire; every filter rule
one line each plus a flagged page still landing; an unreachable llama as a ledger row and exit
0; the tail cut to whole sentences; and on the routes — newest first, flagged hidden until
`all=1`, `before` paging backwards, `n` capping the batch, the three status states, a mark
through `/api/mark` showing up, and the star freezing a page as an artifact. For the
interpreter: a short stretch never starting the cli at all, the block being the newest two
unflagged, the persona going out verbatim, the last four readings in the prompt, a garbage
answer and a dead cli as ledger rows with exit 0, an identical copy having nothing red in it, a
slip kept and mapped (a word replaced, a word inserted inside an underline, a sentence dropped,
an underline on a word he did not touch), whitespace he normalised not lighting up, `<mark>`
being the only tag, and the api hanging the reading on the head of its block.

```bash
uv run --python 3.12 -m unittest discover -s eva/tests -p '*test.py'
```
