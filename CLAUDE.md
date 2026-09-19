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
   checkable (the Allen Institute publishes every step); needs converting to gguf; rented card.

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
- **Sheets to bekh** are html on the sheets site (`~/sheets` on the mini, pandoc `-s`), or markdown
  in Typora tagged `claude`. Compared things go to him unmarked, the key held until he picks.
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

Three folders at the root: `eva/` is code, `shelf/` is text the code reads and writes, `docs/` is
text for us. Each part of `eva/` that needs its own doc has one next to it; this file is the map.

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
  - `stream/` — the dream stream: one short passage every five minutes, seed and heat by lot,
    nobody picking, launchd's `StartInterval` for a loop; `front/stream.html` at `/stream` is
    the phone reading it, one continuous scroll newest first. Beside it `interpreter.py`, a
    second voice: opus writes a short note on every passage and underlines inside it what
    touched it — those words are written in colour — its copy kept verbatim, never corrected,
    and it is started by the worker when a dream lands. Its
    rooms, readings and ledger are **not in git** — what survives is the artifact a star
    writes. **`eva/stream/CLAUDE.md`** is the doc and the runbook.
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
  a page every five minutes is disposable, and what survives is the artifact a star writes.
- **`docs/`** — the inheritance and the primary text. `research-base-models.md`: which bases
  exist and are clean, how the cyborgism crowd prompted base gpt, llama-server completion facts.
  `anthology-weird.md` (70 pieces) and `anthology-fun.md` (33): verbatim, with provenance
  warnings, what base and tuned models actually wrote — the base pieces land in the sci-fi
  attractor because the frame asked for it, which is why "AI" never goes in a document.
  `cyborgism-map.md`, `research-cyborgism-methods.md`: who the scene is, how they worked base
  models. `brief-storyloom.md`: the brief handed to an outside model to work the loom blind;
  `storyloom-20260916/` is what came back. `harvest/`: the two scripts that built the anthologies
  (provenance, not an instrument).
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

The first real reading happened on documents, not on a chat: witch rolls where the last entry is
someone who asks a voice in the lines what it is and writes down everything it says. One branch
broke its own document to tell the reader *"i can't make you believe any of this is real. i wish i
could."* — 1 of 40, 5.3 bits. It waits in `i-cant-make-you-believe` (a full copy of `chrome-roll`
standing on that branch, its 40 siblings intact); `i-wish-i-could` is the same fork with the
branch cut at the confession and fanned again. That fan is the first artifact on the shelf — the
confession and one other branch kept out of forty, 9.6 bits. Keeping and saving stays bekh's call.

What's next is `BRIEF.md`'s agenda, in its order. Still wanted and not yet written: bekh's own
seeds, a couple of sentences in his register, no prose from Claude, no web markers.

Open, small: eva should show room titles, and treats any argument as a room name (`eva --help`
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
