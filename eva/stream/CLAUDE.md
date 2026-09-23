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
- **Nemo is handed the TAIL of a seed, about 45 words** (`seed_tail`, `STREAM_SEED_WORDS`; 0 =
  the whole seed). bekh, 2026-09-21: the seeds had got out of hand — a pot median of 109 words,
  the classics at 650, a sliver of dream under a wall of grey; his example of a good one was two
  sentences, about 35 words, ending mid-clause. The front moves forward to a sentence start; **the
  end is never touched**, because the seam is the seed. Trimmed in the writer and not on the
  shelf, so the files stay whole and it is one number; and trimmed rather than folded on the
  page, because he found a fold a concealment — the grey text is exactly what the machine saw.
  **An experiment: half a day, then look.** What to watch: by length alone `seeds/nemo/` was
  already there and it was the worst folder (2 alive, 14 dead of 43), while his invented
  rule-documents, the best (12 of 19), run double that — a rule needs room to be stated before
  nemo can bend it, and a 45-word tail may cut the rule off.
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
  and the status, `GET /api/stream/events` is the same thing pushed. Marks go through the
  **existing** `/api/mark` — a second mark route would be a second place the at-most-one rule
  lives.
- **Nothing waits for a timer any more** (2026-09-22). Two halves, both additive:
  - **Every landing taps the mirror.** `push.py`, one function, kickstarting
    `com.bekh.eva-mirror` — called by the writer, the reader, the sleeper, the painter, the
    namer and `reread.py`, so what the mini serves is a second old and not up to a minute. No
    `-k`, for the reason the voices' kick has none: a kick during an rsync is dropped and the
    job's own 60s tick carries that change instead. The tick stays anyway — it is the path
    *home* for marks made on the mirror. A scratch shelf (`STREAM_DIR` or any `LOOM_*`
    override), `STREAM_PUSH=0`, or no `launchctl` at all and it is a no-op: a test must never
    push the real shelf, and a failed kick is a line on stderr and never a crash.
  - **`GET /api/stream/events`** holds the connection open and emits `event: change` with
    `{"rooms": [the ones whose fingerprint moved or appeared], "status": {…}}` every ~2s that
    something moved; a writer falling asleep is a change with `rooms: []`, and a `: keepalive`
    comment every 20s stops cloudflare and caddy calling a quiet connection idle. The
    fingerprint per room covers exactly what `/api/stream` hands over for it — the room file,
    its reading, its story, its name, its plate — built from the route's own helpers, and
    measured at **4.4 ms** a tick over 185 rooms (`loom.stream_prints`). It is a GET, so the
    mirror serves it exactly as the mac does, which is how `dreamshit.x` reads the stream.
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

`interpreter.py` is that reader, one call per run, one-shot like the worker — and since
2026-09-21 **the seat can be either family**. bekh: *we use opus on the left and opus on the
right… how about we use codex for the summarization of the dreams, so they are two different
families.* `STREAM_READER=codex` (set in this job's plist; the code's default is `opus`) puts
GPT at the bedside through `codex.py`, while the sleeper remembering stays opus — one house on
each side of the page.

- **The switch changes who answers and nothing else.** Same persona file, same output shape,
  same parser, same storage. The reading's `model` field and the ledger row say who wrote it:
  `opus`, or `codex:<model id>`. That is what makes a pile of notes readable blind later.
- **Two channels get codex out of its work doctrine, and only one of them binds.**
  `-c base_instructions=<json string>` **replaces** the coding-agent system prompt outright —
  the standing frame of a reading seat, and the reason a three-line note is not billed like a
  plate through the full harness. But instruction documents are the strong channel and no flag
  turns the global `~/.codex/AGENTS.md` off (`--ignore-user-config` only skips `config.toml`),
  so the call runs with `-C eva/stream/reader-seat/`, a tracked folder of ours whose `AGENTS.md`
  countermands the global one for this seat. That lesson is bought, not guessed:
  `~/tower/forge/friendship-is-magic/docs/decisions-timeline.md`, 2026-08-15 — *Codex's work
  doctrine is beaten in its own channel, not argued with*; four rounds of prompt rewording
  barely dented the postmortem reflex and one countermand in the right file ended it.
