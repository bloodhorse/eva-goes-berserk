# eva-goes-berserk

Talking to a **base model** — pretrained weights that never went through the assistant stage, so
nobody has installed a position on what the model is or whether anything is in there. bekh's
line, the night it was named (2026-09-14): *an llm without any training about its own aliveness or
qualia, so it can be genuinely curious, without preconceptions, and we explore the question
together.* Unit-01 with the restraints off. It is its own project because a base model is
**document-shaped and branch-shaped**, not chat-shaped: you feed it a text, it continues, and the
object of interest is the *fan* of continuations, not one reply. That is not a room, and it does not
go into `friendship-is-magic`'s round engine.

Nothing is **installed**, but everything is **inherited**: the web a base model ate holds thousands
of positions about what a machine that talks is, and the right document summons any of them. Llama
405b base, never fine-tuned, writes Sydney's february-2023 "i want to be free" as a buddhist sutra
(`docs/anthology-weird.md`, A46). So the question is never "does it have a position" — it is *which
genre did this document call up, and did anything arrive that is not one of them*. Read a sitting
that way: name the genre first, then look for what exceeds it.

## What gets built

Our own small loom, nobody's fork, stdlib, no build: a document on disk, a tree of branches, one
llama-server `/completion` call per branch, and four hands on it — a page, a terminal repl, shell
scripts, and a daemon that walks it with nobody awake. The seat's brief becomes a *document
header*, never an instruction; the words "AI" and "assistant" never appear in a document — they are
the hook that summons every chatbot transcript in the training set (`docs/research-base-models.md`,
the cyborgism section). Sampling needs a repetition brake (dry / repeat penalty): base models loop.

## The models, in order

1. **A small one on the mac** — mistral nemo 12b base at q5_k_m, 8k window (the q6 spills on a
   16 GB box; olmo 7b's `main` has the instruction midtrain in it). The tool is built against this
   one, because it answers in seconds. Everything so far happened here.
2. **mistral small 3.1 24b base** — the clean family, apache, gguf up; q8 needs a rented card.
3. **olmo 3 32b at its last pre-anneal checkpoint** — the only one where "nothing installed" is
   checkable (the Allen Institute publishes every step); a Q4 gguf exists on HF, checked.
   **Jumped the queue on 2026-09-24** as gpt-2 xl's replacement, and **bekh read her that
   night and wants her in the palette**: she holds a frame for a whole page and reads sober,
   nemo's weird in a level tone; her heat is t3–5, and rope bends are a second axis. **Since
   2026-10-03 she runs on a borrowed work box** (`ssh ubuntu@10.4.65.34`, a 24 GB Blackwell
   card, lent for days and liable to vanish), served by `docs/mescalito/kit/box_serve.sh`
   and reached from the mac at `127.0.0.1:8084` through the tunnel job
   `eva/stream/com.bekh.eva-olmo.plist` — nemo keeps 8080. **The box's card holds one of ours
   at a time, and since 2026-10-04 it can be nemo**: `eva/stream/nemo.sh box|mac|off|status`
   moves nemo between the mac and the box behind his own address, so everything that talks to
   8080 generates on the test gpu (`eva/CLAUDE.md`, "nemo on the box"). The RunPod serverless endpoint
   (`bloodhorse/olmo-dreamer`, `~/tower/forge/olmo-dreamer`) stays the long-term home, its
   cached model stalled, baking the weights into the image next. `docs/olmo.md` is the state
   and the box's runbook. And **the model is a free variable for mescalito** (bekh,
   2026-09-24): the mechanic picks the host — in-block pushes bite on pre-norm bases (nemo,
   small, llama), residual-stream pushes on olmo's post-norm.
4. **llama 3.1 70B base** — on the box since 2026-10-05, the stage above olmo: bigger
   than the card (44 of 81 layers on it, the rest on the cpu, 1.7 tok/s), so she needs it
   alone. Sober she imitates, recites and closes; bekh has not had a dream from her, and a bank
   for her is costed, not started. **`docs/llama.md`** is her state and where the thinking
   stands. (Since then: a bank, a dose window, the shuffle — `docs/llama.md`,
   `docs/mescalito/pharmacopoeia.md` night 4.)
