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
- **Two marks and no more, and the colours mean them** (bekh, 2026-09-21). His own prompt
  already asked for two things, so they are two tags now: `<touched>` — what impressed and
  touched him most — is the **magenta**, `<strange>` — what felt most mysterious and meaningful
  — is the **cyan**. A colour is a reading instead of a coin toss. The **first of each kind
  wins**: a second `<touched>` becomes plain text and is counted on the ledger row (`dropped`),
  because enforcing that where the copy is cut is cheaper than a second rule in the page that
  would have to agree with this one forever. Legacy `<mark>` still parses, and a legacy reading
  is brought under the same rule as it is drawn — first run magenta, second cyan, the rest plain
  — so the whole feed shows two marks however old the reading is, and nothing on the shelf is
  rewritten.
- **Written in colour and nothing else** — never a background, an underline or a box, which
  both read as decoration laid over the text instead of as part of it. There is **no toggle**:
  it was superfluous. `?raw=1` still serves the shelf's own text, untrimmed and uncoloured, for
  checking what the interpreter was handed.
- **The page renders every segment through `textContent`.** Only the two marks (and the legacy
  `<mark>`) are ever read as tags, and that is done here; anything else he typed, `<script>` included, arrives as
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
- **On the page, three voices in three columns** (bekh's picture): the dreams down the centre,
  the sleeper's account on the **left** at about half the notes' width, the reader's notes on
  the right, from 1180px. The feed is the grid and not `main`, because a plated dream's band has
  to cross all three tracks and can only do that as an item of the grid the account is in.
- **The left column is a counterpart to the dreams, not a status box** — bekh, 2026-09-21:
  *"a counterpiece to the dream as much as the summarization, which is always there"*. The
  account **starts at the top beside the newest dream and reads downward for its own length**,
  flowing with the page and scrolling away. It is not sticky; it was, for two days, and that was
  a misreading of him. It is laid **over** the left track, out of the grid's flow: as a grid
  item it collided with a plated dream, whose band spans that track too, and the grid pushed
  the newest dream down to start below the story instead of beside it.
- **It is never blank.** With nothing live — the stream off, or the dream ended by the gap or
  the scene cap — it shows the last account there is, with its count and a quiet word beside it:
  `1 / 4 · told`. That is what `live` on the api's `dream` is for; the server falls back to the
  newest version overall rather than handing back null.
- **His ideal, recorded as NOT built**: whatever dream you are looking at, its note to the right
  and *the part of the story that corresponds to it* on the left. He thinks it may be
  unobtainable. The idea on the table: keep rewriting the whole account every time, but write it
  **in parts, one per scene**, so a later scene can still change an earlier part — the rewriting
  is the point and must never become an append.
- A live rewrite still swaps under a soft fade. A finished dream keeps its inset in the feed
  **where it ended**, above its last scene, in the centre column — **except** the one standing
  in the left column, or the same words are on screen twice. The page draws the story before
  the passages for exactly that: the other way round, the first load cannot know which dream
  the left column holds and shows it twice. Two columns and the phone keep the
  panel at the top of the feed, never blank there either.
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

## Plates — a painting behind the dream

**bekh's picture, the way he has always seen it (2026-09-20): the dream's text; the reader's
note to its right; and the painting made for that dream BEHIND the dream's text**, dimmed so it
does not fight the words. Not somewhere else on the page — behind it. This is not the final
look, it is the mechanic the front will use.

**Where the prompts stand after fourteen plates (2026-09-20/21), in bekh's terms: almost no dud,
so nothing gets changed until we understand why it works.** Both prompts stay and **take
turns** — `plate.py`'s default `--prompt alternate` reads the newest plate on the shelf and uses
the other one. His prompt over the whole dream gave five of five good to very good, looser and
more painted; the coloured-words prompt gave the single strangest one (a face in a door panel
for *something a house might answer*) and two genre backdrops. **Words in a picture are
allowed**: one plate lettered the dream's own lines onto the canvas (the widows' names) and it
was one of his favourites — another dimension, where it fits; rare; nothing in either prompt
pushes for or against it, and no lettering clause goes back in. **The 16-bit pixel hand is
out of the pot** (his call: it gave adventure-game backdrops). Noticed and left alone:
"landscape, magenta, neon, cyan" pulls most plates to a disc over water at sunset; the ones set
indoors escape it. A hand is recorded only for a prompt that has a `{hand}` slot. Nine plates
cost about two points of the codex week by his `cu`, roughly a minute each.

**Still nothing scheduled.** `plate.py` is a hand tool: no launchd job, no kick, no clock. Every
plate costs one generation off bekh's ChatGPT allowance and about a minute, so it is run on
purpose, one room at a time, and a failure is a message and a non-zero exit — the opposite of
every other stance here, deliberately.

```bash
uv run --python 3.12 eva/stream/plate.py --room stream/2026-09-19/1647
uv run --python 3.12 eva/stream/plate.py --room stream/2026-09-19/1437 --prompt bekh --from a.png
```