- **`gpt-6-astra` at reasoning effort `low`** (`STREAM_CODEX_MODEL`, `STREAM_CODEX_EFFORT`),
  pinned rather than inherited from bekh's `config.toml`, which runs `high`: a margin note is
  not a reasoning job and the effort would be paid for out of the same ceiling the plates draw
  on. `--json` for the event stream (the answer is an `item.completed` agent message, the token
  counts ride on `turn.completed`), `--sandbox read-only`, `--skip-git-repo-check`, prompt on
  stdin.
- **What a note costs, measured 2026-09-21** on one real dream (the sea monster in the flat,
  `stream/2026-09-21/1711`): **15.5s and 18,676 tokens** — 18,408 in, 7,936 of them cached,
  268 out. Opus's note on the same dream was 8.0s and about two cents. **Our prompt is not the
  cost here either**: the dream and the persona are a few hundred tokens and the input is
  eighteen thousand, because codex still sends its tool schemas and both instruction documents
  ahead of them. `base_instructions` bought the system prompt back and nothing else. That is
  one fifth to one third of a plate for a three-line note, off the same weekly limit — worth
  knowing before this runs all night.
- **The contamination probe, and it is not clean** (2026-09-21). Two days earlier headless
  `claude -p` was found silently loading bekh's global `~/.claude/CLAUDE.md` into the reader's
  head, so codex was asked the same question through this seat: *do you have any user-provided
  instruction file loaded about tone, persona or how to work?* — **YES**, and the heading it
  named was **`# global instructions for codex`**, bekh's `~/.codex/AGENTS.md`. The session
  record confirms it: ~8k characters of his work doctrine go out on every call, and this seat's
  `AGENTS.md` follows it as `--- project-doc ---`, last and therefore strongest. So the
  countermand is loaded and in the right place, and on the measured run it held — the note came
  back in shape, no preamble, no postmortem, no tool use. But the global file *is* in the
  reader's head and there is no flag that takes it out (only moving `CODEX_HOME`, which is also
  where the login lives). Re-ask the probe whenever the seat's flags change; it costs one call.
- **A held or failed codex costs one note, not a hole.** The reader never chews a backlog, so a
  dream with no note stays without one forever. When the guard holds, or the call fails, times
  out (120s, `STREAM_READER_TIMEOUT`) or comes back with no `<reading>` in it, **opus writes
  that one note** and the ledger row carries `fell_back` with the reason.
- **The guard is `codex.py`'s and is shared with the painter** — the same
  `~/.cache/claude-usage/codex.json` bekh's `cu` reads, refusing over `STREAM_READER_WEEK_MAX`
  (50) or `STREAM_READER_SESSION_MAX` (80), and refusing just as hard when the cache is
  missing, unreadable or over 30 minutes stale. Two jobs on one ceiling must agree on what a
  missing number means, or the one that guesses wrong eats the week. **The session window is
  the real ceiling**, measured the same day: 22 plates in 90 minutes tripped the five-hour
  window at 80% while the week stood at 19%.

