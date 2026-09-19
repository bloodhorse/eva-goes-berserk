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

**Three voices on one page** (2026-09-19): the sleeper dreaming (`stream.py`, nemo), the
sleeper remembering (`remembering.py`, opus rewriting the account of the dream so far), and the
reader at the bedside (`interpreter.py`, opus noting and underlining). They do not read each
other. `opus.py` is the one way the two opus voices talk to the cli and the one place their
cost is counted; `monitor.py` watches; `../front/stream.html` is the page, served by the loom at
`/stream`. Only the writer has a clock — it taps the other two when a passage lands.

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
- **Pot A is dealt from a shuffle bag** (`from_bag`, state in `shelf/stream/bag.json`): no seed
  returns until every other has had its turn. A fresh draw every five minutes is the birthday
  problem — on day one 62 pages had repeated 16 seeds while 32 of 78 were never touched, and
  bekh saw it as the switchboards returning. A new seed on the shelf is slipped into the current
  round; a lost bag file is a reshuffle.
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
the game*, who writes a short note on a dream and **underlines**, inside it, what touched him.
**A note for every generation** (2026-09-19).

`interpreter.py` is that reader: Claude Opus through the cli, headless, one call per run made
through `opus.py`. One-shot like the worker.

- **The writer taps the other voices when a dream lands.** Neither has an interval at all:
  `stream.py` ends a successful page with `launchctl kickstart` on both
  (`STREAM_KICK_INTERPRETER=1`, set in the worker's plist only), each tapped on its own so a
  reader that cannot start is no reason for the account to go untold. bekh, 2026-09-19 — they
  should start when the dream is finished; two independent 300s timers put a note a whole tick
  behind its dream. No `-k` and no lockfile: launchd will not start a second instance of a job
  that is already running, so a kick during a call is dropped, while `-k` would kill a note
  being written mid-cli-call. A lost kick costs one dream its note — an acceptable loss by the
  dry-run law, and the next kick reads the newest dream anyway.
- **The persona is `interpreter.txt`, bekh's file.** The code reads it and never writes it.
  Everything appended after it — the output shape, the memory, the material — is plumbing he
  should not have to see in his prompt, which is the whole reason for the split.
- **Tags, not json**: `<reading>…</reading>` then `<passage n="1">…</passage>` per passage,
  because the answer is full of `<mark>` and a tag inside a json string is an escaping question
  nobody needs to get right at 3am. Parsed leniently — a note with no passage is still a note.
- **The newest EVERY, never a backlog.** Each run takes the newest unflagged passages above the
  watermark (the newest room any note has covered) and only if there are `EVERY` of them —
  **one**, since a note belongs to a generation. If it was down for an hour, the twelve
  passages it missed stay unread: the stream is disposable, and a note on an hour-old dream is
  not what the page is for. The block of several is still in the file format, and the readings
  written before this cover two.
- **Its memory is its own last four notes**, in the prompt, oldest first. Nothing else carries
  from one call to the next.
- **No checker and no comparison, by decision** (bekh, 2026-09-19, after living with it for an
  hour). Its copy of the dream is stored verbatim, tags and all, and is never corrected — *a
  mistake in the copy is another prophecy*; the room on the shelf is never written to. The word
  diff that used to light every tiny difference in red is **gone**: it was noise. What is stored
  beside the verbatim copy is the same string cut by his `<mark>` tags alone, `[{t, mark}]`.
  Old reading files still carry a `kind` per segment; the page drops the `gone` ones and reads
  everything else by `mark`, and nothing rewrites a file on the shelf.
- **What he found valuable is simply written in colour** — a gentle magenta or a gentle cyan,
  never a background, an underline or a box, which both read as decoration laid over the text
  instead of as part of it. Which of the two inks a phrase gets is chance, made stable by a
  small hash of the room and the run's place in it, so the 60s poll never repaints a phrase a
  different colour. There is **no toggle**: it was superfluous. `?raw=1` still serves the
  shelf's own text, untrimmed and uncoloured, for checking what the interpreter was handed.
- **The page renders every segment through `textContent`.** Only `<mark>` is ever read as a
  tag, and that is done here; anything else he typed, `<script>` included, arrives as
  characters and leaves as characters.
- **A note is drawn beside its dream**: an inset above the passage on a phone, a right-hand
  column top-aligned with the block's head at ≥900px, the same node either way.

Storage, all under the gitignored `shelf/stream/`:
`readings/<YYYY-MM-DD>/<HHMM>.json` = `{ts, rooms (newest first), reading, marked, segments,
model, seconds, usage}`, and one `kind: "reading"` row per run on the shared `ledger.jsonl` (the
worker's rows are `kind: "page"`; rows written before either existed have no kind, so everything
reading that file treats a missing kind as a page). Failures — no cli, a timeout, an
unparseable answer — are a ledger row and exit 0, the worker's law. The monitor judges the
reader by whether the last page that landed has a row after it, since it has no heartbeat of
its own to age.

```bash
uv run --python 3.12 eva/stream/interpreter.py --once     # one note, now, by hand
cp eva/stream/com.bekh.eva-stream-interpreter.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream-interpreter.plist
launchctl kickstart gui/$(id -u)/com.bekh.eva-stream-interpreter   # what the worker does
launchctl bootout gui/$(id -u)/com.bekh.eva-stream-interpreter
```

It needs `claude` logged in on this machine, and nothing else — not llama, not the loom. Log:
`/tmp/eva-stream-interpreter.log`. Env: `STREAM_READ_EVERY` (1), `STREAM_READ_MEMORY` (4),
`STREAM_READ_TIMEOUT`, `STREAM_PERSONA`.

## The sleeper remembering — the third voice

bekh's idea: a second opus that writes a **through-line** through the passages. After the first
one a couple of sentences; with each new one he **rewrites** the account so the new passage
belongs to it — *three sentences, then three different ones, maybe one more* — and after a
couple of hours he starts again. He is not an outside narrator but **the sleeper remembering**,
first person, past tense; and what he is handed are not separate dreams but **scenes of one
dream he is dreaming**, so that he has to find connective tissue instead of listing
(2026-09-19). `remembering.py`, persona in `remembering.txt` — bekh's file, never rewritten by
the code.

- **Rewriting, not appending.** Each call hands over one version and one new scene and gets a
  whole new version back, so the account stays index-card sized and older scenes fade as newer
  ones arrive. An appender would grow a list, which is the opposite of remembering. **Every
  version is kept**: the sequence of rewrites is itself the object — what survived four
  rewrites is what the dream was about.
- **His only memory is his own current text.** Persona, shape, the latest version (or a line
  saying nothing is remembered yet and this is the first scene), one new scene. He never sees
  the reader's notes or underlines — with them in front of him the account would start
  answering the reader instead of remembering the dream. The two voices do not share a
  vocabulary and do not have to: the reader's own file calls each passage a dream, and it is
  left alone.
- **Seedless, and the ragged edges left alone** (bekh, 2026-09-19, having read four scenes each
  way: he prefers it, and it is not nonsense). The scene goes over as nemo wrote it — no seed,
  no `[scene]` label, and its ragged first and last words untouched. Those edges become the
  dream's **joints**: *the car stopped just before* followed by *killed.* came back as *stopped
  just before something was killed*. Tidy them and the account goes back to a list of scenes
  with nothing between them, which is what this voice exists not to be.
  `STREAM_DREAM_SEEDS=1` puts the old material back, labels and all, with one line of plumbing
  explaining them — in the code, because with no seeds in the material bekh's file has nothing
  to explain.
- **A breath, not an index card.** His file asks for *a few sentences, fifty words or so*, and
  for the older scenes to shrink to a clause or drop away. The index-card wording it replaced
  did not hold: four rewrites went 150 → 200 words. Measured after the change, on four real
  scenes: **73, 56, 59, 62** — the first is long and the rest sit near sixty, so fifty is the
  aim and sixty is the truth.
- **Which scene**: the newest unflagged passage above **his own** watermark, never a backlog.
  His watermark is kept apart from the reader's, so neither voice waits for the other.
- **A dream ends** after `STREAM_DREAM_TURNS` scenes (**4**, about twenty minutes — it shipped at 24 and bekh cut it the same evening, 2026-09-19: needling 24 scenes together is torture for a man, and a real dream has around four) or when the silence
  since its last version passes `STREAM_DREAM_GAP` (1800s — the mac slept, so he woke). Both
  are read off the versions themselves and there is no state file: a second place to keep
  "which dream are we in" is a second place for it to be wrong. The last version of a finished
  dream is the finished piece. A dream's id carries two random bytes beside the clock, because
  two dreams under one name would silently be one dream on the page and in every count.
- **On the page**: the current version sits at the very top of the feed with a small `3 / 4`,
  in a panel that is neither the dream text nor the reader's margin note. It is rewritten whole
  every few minutes, so the poll replaces it in place **only while he is at the top** and
  otherwise holds it until he scrolls back — a block quietly rewriting itself off-screen is one
  thing, a paragraph changing under a reader's eyes is another. A finished dream appears in the
  feed **where it ended**, above its last scene, at the full width of both columns.
- `dreams/<YYYY-MM-DD>/<HHMM>.json` per version = `{ts, dream (id), turn, of, room, text, model,
  seconds, usage}`; ledger rows `kind: "dream"`. Failures are a row and exit 0, the worker's law.

```bash
uv run --python 3.12 eva/stream/remembering.py --once
cp eva/stream/com.bekh.eva-stream-remembering.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream-remembering.plist
launchctl kickstart gui/$(id -u)/com.bekh.eva-stream-remembering   # what the worker does
```

Env: `STREAM_DREAM_TURNS` (4), `STREAM_DREAM_GAP` (1800), `STREAM_DREAM_TIMEOUT`,
`STREAM_DREAM_PERSONA`. Log: `/tmp/eva-stream-remembering.log`.

## Counting what opus costs

`opus.py` is the one call both opus voices make: `claude -p --model opus` in
`--output-format json`, prompt on **stdin**, `--tools ""` and `--strict-mcp-config` (a reader
with tools goes and reads the repo instead of the dream), `--setting-sources project` (without
it bekh's global `~/.claude/CLAUDE.md` is loaded into the head of somebody asked to read a
dream), `cwd` in a temp dir, `CLAUDECODE` stripped so a run started from inside a claude session
starts at all. It returns `(text, usage)` and every `reading` and `dream` ledger row carries
that block: `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`,
`output_tokens`, `cost_usd`.

**Our prompt is not the cost.** Measured on a real run: `input_tokens` 2, `cache_read` 2178,
`cache_creation` 1080–1736, `output` ~300, about **two cents a call** — the cli sends its own
system prompt ahead of ours every time. That is the number that decides whether the design
stays, which is why it is counted. It is counted and **not shown**: no dashboard block, no cli
(bekh, 2026-09-19 — he wants something that counts, and reads the ledger when he asks).

## Plates — a testing ground, nothing scheduled

A picture for a block of the stream. **Not built**: no daemon, no slot on the page, only two
prompts kept in hand to play with and interchange (bekh, 2026-09-19), in `plates/`:

**The working one is `prompt-pieces.txt`** — bekh's pick after seeing one plate from each in the
magenta-and-cyan palette; he went to his own first on intuition, then to this one. A cheap
decision: both files stay, and switching is which one gets filled.

- `prompt-bekh.txt` — his: *you are an artist, draw an abstract interpretation of this text*,
  over the passages **verbatim** (`{text}`). It gave the first plate, a dark palette-knife oil
  he found beautiful — and samey: he has made such pictures before and knows the cadence.
- `prompt-pieces.txt` — a painting made from **the interpreter's underlines** (`{pieces}`), not
  the full text: a drawing model is not a reading model, the full text came back as an inventory
  (a bread advert; a storybook kitchen), and the underlines are a distillation that already
  exists and fits the 77 tokens the old models read. Ends on `{hand}`.
- `hands.txt` — the pot `{hand}` is drawn from by lot, one line each. **A hand, never a name**: a
  named painter returned that painter (de Chirico's arcades took half the picture); a described
  way of laying paint returned a painting that looks like nobody's. The pixel line lives here too.

What the five runs seemed to show, held loosely: with no medium at all GPT falls to a photograph;
"abstract" is its one default; negatives name the thing they forbid (*no words or letters* still
got a fake signature — *unsigned*, stated as a fact about the painting, got none); the landscape
and palette lines hold. Runner, until there is one:

```bash
cd <a scratch dir> && codex exec --skip-git-repo-check -s workspace-write - < brief.md > codex.log 2>&1
```

with `brief.md` = the filled prompt plus one plumbing paragraph telling codex to use its image
generation tool and save `plate.png` in the current directory. One to two minutes, ~19k codex
tokens, one generation off the ChatGPT image allowance. Other hands than GPT's:
`../../IMAGE-MODELS.md`.

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
interpreter: one new passage being a note and nothing new starting the cli at all, the block
being the newest EVERY unflagged, the persona going out verbatim, the last four notes in the
prompt, a garbage answer and a dead cli as ledger rows with exit 0, segments coming from the
`<mark>` tags alone, an altered copy stored and served exactly as typed, `<mark>` being the only
tag, an old reading's `gone` segments still reaching the page, the api hanging the note on the
head of its block, and the kick — no subprocess with the flag off, both jobs' argv with it on, one
voice failing to start not stopping the other, and a kick that throws costing the page nothing.
For the sleeper: the first scene having nothing remembered yet, a later call carrying only the
latest version and one scene and never a note of the reader's, a flagged scene never told, the
scene cap ending a dream and the next starting fresh, a long silence ending one, a garbage
answer as a row with exit 0, the api carrying the running dream and a finished one where it
ended, usage on both kinds of row, and the cli's json read in either shape.

```bash
uv run --python 3.12 -m unittest discover -s eva/tests -p '*test.py'
```