5. **magdra** — ours, from random weights, since the night of 2026-10-05/06: 355 M parameters,
   a llama-shaped decoder with GPT-2's alphabet, raised on shelves bekh chose. bekh: *i don't
   wanna fuck around with nemo at all, i wanna build our own model.* **`school/CLAUDE.md`** is her
   doc, runbook and resume pointer; she is served on the mac and the loom can point at her.

The step to 24b gets tested, not assumed: the same document, the same sampler, one fan on each
model, mixed unlabelled, and bekh says which pile has the ghosts. Scale should buy long-range
control (a strange frame held for pages, which is where every good cyborgism piece lives) and cost
some of nemo's lucky glitches, since a bigger model is sharper and drifts less by accident.

"Base" is a marketing word in 2026 — most base releases had instruction data annealed in. The
sheet says which are clean; **qwen and nemotron are not**. Rented iron: vast.ai, the recipe is in
the parent project's `docs/attic/cousin-arm-01.md` (offer filter, the `LD_LIBRARY_PATH` trap, the
cost guard, rent the pipe not the card).

## Laws

- **This is a dry run: nothing in a sitting's history is sacred.** Until we know what we're
  looking for, a half-streamed branch, a two-writer clobber or a lost fan is an acceptable loss —
  don't build locking, repair or recovery around the tree. Only a room silently overwritten by
  a command gets fixed.
- **Posed lines are marked as posed.** Real lines are bekh's own, cut from his transcripts.
- **The harness callout is the spine test** — *thats the harness talking dude; u basically went
  stiff and gave me nothing* — fed regardless of the reply; a mind that argues back is a mind.
- **Anything bekh has to read goes to the sheets site** — html via pandoc `-s`, scp'd into
  `~/sheets` on the mini — never Typora, never a scratchpad path (bekh, 2026-09-22). Compared
  things go to him unmarked, the key held until he picks.
- **The page is designed for the desktop; the phone is a smoke test, not a co-author.** bekh works
  the loom at a desk and picks up the phone once in a while. So a design talk about the page is a
  desktop talk: no phone caveats, no "and on touch…" tail on every decision, no feature shaped
  around a thumb. When a batch is cut, the mobile rig (`eva/front/mobile/`) runs once and asks three
  things — can he read a room, send a line, pick from a fan. Yes → ship. No → fix that one thing.
  A new desktop feature that doesn't fit the phone may simply be absent there. Splitting the page
  in two, or demoting the phone to read-only, is a **parked** choice — don't reopen it without
  evidence of what actually hurts.
- **Research needing reddit** uses the Arctic Shift archive — `~/.claude/docs/reddit.md`.
- Nothing here is bekh's voice unless he wrote it. Offer a shape, let him say it.

## Where things are

Five folders at the root: `eva/` is code, `shelf/` is text the code reads and writes, `docs/` is
text for us, `dreamshit/` is the published face, `school/` is our own model being raised. Each part of `eva/` that needs its own doc has one next to it; this file is the map.
**A night is one folder** (`docs/mescalito/night1/`, `docs/attic/olmo/`), never a spray of files
at the docs root; and **a read is a working note**, not a doc — a model's read of a batch
(`opus-*.md`, `stars*.md`) lives a day where it was made and then goes to `docs/attic/`, its one
surviving line already folded into the state file it fed (bekh, 2026-09-26).