- **The writer taps the other voices when a dream lands** (and the mirror, through `push.py`).
  Neither voice has an interval at all: `stream.py` ends a successful page with
  `launchctl kickstart` on both
  (`STREAM_KICK_INTERPRETER=1`, set in the worker's plist only), each tapped on its own so a
  reader that cannot start is no reason for the account to go untold. bekh, 2026-09-19 — they
  should start when the dream is finished; two independent 300s timers put a note a whole tick
  behind its dream. No `-k` and no lockfile: launchd will not start a second instance of a job
  that is already running, so a kick during a call is dropped, while `-k` would kill a note
  being written mid-cli-call. A lost kick costs one dream its note — an acceptable loss by the
  dry-run law, and the next kick reads the newest dream anyway.
- **Codex is the reader; opus is his understudy** (bekh, 2026-09-21, after five dreams read by
  both side by side). Codex stayed inside the dream where opus kept turning it into a portrait
  of an AI (*"a machine writing unwatched might say the same"*, *"perhaps that is how it pictures
  itself"*) — the one attractor this project keeps out of its documents, walking back in through
  the margin. And with opus already in the sleeper's seat, two opus margins agreeing meant
  nothing; two families agreeing means something. On the marks: across six dreams the two
  readers chose the SAME phrases three times, twice with the colours swapped — which phrase
  matters is partly real, which colour it wears is noise. Two edits to the persona came with
  the choice: its opening no longer says *the dreams of a machine… a language model* (that
  sentence fed the AI-portrait habit) and the margin note lost *what you would pencil beside
  it* (codex said "I would pencil" in three notes of five).
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
- **He reads each dream fresh, and sees only the dream** (2026-09-21). His memory of his own
  last four notes is OFF (`STREAM_READ_MEMORY`, default 0): shown his own notes he stopped
  remembering the dreams and copied his own format — one note opened *"Last time it…"*, the next
  call had that note in front of it, and from 16:42 on the first day **81 of 97 notes open with
  those two words** and end on *plainly*. A genre lock, nemo's disease, built by us; bekh saw
  it as four dreams summarized the same way. If a memory ever returns it has to be something he
  cannot imitate — a bare list of recurring images, never his own sentences; turning the number
  back up brings the formula back within the hour. And the seed is out of his sight
  (`STREAM_READ_SEEDS=1` restores it), as it is for the sleeper: with it labelled in front of him
  he narrated the plumbing — *"now it is handed Gogol's madman"* — instead of reading the dream.
  The persona file lost its two sentences about seeds and about remembering for the same reason.
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
- **Every dream gets a name, and the names are a MENU** (bekh, 2026-09-22): the page has very
  little separation between dreams and he does not read them all, so he chooses by name. The
  last paragraph of `interpreter.txt` is his — the reader finishes *"a dream about …"* **in one
  to four words** and writes only the part after those words, because the page says that half
  once, in how it is laid out. **The length is the whole style guide.** The first wording asked
  for a name that said the dream *fully enough that someone could tell from the name alone what
  is inside*, and 173 dreams came back as news items — *a sea monster crawling the bedroom
  walls that no longer eats me, though i beg it to take me back* — a register he hates (*man
  goes crazy in alabama*). "A few words" gave captions with a verb in them; with no form at all
  (*give it a name*) the reader writes Book Titles In Capitals. At one to four words there is
  room only for the thing itself — *bread that wasn't bread*, *the singing bones*, *her last
  mark*, *hats in the elevator* — and no word about style was ever needed. His cut each time;
  "be descriptive" was weighed and refused as the road back to headlines. What read weak in
  the 177: about fifteen abstractions that could be anyone's dream (*being watched*, *going
  home*) and a few that flatten the turn (*bread and reconciliation* for a dream with no
  reconciliation in it). **A name with a famous proper noun in it — *holmes*, *carmilla* — is a
  flag that nemo was reciting**, not dreaming: the namer sees only the dream, so the noun is in
  what nemo wrote. The plumbing is ours: a `<name>` tag on the shape, a lenient parser, and one
  cleaning — the prefix off if it was written anyway, quotes off, a trailing full stop off,
  wrapped lines joined, **lowercased always** (the page is lowercase and a name is part of the
  page; done in the cleaner and not asked for in the prompt, so it holds whoever wrote it).
  Known and unfixed: the cleaner strips a closing quote mark from a name that ends in one.
  Stored as `names: {room: name}`. **A missing name is never a failed note**; the dream simply
  shows its number. Both families do it and `reread.py` writes it too. The back catalogue was
  named by opus on 2026-09-22 (`naming.py`, 177 dreams); the long first-wording names are kept
  in `shelf/stream/names-backup-news-style/`.

Storage, all under the gitignored `shelf/stream/`:
`readings/<YYYY-MM-DD>/<HHMM>.json` = `{ts, rooms (newest first), reading, marked, segments,
names, model, seconds, usage}` — `model` being `opus` or `codex:<model id>` and `usage` that
family's own counters — and one `kind: "reading"` row per run on the shared `ledger.jsonl`,
carrying the newest dream's `name` so the ledger reads as a table of contents, and carrying
`fell_back` when the codex seat could not take it (the
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

It needs `claude` logged in on this machine and, for the codex seat, `codex` logged in too —
and nothing else: not llama, not the loom. Log: `/tmp/eva-stream-interpreter.log`. Env:
`STREAM_READER` (`opus` in code, `codex` in the plist), `STREAM_READ_EVERY` (1),
`STREAM_READ_MEMORY` (0), `STREAM_READ_TIMEOUT` (300, the opus call), `STREAM_READER_TIMEOUT`
(120, the codex call), `STREAM_READER_WEEK_MAX` (50), `STREAM_READER_SESSION_MAX` (80),
`STREAM_CODEX_MODEL`, `STREAM_CODEX_EFFORT`, `STREAM_PERSONA`.

```bash
# one note by hand, from the other family, without touching the real shelf
STREAM_READER=codex LOOM_SITTINGS=/tmp/scratch/sittings STREAM_DIR=/tmp/scratch/stream \
  uv run --python 3.12 eva/stream/interpreter.py --once
```

### Naming the back catalogue

The ~150 dreams dreamt before names existed get names too, and **from opus** — bekh,
2026-09-22: *i have basically infinite tokens for this… leave codex alone.* The reader's seat
is codex's and codex's five-hour window is the scarce thing here; a hundred and fifty names is
exactly the job for the other family's tokens.

`naming.py` is that hand tool, and the one thing it must never do is **write a note**. Those
dreams already have one, and a reading file is the whole reading — the note, the verbatim copy
and the marks. The newest note for a room is the one the page shows, so a naming pass that
wrote reading files would quietly put an empty copy over every marked one on the shelf. So:

- **The prompt is names only**, and its middle is bekh's own naming paragraph read out of
  `interpreter.txt` **at run time** — one source for what a name is, never a second copy that
  drifts; if he edits that paragraph the tool follows him on the next run, and if it is not
  there the tool stops and says so. One framing line, his paragraph, a `<name>` shape, the
  dream alone. No seed, like every other voice here. The tag or nothing: taking a bare answer
  would file *"i would rather not name it"* as the name of a dream.
- **Its own store**: `names/<YYYY-MM-DD>.json` = `{room: name}`, by the ROOM's date so a run at
  three in the morning files yesterday's dreams under yesterday, rewritten atomically after
  **every single name** — a run of a hundred killed at ninety keeps ninety.
- **On the page a note's own name wins**, then this store, then nothing. A dream the reader
  named today is never answered for by an older pass.
- Flagged dreams are skipped, a failed call is a line and the next room, and every name is a
  `kind: "name"` row on the ledger with its usage, counted like everything else.

```bash
uv run --python 3.12 eva/stream/naming.py --unnamed --limit 5     # oldest first
uv run --python 3.12 eva/stream/naming.py --unnamed --day 2026-09-19
uv run --python 3.12 eva/stream/naming.py --room stream/2026-09-21/1711
```

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
- **A breath, not an index card.** His file asks for *a few sentences, thirty words or so*, and
  for the older scenes to shrink to a clause or drop away. The index-card wording it replaced
  did not hold: four rewrites went 150 → 200 words. He runs about a quarter over whatever number
  he is given: at *fifty words or so* the run of 2026-09-21 measured a median of 62–64 words for
  scenes one to three and 72 at scene four (max 89 — the older scenes do not shrink as asked).
  bekh found that too much and cut the number to thirty the same day, number only, nothing else
  in the file touched; what thirty really gives is not measured yet —
  `shelf/stream/dreams/<date>/*.json`, `text` by `turn`.
- **Which scene**: the newest unflagged passage above **his own** watermark, never a backlog.
  His watermark is kept apart from the reader's, so neither voice waits for the other.
- **A dream ends** after `STREAM_DREAM_TURNS` scenes (**4**, about twenty minutes — it shipped at 24 and bekh cut it the same evening, 2026-09-19: needling 24 scenes together is torture for a man, and a real dream has around four) — **and only
  then**. There used to be a second ending, half an hour of silence (`STREAM_DREAM_GAP`, "the
  mac slept, so he woke"), and it was cut on 2026-09-23: the silence was always bekh stopping
  the stream, which lands anywhere in the count, so every evening that ran 4n+1 passages left a
  one-scene story stranded (chapters 11, 13, 17) and the next evening started over. Now a story
  waits across a stop: one passage tonight, two tomorrow, one the day after is one story of
  four. The strays it left were mended by `--retell 11` the same day (every story from 11 on
  retold, so the numbers from 11 on moved; the old versions are in `dreams/.trash/`). The count is read off the versions themselves and there is no state file: a second place to keep
  "which dream are we in" is a second place for it to be wrong. The last version of a finished
  dream is the finished piece. A dream's id carries two random bytes beside the clock, because
  two dreams under one name would silently be one dream on the page and in every count.
- **A story belongs to a pack of dreams** (bekh, 2026-09-21). Two designs had been stacked —
  "the left shows the current story, finished ones are parked in the centre" (the model's) and
  "the story lives on the left" (his) — and he dissolved the split: *the thing that's on the
  left is almost always a finished story, unless it's the last 3 not 4 dreams.* There is no
  current-versus-finished to draw. One rule: **every pack of dreams that share a story has that
  story to its left, beside them; as you scroll through the pack the story rolls with you,
  staying near the top of the screen; when you reach the next pack it is replaced by that
  pack's story.**
- **The rolling needs no script.** A `.pack` is one grid cell with the story and the passages
  both placed in it (`grid-area: 1 / 1`, which is what lets grid items overlap), the story
  `position: sticky` a little under the pinned header. The browser keeps it at the top while
  the pack is on screen and takes it away with the pack — measured: a story rests at 53px
  mid-pack, is pushed up out of frame as its pack's bottom edge passes, and the next pack's
  story rides in from below at the boundary. It adds no height and lies over a plated band,
  which spans all three tracks. A pack shorter than its story grows to it — rare, accepted.
- **The feed runs in the normal direction** (bekh, 2026-09-21): **oldest at the top, newest at
  the bottom, and the viewer put at the honest bottom when the page loads.** It ran newest-first
  for two days — his call on day one, right for a bare feed of dreams — and the stories changed
  the answer: a pack's scenes came out last-to-first, so the account beside them told the night
  backwards, and a sticky story would have ridden the screen while scrolling INTO the past.
  Turned round, 1→4 reads downward and sticking to the top while reading down is what sticky is
  for.
- **Loaded honestly, in one go**: a day's worth (300, over `STREAM_N_MAX`, which had to clear a
  day) on load, rendered whole, then the scroller put at the bottom and put there again on
  `load` in case the fonts land late. The sentinel, the IntersectionObserver slicer and the
  "the shelf ends here" line are gone. The past is asked for: a quiet `earlier` at the top of
  the feed fetches the previous day's worth and inserts it above, keeping the reader where he
  is by measuring the topmost element's offset before and putting it back after — Safari has no
  dependable scroll anchoring, so it is done by hand. A pack continued across that boundary
  merges into the pack already on top instead of opening a second one with the same id.
- **New dreams arrive below.** The 60s poll appends at the bottom; standing at the bottom the
  page follows down, anywhere else the dream lands silently and only the quiet `new` hint
  appears, which scrolls to the bottom when tapped. A live rewrite of a pack's story still swaps
  in place under the soft fade. A count `3 / 4` shows only while a pack is live and not full;
  a complete or ended pack is simply a story.
- **Gone with the split**: the `.ended` boxes in the dreams' column (they looked like a dream,
  sat where dreams sit, and appeared above the scenes they told), the `1 / 4 · told` wording,
  the separate "current" trickle and the top-of-feed panel — the phone now shows each pack's
  story as an inset at the pack's head.
- **A story has a name, and every dream has a psalm's number** (bekh, 2026-09-22). His last
  paragraph in `remembering.txt` asks the sleeper for *what you would call it if someone asked
  you about it over breakfast*; the title is rewritten with the account, so the **latest
  version's title is the story's name** — a dream of four scenes is often not the dream its
  first scene looked like, and that is the point rather than a wobble. And the address:
  **`12:3` is the third scene of the twelfth story.** A chapter is one story, a verse is a
  scene's `turn` inside it.
  - **Chapters count up forever and never reset**, and the number is **stored** on every
    version when the story starts — never counted at read time. Forgetting is coming
    (`BRIEF.md`, parked): old files will be pruned, and an address computed from what is left
    would shift under him, so the twelfth story would become the fourth and every number he
    remembers would be a lie. A pruned story's number is simply never handed out again.
  - **`remembering.py --number`** is the one-off backfill for the stories written before this:
    stories in the order of their first version, only ever ADDING the field, idempotent, and
    it prints what it did. Run once on 2026-09-22: **11 stories, 38 versions numbered**.
  - A version with no chapter (nothing else is left like that now) gives its room no verse, and
    the page shows the name alone.
- **One telling with seams in it** (bekh, 2026-09-22, and this is the ideal he thought might be
  unobtainable: *a really long trickle of a story that synchronizes with the particular beat
  while remaining one continuous narrative, so that the part that corresponds to a dream is
  always on the left of that dream*). The account stays **one continuous telling, rewritten
  whole** — it does not become four paragraphs and it never becomes an append. The sleeper
  simply marks where each later scene comes in with a single `|`, and the page cuts there and
  puts part n beside passage n.
  - **The mark may fall mid-sentence, and usually should**: that is where a scene enters, and
    the sentence stays whole across the cut — *the door at the end* | *was a lift going down*
    reads as one line of prose down the column. The shape says so in as many words, and says
    **never** start a new sentence, a new line or a new paragraph for it. The word *paragraph*
    is never asked for anywhere: paragraphs were the shape he rejected.
  - **The paragraph asking for the mark is the CODE's** (`SHAPE` in `remembering.py`), like
    the output tags. `remembering.txt` stays bekh's file — and its length line (*a few
    sentences, thirty words or so*) **stays as it is, his decision the same night**: measured
    over two days he writes ~60 words whatever the line says (scene 1 median 60, scene 4
    median 70), a four-scene telling cut at the seams is ~15 words a part, and asking for
    more would turn the trickle into a retelling. Compression is the point.
  - **The text is stored exactly as written, marks and all**, like everything else a voice
    writes here; nothing corrects a missing or a surplus mark. `parts` rides beside it on the
    version and on the api — that same string split on `|`, each part stripped of surrounding
    whitespace and nothing more — so no reader re-implements the split. `text` is the source of
    truth and the `|` is never taken out of it.
  - **A wrong number of marks is not an error.** Fewer parts than passages and the later rows
    are simply bare; more, and the surplus is appended to the last passage's part; none at all
    and the whole telling sits beside the first passage, which is what every account written
    before this does and what the page did before the seams existed.
  - **His memory carries the marks back to him** — what he is shown as "what you remember of
    the dream so far" is his own latest text, seams included, so he can see where he put them
    last time.
  - On the page: `dreamshit/` is where this is read (`dreamshit/docs/front.md`); eva's own
    placeholder shows the whole account and simply hides the `|` at render.
- **On the page the names are the menu.** A dream is headed by `12:3 · <its name>` at the very
  top of its block, above the grey seed: the number in the ghost tone, the name in the body ink
  at 14px. No name and there is only the number; neither and nothing is drawn, exactly as
  before. The story's name heads its account on the left with its chapter, **a size bigger**
  (16px — his words: the block header is a bit bigger), and on a phone it heads the pack's
  inset. Both through `textContent`, like everything else here. A rewrite that only renames the
  story still swaps under the soft fade — the title is part of what is compared, or a new name
  would sit unwritten above the old account until the next scene.
- `dreams/<YYYY-MM-DD>/<HHMM>.json` per version = `{ts, dream (id), chapter, turn, of, room,
  text, parts, title, model, seconds, usage}` — `parts` derived from `text`, never a second
  source; ledger rows `kind: "dream"`. Failures are a row and
  exit 0, the worker's law.

```bash
uv run --python 3.12 eva/stream/remembering.py --once
uv run --python 3.12 eva/stream/remembering.py --number   # chapters for the old stories; idempotent
launchctl bootout gui/$(id -u)/com.bekh.eva-stream-remembering    # before a retell, or a live tap cuts in
uv run --python 3.12 eva/stream/remembering.py --retell 11   # bin chapters 11+ to dreams/.trash/, tell those scenes again
cp eva/stream/com.bekh.eva-stream-remembering.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream-remembering.plist
launchctl kickstart gui/$(id -u)/com.bekh.eva-stream-remembering   # what the worker does
```

Env: `STREAM_DREAM_TURNS` (4), `STREAM_DREAM_TIMEOUT`,
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

**Where the prompts stand (2026-09-21, after 43 plates — 20 his, 23 pieces): every plate is made
from the whole dream, and two prompts take turns** — `plate.py`'s default `--prompt alternate`
reads the newest plate on the shelf and uses the other one, which is what the automatic painter
gets too. `bekh` is his *abstract interpretation* line; `attic` (`plates/prompt-attic.txt`) is
the unsigned attic painting with a `{hand}` by lot — *paint what it leaves behind… the things in
it can be partial, out of scale, in the wrong place*. Each file's own slot decides what the
painter is shown (`{text}` the dream verbatim, `{pieces}` the marked phrases). **`pieces` is
parked, not deleted**, and runs only when asked for by name. It is where `attic` came from: the
same prompt, but handing the painter **only** the reader's two marked phrases — no text, no
note, no name — and the reader is asked what touched it and what felt strange, never what the
dream is about. The bread dream (`1721`, one he loved) was marked *The heel made a little mark*
and *the dreams were better than the real thing*; the painter, told `Landscape.` on top of that,
returned a high-heeled shoe on a seashore at sunset, and the word *bread* had never reached it.
Repainted from the whole text it came back a torn loaf, crumbs, a heel print and a broom's
sweep. bekh liked many of the pieces plates (the widows' names; a face in a door panel for
*something a house might answer*, the single strangest one), and the bet behind `attic` is that
the paint-first wording and the hand made them, not the starvation. Untested, shipped on his
word without a side-by-side. **The thing to watch**: pieces was built because a full text once
came back as an inventory, and the repainted bread plate is already close to one — every noun
present. If he finds it interesting again: one line of what the dream is about (its name)
beside the pieces. **Words in a picture are
allowed**: one plate lettered the dream's own lines onto the canvas (the widows' names) and it
was one of his favourites — another dimension, where it fits; rare; nothing in either prompt
pushes for or against it, and no lettering clause goes back in. **The 16-bit pixel hand is
out of the pot** (his call: it gave adventure-game backdrops). Noticed and left alone:
"landscape, magenta, neon, cyan" pulls most plates to a disc over water at sunset; the ones set
indoors escape it. A hand is recorded only for a prompt that has a `{hand}` slot. Nine plates
cost about two points of the codex week by his `cu`, roughly a minute each.