- **The prompt files are bekh's**, filled and never rewritten: `plates/prompt-pieces.txt` (the
  default) and `plates/prompt-bekh.txt`, with `{hand}` drawn by lot from `plates/hands.txt`
  unless `--hand` says otherwise. The paragraph telling codex to use its image tool and save
  `plate.png` is appended **after** the file by the code — the file he reads is the prompt, and
  nothing about saving a png belongs in it.
- **Pieces, not the whole dream.** `{pieces}` is what the interpreter underlined in that room,
  one per line in order, adjacent marked runs joined, off the newest reading covering it. A
  drawing model is not a reading model: the full text came back as an inventory. With no
  reading, or nothing marked, it falls back to `bekh` over the dream verbatim and says so on
  stdout and in the json.
- **`--from`** files a png that already exists without calling codex — which is how the two
  plates drawn by hand on 2026-09-19, before this existed, are on the shelf.
- **Storage** (gitignored, with everything else in `shelf/stream/`):
  `plates/<YYYY-MM-DD>/<HHMM>.jpg` — the served copy, longest side 1400 at quality 82 via
  `sips`, because codex hands back a ~3 MB png and the page loads one of these per passage —
  the original `.png` beside it, and `.json` with `{ts, room, prompt, hand, pieces, seconds,
  source_png}`. One plate per room; a re-run replaces it. Ledger rows `kind: "plate"`.
- **Served as a file**: `GET /stream/plate/<date>/<HHMM>.jpg`, the path built only from a name
  `name_ok` has passed, cached hard because each `/api/stream` page carries
  `plate: "<url>?v=<mtime>"` and a re-drawn plate is a new url.
- **The wash is measured, not guessed.** The plate is the band's background under a two-stop
  gradient of the page's own ground. Dark: 0.90–0.955, which leaves body ink at **9.9:1** over
  these plates and **7.6:1** over the brightest cell in one (12.1:1 on the bare page). Light:
  0.915–0.955 → **6.2:1**, against a light palette whose own ceiling is 6.66:1 — that room
  cannot do better and does not pretend to. A picture bright enough to break the dark figure
  would have to be near white; none of these is (mean luminance 0.21).
- **The peek**: hover on a desk, press-and-hold on a phone, and the wash lifts to ~0.3 for as
  long as it is held. The hold starts only for a touch pointer, dies on the first real move and
  never begins on a mark button, so it does not fight text selection or the strokes.
- **The plate is the band of the WHOLE dream** (bekh, 2026-09-21: *"pic should stay on the whole
  space pertaining to the dream — left to right — trickle, dream, summary"*). It is the
  article's background and never the inner block's: at three columns that is the account's
  column, the dream and the note; at two, dream and note; on a phone the dream with its note
  inset. The account lies over whatever band it passes — every background paints before every
  line of text — and reads on the same wash. Rounded on the band's outer edges.
- **The dream decides the box and the picture fills it** (bekh, 2026-09-20). `cover`, centred,
  the aspect ratio never touched: a short dream shows a cropped band of its painting, a long one
  a zoomed, side-cropped one. A plate **never makes a passage taller or moves a word** — no
  min-height anywhere — and the 16px/18px the wash needs for legibility is taken straight back
  by an equal negative margin sideways, while the vertical padding stays the passage's own — so
  a plated passage's box is exactly its unplated box and the picture bleeds into the gutters
  instead of pushing the text inward. The same padding on every plated passage.
- **The wash is tuned by eye, at `https://eva.x/stream?tune=1`** — a panel of three sliders
  (wash, fade between the gradient's two stops, peek) that writes the same `--wash-a/-b` and
  `--peek-a/-b` the stylesheet uses, prints the two alphas to read out and the contrast they
  cost over a black and a white plate, and remembers per theme in `localStorage` (the stored
  numbers apply without `?tune=1`; `reset` clears them). It is a tool and not the look: what it
  lands on gets **baked into the stylesheet by hand**, and the tuner then stays as a hidden
  tool for the next time.
- **Lazy**: a plate is a quarter of a megabyte and most of the feed is below the fold, so the
  background is set only when its block comes within 800px of the viewport, loaded through an
  `Image()` first so nothing is ever painted half-arrived.
- A passage with no plate renders exactly as it did before any of this.

What the runs have shown, held loosely: with no medium at all GPT falls to a photograph;
"abstract" is its one default; negatives name the thing they forbid (*no words or letters* still
got a fake signature — *unsigned*, stated as a fact about the painting, got none); the landscape
and palette lines hold; **a hand, never a name** — a named painter returned that painter (de
Chirico's arcades took half the picture), a described way of laying paint returned a painting
that looks like nobody's. Five plates are on the shelf, 60–72s and ~19k codex tokens each.
Other hands than GPT's: `../../IMAGE-MODELS.md`.

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

The agent. **Whether the stream is on is whether this job is loaded** (`launchctl print
gui/$(id -u)/com.bekh.eva-stream` answers; bekh stops it for the night with the `bootout` line and
starts it with the `bootstrap` line — the two opus voices have no clock and can stay loaded):

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