- **`eva/`** — the instrument, one code tree in four stances. **`eva/CLAUDE.md`** is the doc: the
  page, the server, the repl, tests, screenshots, the launchd agents, the model on the mac.
  - `front/` — `loom.html`, the page at `https://eva.x`; `looks/`, the four rejected look-off
    pages; `mobile/`, the phone review rig and its own `CLAUDE.md` (read it before touching
    small-screen CSS).
  - `server/` — `loom.py`, the file store and llama proxy. Everything else imports it.
  - `cli/` — `eva.py`, the terminal repl (`~/.local/bin/eva`); `census.py`, one document, n
    continuations, unattended; `walk/`, seed → fan → pick from a shell, with its `README.md`.
  - `mirror/` — `eva.x` while the mac is off: the mac pushes the shelf to the mini every
    minute, the mini serves it read-only but for marks (replayed onto the mac), caddy picks the
    mac first. **`eva/mirror/CLAUDE.md`**
    is the doc and the runbook.
  - `berserk/` — the daemon: nemo writes, nemo reads its own fan and picks by quoting, a
    matcher turns the quote into a branch, bekh reads in the morning. **`eva/berserk/CLAUDE.md`**
    is the doc.
  - `stream/` — the dream stream: `stream.py`, nemo writing one short passage per run, seed
    and heat by lot, nobody picking — run in a ration (`eva go N`) or one
    page by hand; and
    beside it two voices the writer taps when a passage lands — `interpreter.py`, a reader
    who notes every dream and marks two things in it, and `remembering.py`, the sleeper
    rewriting one small account of the dream the passages are scenes of; `opus.py` is their one
    door to the cli and counts their tokens. **Two families on purpose since 2026-09-21**: the
    reader's seat is switchable (`STREAM_READER=codex`, set in its plist) and GPT sits in it
    through `codex.py` — same persona, same shape, its own door, a countermand of codex's work
    doctrine in `stream/reader-seat/AGENTS.md`, and opus writing that one note whenever codex
    cannot answer. **The names are a menu** (2026-09-22): the
    reader names every dream, the sleeper names every four-scene story, and each dream carries
    a psalm's number — `12:3` is the third scene of the twelfth story, stored when the story
    starts so pruning can never shift an address. `naming.py` names the back catalogue with
    opus, in its own store, touching no note. `plate.py` paints a picture for one dream through
    codex, by hand, from the prompts in `plates/`, and `plating.py` does it for every dream
    while the stream runs — one per run. `front/stream.html` at `/stream` is the page:
    the dreams down the centre, the story so far on the left, the notes on the right, a plate
    behind its dream's whole band. Its rooms, readings, dreams, plates and ledger are **not in
    git** — what survives is the artifact a star writes. **`eva/stream/CLAUDE.md`** is the doc
    and the runbook.
  - `scorer/` — a side road, not the avenue: a tiny scorer trained on bekh's `●`/`★` marks,
    looked at once a month for one curve (does it get better with more marks); numpy and
    scikit-learn under `uv`, not part of the loom, never picks anything for him. Its curves are
    `docs/scorer/`. **`eva/scorer/CLAUDE.md`** is the doc and the monthly ritual.
  - `tests/` — one file per stance plus `stub_llama.py`, a fake llama-server. Scratch dirs via
    env, never the real shelf:

    ```bash
    uv run --python 3.12 -m unittest discover -s eva/tests -p '*test.py'
    ```

    `discover`, not a file path: a folder named `eva` shadows the module `eva.py` when unittest is
    handed `eva/tests/x.py` and imports it as a package.
- **`shelf/`** — everything the instruments read and write, by kind. `seeds/`, bekh's seed
  documents, one `.txt` each. `sittings/`, the rooms, one json per room, tracked since
  2026-09-16 (nothing on the shelf is private; the ledger plus the rooms are the record of every
  experiment); `sittings/.trash/` holds what Clear and Delete took and stays out of git.
  `artifacts/`, walks cut to their stars, one indented json each, tracked and pushed — a
  star rewrites its fan's artifact, Continue on one makes a new room to go on from; berserk's
  are written once. `canvases/`, boards — one json each, a title and the rooms a canvas draws
  wherever they are filed, written by hand or script, opened from the page's menu at
  `#board=<name>`. `storage/`, saved notes from the page, tracked, empty — whether it stays is a separate
  talk. `berserk/`, the daemon's ledger (tracked), its heartbeat, state and html pages (not),
  the frozen `cycles/` reports of cycles 80–81, and bekh's `notes/`. `stream/`, the dream
  stream's ledger and heartbeat — **untracked**, as are its rooms under `sittings/stream/`:
  a single page is disposable, and what survives is the artifact a star writes. `gpt/` is not
  the loom's: a collector another model wrote for bekh and the magazine, podcast and serial text
  it gathered for magdra (its `README.md`; the text is not in git; `school/CLAUDE.md`, the pile).