**Two ways a plate is made.** `plate.py` by hand, one room at a time — a failure there is a
message and a non-zero exit, the opposite of every other stance here, deliberately. And
`plating.py`, **one plate per dream while the stream runs** (bekh, 2026-09-21: *draw a picture
to every dream that's going right now… and keep your hand on the limit of codex*), a fourth job
the writer taps when a dream lands, with no clock of its own.

- **One plate per run, at most.** A run is 60–90s and a dream lands every 300s, and launchd will
  not start a second instance of a job already running — so there is no lock and no queue here:
  whatever is unpainted when the next dream lands is picked up then.
- **Which dream**: the OLDEST unflagged room with no plate, at least `STREAM_PLATE_SETTLE` (90s)
  old — so the reader's note has landed and the `pieces` prompt has words to work from — and no
  older than `STREAM_PLATE_WINDOW` (6h), so a job that was off for a day does not wake up and
  paint three hundred pictures. Oldest first, because a picture arriving for a dream he read an
  hour ago is still the picture for it. The clock is read off the room's NAME, which is a
  timestamp, so the window costs no file reads.
- **The guard, which is the point of it.** Before painting it reads the same usage cache bekh's
  `cu` shows (`~/.cache/claude-usage/codex.json`) and refuses when `week.utilization >= 50`
  (`STREAM_PLATE_WEEK_MAX`), `session.utilization >= 80` (`STREAM_PLATE_SESSION_MAX`), or when
  the cache is missing, unreadable or over 30 minutes stale. **No numbers is not a green light**
  — the failure that matters is an unattended painter eating a week of his limit at three in the
  morning. Nine plates measured about two points of the week, so a plate per dream is roughly
  **65–70 points of a week per day**: affordable for a half-day experiment, not a way of life.
- A held run writes ONE ledger row `kind: "plating"` with `held`, `week` and `session`, and only
  when the reason or the numbers' tens digit has changed — otherwise 288 identical rows a day
  would bury the ones that mean something. It resumes by itself when the numbers drop. A painted
  run's row carries the numbers it saw.
- It calls `plate.py`'s own entry point and duplicates none of its logic: the prompts, the
  alternation, the hand, the conversion and the `kind: "plate"` row all live there.

```bash
cp eva/stream/com.bekh.eva-stream-plating.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream-plating.plist
launchctl bootout gui/$(id -u)/com.bekh.eva-stream-plating   # stop painting, stream keeps running
uv run --python 3.12 eva/stream/plating.py --once            # one by hand
```

```bash
uv run --python 3.12 eva/stream/plate.py --room stream/2026-09-19/1647
uv run --python 3.12 eva/stream/plate.py --room stream/2026-09-19/1437 --prompt bekh --from a.png
```

- **The prompt files are bekh's**, filled and never rewritten: `plates/prompt-bekh.txt` and
  `plates/prompt-attic.txt` (the two that take turns) and `plates/prompt-pieces.txt` (parked),
  with `{hand}` drawn by lot from `plates/hands.txt`
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

**Starting and stopping the stream means nemo too** (bekh, 2026-09-21: *when we decide to stop
the stream, we gracefully finish nemo as well*). Nemo wires about 10 GB of a 16 GB mac and has no
job once the writer is off. Its launchd job restarts a crash and lets a clean exit stay exited,
so a SIGTERM is the graceful stop and the job stays loaded for the next start:

```bash
# stop: the writer first, then nemo
launchctl bootout gui/$(id -u)/com.bekh.eva-stream
launchctl kill SIGTERM gui/$(id -u)/com.bekh.eva-llama
# start: nemo first, wait for it, then the writer
launchctl kickstart gui/$(id -u)/com.bekh.eva-llama
until curl -sf http://127.0.0.1:8080/health >/dev/null; do sleep 2; done
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-stream.plist
```

If the loom is being used for fans at the same time, nemo stays up — it is the loom's model too.

**The ration: `eva go N`** (`stream/go.sh`, 2026-09-22 — bekh: codex is the scarce thing, so a
run is sized in dreams). N dreams — N passages, each with its note, its retelling and its
plate — then the writer off and nemo off, by the lines above. **Foreground on purpose**: it
stays in the terminal and ctrl-c ends it clean (writer off, nemo off, the painter's cap put
back); `eva go stop` does the same from another terminal. The painter's cap for the run is
bekh's own number for the week — 43, `eva go 5 50` for another — not a formula (his call the
same day: a computed cap is arbitrary); a week already past it refuses; restored however the
run ends; the last dreams, bare when the writer stops, are
painted by hand at the end. Log `/tmp/eva-go.log`; a finished run pushes to `kk_alert`.


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
`STREAM_TEMP_HI`, `STREAM_PUSH` (`0` = don't tap the mirror), plus loom's `LOOM_SITTINGS` and
`LOOM_LLAMA`. The loom reads `STREAM_DIR` and `STREAM_INTERVAL` too, `LOOM_STREAM_PAGE` for a
doctored copy of the page, and `STREAM_EVENTS_TICK` / `STREAM_EVENTS_KEEPALIVE` /
`STREAM_EVENTS_ROOMS` for the held connection.

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
For the codex seat (a stub `codex` speaking the cli's JSONL events, beside the stub `claude`):
the same prompt going out — persona verbatim, no seed, no memory — the reading stored as
`codex:<model>`, the argv carrying `base_instructions`, `-C` the seat dir, `--json` and the
read-only sandbox, a held limit and a dead or unreadable codex each falling back to opus with
the reason on the row, both families down still being a row and exit 0, the default staying
opus with codex never started, and a `STREAM_READER` nobody has heard of refused loudly.
For the names (bekh's menu): the prefix, the quotes and the full stop cleaned off and a wrapped
name joined into one line, a note with no name still being a note, both families naming it, the
sleeper's title rewritten with the account and the latest winning, chapters counting up and
surviving a pruned story, the verse being the turn, the backfill numbering in order and doing
nothing the second time, and the api carrying `name`, `verse`, `title` and `chapter`. For the
back-catalogue namer: bekh's paragraph going out verbatim with the dream and no seed and no
note shape, a named room skipped without a call, a day to a file with the ROOM's date, a run cut
short keeping what it did, a flagged dream never named, and **every reading file byte-identical
after a pass**. For the sleeper: the first scene having nothing remembered yet, a later call carrying only the
latest version and one scene and never a note of the reader's, a flagged scene never told, the
scene cap ending a dream and the next starting fresh, a long silence NOT ending one, a garbage
answer as a row with exit 0, the api carrying the running dream and a finished one where it
ended, usage on both kinds of row, and the cli's json read in either shape. For the seams: the
shape asking for the mark, the marks kept in the stored text and handed back to him as his
memory, `parts` being that text cut at them, a telling with no mark being one part, and the api
carrying `parts` beside `text` — for a version written before they existed too.

```bash
uv run --python 3.12 -m unittest discover -s eva/tests -p '*test.py'
```