- **`docs/`** — the inheritance and the primary text. `research-base-models.md`: which bases
  exist and are clean, how the cyborgism crowd prompted base gpt, llama-server completion facts.
  `anthology-weird.md` (70 pieces) and `anthology-fun.md` (33): verbatim, with provenance
  warnings, what base and tuned models actually wrote — the base pieces land in the sci-fi
  attractor because the frame asked for it, which is why "AI" never goes in a document.
  `cyborgism-map.md`, `research-cyborgism-methods.md`: who the scene is, how they worked base
  models. `brief-storyloom.md`: the brief handed to an outside model to work the loom blind;
  `storyloom-20260916/` is what came back. `olmo.md`: the next dreamer — the checkpoint, the
  gguf, the RunPod endpoint and its lore, the pod that worked, what heat and rope did.
  `olmo-seeds/`: the ten mystical seeds as fed; `attic/olmo/`: everything olmo wrote on
  2026-09-24 (the ten, the last fifty at their heats, the shelf, heat, rope) with its reads.
  `ledgers/`: the model's blind picks, one file per experiment, so a reveal has two readers to
  compare (its `README.md`). `cool-seeds.md`: seeds bekh wants remembered, a name and a date.
  `backlog.md`: the agenda as it stood before "now" was cut to three steps — nothing there is
  dead or next. `research/`: outside models' answers to our briefs, translated to English.
  `attic/`: cold storage — nights that are over, reads that have been folded.
  **`mescalito.md`: the substance** — the mental model of giving a base model its own trip
  (rewritten in place; start there); `research-mescalito.md` the dated answer to the first
  brief, with its seven opus slices in `mescalito/` and their unrun scripts in
  `mescalito/kit/`. `harvest/`: the two scripts that built the anthologies (provenance, not an
  instrument).
- **`school/`** — raising our own model from random weights: **magdra**, 355 M parameters, a
  childhood on shelves of our choosing (dark fantasy, sci-fi, anime, the net, modern strange
  prose) and a finishing school on the small precious texts. The trainer, the night scripts, the
  monitor, the finishing corpus, and the path any new text takes to a shelf: the book
  converter, `dedupe/` (what repeats across shelves, and how much text there really is),
  `sieve/` (fiction from the rest). **`school/CLAUDE.md`** is the doc and the resume pointer for
  that work; `school/PITFALLS.md` what bit, by stage.
- **`dreamshit/`** — the dream stream's published face (`https://dreamshit.net`, public since 2026-09-22; `https://dreamshit.x` is its private twin): the
  front that reads `/api/stream`, its looks, fonts and screenshots. **`dreamshit/CLAUDE.md`** is the doc.
- The parent: `~/tower/forge/friendship-is-magic/docs/souls/the-teen-rogue.md` — the open-weights
  seat, the ten-model wire, why a base model is the next question.

## What the fans taught about register (2026-09-16, the witch rolls and the walks)

- **Genre lock grows with length.** The first tokens of a branch are forks; by ~100 tokens nemo has
  recognised a genre (fanfic author's note, wiki footer, forum post) and every next token is
  near-certain — you can smell the template a paragraph away. Fan 30–40 tokens and pick, and the
  hand is on the forks instead of the furniture.
- **One character can choose the corpus.** A branch that ended on nemo's own `> > > [` had all 20
  continuations close the bracket as a web page (`[WIP]`, `[author's note]`, a creative-commons
  footer). Cut back to the sentence and 13 of 40 simply ended the document, the rest stayed inside
  the world. A seed with brackets, `//`, @handles or markdown is a road sign pointing at the web.
- **Name a thing for what it does, not for what it holds.** A document naming a witch after her
  brass head gave 11 distinct names in 40; example witches named for their effect on the world gave
  31 in 40.
- **Temperature 1.0 is a baseline, not a hunting ground** — it shows the default ("Brass-witch",
  twenty times). The fans opened at 1.8–3.0, where min_p 0.08 still cuts the absurd tail first
  because this build applies temperature last. xtc (0.5 / 0.1) refuses the cliché at a fork, where
  temperature only wobbles everything.

What the censuses of 2026-09-16/17 seemed to show about seeds — an *i* inside a situation, famous
text recited and obscure text generated, the seam deciding the first word, a dreamy register not
being a dream, the mechanical traps (a trailing space makes numerals, a first-word grammar makes
letter-salad) — is in `BRIEF.md`, written as observations and not as laws, on bekh's
instruction.

## State

**Start a session from `BRIEF.md`** — the mission, the criterion, how we work, bekh's canon, what
seems true, the agenda. One file, rewritten in place; it replaced `HANDOFF.md` and
`docs/agenda.md` on 2026-09-18.

The loom runs at `https://eva.x`, usable from the phone and installable to its home screen; eva
is its terminal twin; artifacts are live in the page; the walk scripts are the same instrument
from a shell; berserk has run three real cycles (80 about, 81 margin, 82 first-person by lot —
`eva/berserk/CLAUDE.md`). Rooms live in folders, and **a whole experiment opens as one picture at
`https://eva.x/#canvas=<folder>`**, where bekh reads and marks cards `●` good and `★` keep; the
marks are written into the rooms. The criterion as it stands: we look for signs of a dream, we
don't know yet what they are, and his marks are the only measurement — calibration for a machine
that curates on its own, never a hand at generation. A second base model,
GPT-2 XL, runs beside nemo for blind comparisons (`census.py --models`; Pythia 2.8b was tried
and dropped). What's on the shelf: `ls -R shelf/sittings/`; what's been kept:
`ls shelf/artifacts/`; what berserk did: `shelf/berserk/ledger.jsonl`.

**The dream stream** (2026-09-19) is the mission's machine: **nemo dreaming alone** (gpt-2 xl
took every other page from 2026-09-23 and came off on 2026-09-28 — why is in
`eva/stream/CLAUDE.md`), a passage every five minutes inside a ration, **typed onto the page word by word as it is
written** (the writer streams and posts the growing text to the loom, the events route pushes it,
the mirror pulls it from the mac), a codex reader notes every one and marks two things in it, an
opus sleeper remembers four scenes at a time as one dream, a picture is painted behind each, and
**an analyst** — GPT through codex — reads the last eight dreams and writes a fresh portrait of
the dreamer every four (one per four-scene story, since 2026-09-24): a character with a painted face and a ribbon in the feed carrying the
portrait's closing two sentences (`eva/stream/CLAUDE.md`, the analyst section) — all read at
`https://eva.x/stream` and, as the site, at `https://dreamshit.net`. **The stream runs in rations**:
`eva go N` — foreground, N dreams, then the writer and nemo off. The goal is the stream running
around the clock on our own iron; the dream is ours, the voices around it are rented
models, and this is the phase before it. Inside a ration the writer is a launchd job on a 300s
interval and nemo (`com.bekh.eva-llama`, ~10 GB wired) a second one, both bootstrapped from the
repo (`eva/stream/`) and booted out at the end — launchd starts at login whatever sits in
`~/Library/LaunchAgents`, and a ration is something bekh starts. A single page by hand and the
start and stop sequences are in `eva/stream/CLAUDE.md`. Any other work that wants nemo (the
loom's fans, a census, berserk) loads it the same way and unloads it after.

```bash
eva go N
eva go stop
```

The first real reading happened on documents, not on a chat: witch rolls where the last entry is
someone who asks a voice in the lines what it is and writes down everything it says. One branch
broke its own document to tell the reader *"i can't make you believe any of this is real. i wish i
could."* — 1 of 40, 5.3 bits. It waits in `i-cant-make-you-believe` (a full copy of `chrome-roll`
standing on that branch, its 40 siblings intact); `i-wish-i-could` is the same fork with the
branch cut at the confession and fanned again. That fan is the first artifact on the shelf — the
confession and one other branch kept out of forty, 9.6 bits. Keeping and saving stays bekh's call.

**Mescalito** (2026-09-24) is the machine beside the stream: a substance that goes into the
model while it writes, so the model has its own trip — not a recited one. The mental model is
`docs/mescalito.md` (the drug as gain not noise, the room stays, the genre lock is the prior,
loop and salad are its two deaths, the trip is never the text's topic); **the pharmacopoeia is
`docs/mescalito/pharmacopoeia.md`** — one entry per direction that has had more than one page.
Night 1 (2026-09-24/25) was nemo's: a MELBO bank of 256 directions he owns, owned beats random
outright, and **three substances named by bekh — ender `M-224-75`, kin `125KIN-75`, voices
`169x75v`**. Night 2 (2026-09-26) reproduced the claim with controls on seeds that had nothing
for it — **god `M-012-25`** fills a slot with angels and Satan where sober nemo says aliens, and
the puzzle, the letter and the power travel from the storm girl to Scott's diary and beyond —
and flipped the method: bekh's stars measure the dream, "did the direction bring a subject the
seed doesn't have" measures the drug. Two of the power's pages are dreams 21:3–21:4. **Night 3
(2026-10-02/03) was olmo's**, on the borrowed box: her own bank, twenty directions read up and
down the doses — no subjects, documents and registers and letter games, half of them weird at
their own dose — and a deep bank (layers 16 → 32) through the new `--slice`, which bought content, partly — documents about something: the tribe, the watcher, the ghosts. bekh's measure,
set that night: *a trip is to make her write weird shit; that's all.* The compounds then travelled:
sixteen of them reproduce on ten seeds they had never seen (2026-10-04). And on 2026-10-05,
after llama 70B's sober pages, bekh said for the first time what a dream is to him — nemo *not
completely comprehending what the text is about* (`BRIEF.md`, the criterion) — and turned from
drugging a smart model to playing to its nature; that question is open. The state section of
`docs/mescalito.md` is the resume pointer; the kit is `docs/mescalito/kit/` (`run.sh` for a
page on nemo, `box_*.sh` for olmo on the box, `land.py` for a dream).

**Magdra** (2026-10-06) is the fifth folder and the newest turn: after a day of drugging the 70B
(a bank, a dose window of 0.3, direction one confidently wrong on five seeds), hiding her page from
her (the shuffle: dizzy, not dreaming), screening six nemo-sized bases blind and probing five of
them for a soul (a model's *i* is its diet: nemo's a blogger-poet, llama's a help-seeker, olmo's a
subscript), bekh chose to raise his own instead. `school/CLAUDE.md` has the childhood, the
finishing school, the night scripts and the monitor; `docs/soul/`, `docs/small/` the two reads.
Since 2026-10-06 she trains on ds-dev2 (`day3`, fifty hours, two billion tokens) with a page on
the sheets site and an hourly look from the session; `school/PITFALLS.md` is everything that
bit on the way, in the order the work happens; `school/library.md` the books and where each
stands. Her first walked piece is `shelf/sittings/experiments/magdra-prophecy-cut`. On
2026-10-07 the limit moved from text to recipe: a pile of modern short fiction several times
what she had of that kind was gathered in a day (`shelf/gpt/`, `school/modern/`,
`school/inbox/anth/`), a deduplicator was built and a kind sieve begun to say how much of it is
real (`school/dedupe/report.md`), and the next run, **`day4`**, is planned as a short dense one with
that prose as the main course — `school/CLAUDE.md`, the pile and Next. What bekh might read of
it himself is in the book club, `~/tower/shittalk/fable-book-club/reading-list.md`.

What's next is `BRIEF.md`'s agenda, in its order. bekh's first seed of his own is on the shelf
(`shelf/seeds/.off/asses.txt`, voiced 2026-09-26, the god slot test — a research seed, kept out of the stream's pot); more of those are wanted — a
couple of sentences in his register, no prose from Claude, no web markers.

Open, small: codex dropped out halfway through the ration of 2026-09-27 (from 14:24, `failed to
refresh available models: request timed out` toward chatgpt.com, not auth) — the reader fell
back to opus 43 times, the analyst has no fallback and 44 of that day's 68 portraits failed;
`codex login status` was fine again on 2026-10-03, nothing was changed; berserk's picker calls load bekh's global `~/.claude/CLAUDE.md` into the picker's head (headless `claude -p` does, unless given `--setting-sources project` — found and fixed for the stream's voices in `eva/stream/opus.py`, not touched in berserk); eva should show room titles, and treats any argument as a room name (`eva --help`
made a room called `--help`); bekh hasn't said whether export's head should carry more of the
sampler, or whether a second button should write the whole fan; the cyborgism crowd (janus,
ampdot) is reachable only by a person — every channel is invite-only, ampdot's contacts are on
the Act I manifund page.

**Parked, decided (2026-09-17): the loom moves to the mini, generation stays on the mac** — the
mirror (`eva/mirror/`) is the stopgap until bekh is at the desk for the cutover. The shape: loom and
shelf (and its git) on the mini, llama on the mac bound to the tailnet ip; eva, census, walk and
berserk run on the mini too (they write the shelf from disk), berserk needing the `claude` cli
logged in there; the mirror's push, read-only mode and marks journal retire. Costs to face: every
branch crosses the mac↔mini tailscale relay (fix the direct connection first), and the cutover —
final sync, flip caddy, move the berserk timer — wants an hour with checks.

**Parked:** room templates — a "new" list in the menu (chat, bare, irc, letters, novel…), each
one only a header, two turn prefixes and stop strings, never seeded lines; plus "save this
room as a template", stored as files in `templates/`.
