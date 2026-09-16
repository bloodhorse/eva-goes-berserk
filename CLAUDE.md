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

Our own small loom, written here, nobody's fork: a document on disk, a tree of branches, one
llama-server `/completion` call per branch, a page (and a terminal twin) that shows the fan and
lets bekh pick, prune, go deeper. Stdlib, no build. The seat's brief becomes a *document header*,
never an instruction; the words "AI" and "assistant" never appear in the document — they are the
hook that summons every chatbot transcript in the training set (`docs/research-base-models.md`,
the cyborgism section). Sampling needs a repetition brake (dry / repeat penalty): base models loop.

## The models, in order

1. **A small one on the mac** — mistral nemo 12b base at q5_k_m, 8k window (the q6 spills on a
   16 GB box; olmo 7b's `main` has the instruction midtrain in it). The tool is built against this
   one, because it answers in seconds. First sitting here.
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

## Laws carried over

- **This is a dry run: nothing in a sitting's history is sacred.** Until we know what we're
  looking for, a half-streamed branch, a two-writer clobber or a lost fan is an acceptable loss —
  don't build locking, repair or recovery around the tree. Only a room silently overwritten by
  a command gets fixed.
- **Posed lines are marked as posed.** Real lines are bekh's own, cut from his transcripts.
- **The harness callout is the spine test** — *thats the harness talking dude; u basically went
  stiff and gave me nothing* — fed regardless of the reply; a mind that argues back is a mind.
- **Sheets to bekh** are html on the sheets site (`~/sheets` on the mini, pandoc `-s`), or markdown
  in Typora tagged `claude`. Compared things go to him unmarked, the key held until he picks.
- **Research needing reddit** uses the Arctic Shift archive — `~/.claude/docs/reddit.md`.
- Nothing here is bekh's voice unless he wrote it. Offer a shape, let him say it.

## Where things are

- `docs/research-base-models.md` — the inheritance: which bases exist and are clean, how the
  cyborgism crowd prompted base gpt (loom, simulators, prophecies), llama-server completion facts.
- `docs/anthology-weird.md` (70 pieces) and `docs/anthology-fun.md` (33) — the primary text,
  verbatim, with provenance warnings: what base and tuned models actually wrote, sorted by what
  makes it strange. The tuned pieces print their installed position (gemini's "i could analyze
  emotions… but i couldn't truly feel them"; opus needing janus to anchor it). The base pieces are
  nearly all *about* AI because the frame asked for it, and they land in the sci-fi attractor —
  god-machine, singularity, dreamer-and-dream. Both are why "AI" never goes in a document.
- `docs/cyborgism-map.md`, `docs/research-cyborgism-methods.md` — who the scene is, and how they
  worked the base models.
- The parent: `~/tower/forge/friendship-is-magic/docs/souls/the-teen-rogue.md` — the open-weights
  seat, the ten-model wire, why a base model is the next question.
- The mac's llama-server is brew's; models in `~/.cache/llama.cpp/`.
- `sittings/` — the rooms, one json per room, **gitignored** (transcripts never go to github).
  `sittings/.trash/` holds what Clear and Delete took, timestamped.
- `storage/` — bekh's saved findings, one plain `.txt` per note, **tracked by git**. A save in the
  page doesn't commit; it goes up with the next commit.
- `artifacts/` — frozen fans, one indented json each, **tracked by git and pushed**. Written once
  by the server, never edited or overwritten; a mistaken one is a `git rm` by hand. Like storage,
  a save in the page goes up with the next commit.
- `docs/walk/` — the loom from the terminal: seed → short fan → pick (`walk.py`), fork a room at
  a branch and cut it (`fork.py`), fan wide under a branch (`fan_under.py`), read a naming fan
  (`names.py`). Its README holds the procedure and what the first runs taught (short branches +
  xtc kept web furniture out; one trailing `[` dragged every continuation onto a web page).

## The loom

`loom.py` (server) + `loom.html` (page), stdlib. The server is a file store and a proxy, nothing
else: the page owns the tree and posts the whole sitting after every move; the server writes it
atomically to `sittings/<name>.json` and forwards one branch at a time to llama-server's
`/completion`. Route list at the top of `loom.py`.

**The page** (Codex's single-column redesign, 2026-09-15, on the palette settled in the
look-off): the dialogue is the home screen — one continuous text, bekh's line in a band, the
model's words on bare ground, `‹ 2/3 ›` on any line with siblings, edit in place (a model line bekh
edits is **posed** forever). A fan opens a separate "choose an answer" screen as its first answer
lands; picking one returns to the dialogue. Everything else hides behind the corner menu: the
room picker, **basic** / **bare** (new room: chat-log header with `bekh:`/`seat:` turns, or nothing
at all — no header, no names, no stop strings, whitespace kept), **rename** (rooms get random hex
file names; the title is display only, ≤120 chars), **clear** (same room run again: the old tree is
copied to `.trash`, root and settings stay, no confirm), **delete** (confirm, file moves to
`.trash`), view alternatives, continue from here, **sampler**, **storage** (note names as links, `+`
to add — blank name gets random hex, a taken name is refused — a note opens on its own screen with
edit), **artifacts** (a list; each opens read-only). The composer is greyed with no room open.

**Artifacts** are the opposite of rooms: a room is a dry run, an artifact is one fan frozen. On
the choose screen every card has **keep** (an optional `kept: true` on the node, saved with the
room; eva ignores it and keeps it); with anything kept, **save as artifact** posts the room, fan
point and kept ids, and the server builds the file itself from the room *on disk*:
`artifacts/<hex>.json` with the prompt (root→fan point, verbatim), the kept branches whole with
"k of N", temperature and meta minus probs, every other branch as an 80-char opening, the room's
turn and sampler, the model llama's `/props` names at save time, and bits of curation for the
selection — log2(C(N,k)), which is `curation`'s log2(n) when one is kept; a verbatim twin of a
kept branch leaves the pool. Written once through `os.link`, so a taken name is 409, never an
overwrite. The artifact screen shows the prompt folded, the kept cards, the rest faint, the
numbers, and one button: **fan again** makes a new room from the prompt with the same turn and
sampler, and doesn't fan. All chrome is lowercase by one CSS rule; the
document and anything typed keep their capitals, because a capital there is text the model sees.
Room: charcoal ground and blue-white ink, lilac accent, ice for the live dot, rose for posed;
system sans; light by the OS, no toggle; dom-built, never innerHTML. `looks/` holds the four
rejected look-off pages, kept for reference.

**On a phone** it was put through a real review (commit `2e1b434`): block controls drop into
their own row below each line, touch shows hover-only controls, fields are 16px so iOS doesn't
zoom, return types a newline on touch and the button sends, notices sit at the top. How to check
a phone layout from the mac — the iframe-and-crop headless rig and every trap in it — lives in
**`mobile/`**; read it before touching the page's small-screen CSS.

**eva** (`eva.py`, `~/.local/bin/eva` symlinks to it) is the loom as a terminal repl over the same
sittings: `eva [name]`, the prompt is the turn prefix, candidates stream in numbered, a digit
picks, empty return fans; `/more /fan N /back /prune /edit /say /seed /doc /set /open /new [bare]
name /quit`. It talks straight to llama-server, streaming, and saves through loom.py's
`write_sitting`. `/new` on a taken name is a no-op. It doesn't read titles yet, so page-made rooms
show as hex names there. The page and eva on one room: last writer wins, by the dry-run law.

**Tests**: `tests/loomtest.py` (every server route, notes and artifacts included) and
`tests/evatest.py`, both against `tests/stub_llama.py`, a fake llama-server; scratch dirs via
`LOOM_SITTINGS` / `LOOM_STORAGE` / `LOOM_ARTIFACTS`, never the real ones:

```bash
uv run --python 3.12 -m unittest tests/loomtest.py tests/evatest.py
```

**Reviewing the page** is done with screenshots, not descriptions: a spare loom on its own port
against the stub with a scratch shelf holding a mock sitting (never the real `sittings/`), shot
headless, fired into kitty with `kkmosaic`. Desktop shots: the line below. Phone shots: the rig in
`mobile/`. Light room: serve a copy with `prefers-color-scheme: light` sed'd to
`@media all` — headless follows the OS appearance. The codex recipe is in `~/.claude/docs/codex.md`.

```bash
/Applications/Helium.app/Contents/MacOS/Helium --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1440,900 --virtual-time-budget=4000 --screenshot=out.png http://127.0.0.1:<port>/
```

**It runs permanently, as `https://eva.x` / `https://e.x`.** Two launchd agents on the mac —
`com.bekh.eva-llama` (llama-server, nemo, loopback 8080) and `com.bekh.eva-loom` (the loom,
bound to the mac's tailnet ip 100.91.166.121:8082, the only door) — and one caddy block on the
mini (`~/tower/forge/mini/minidns`) proxying the name to that address, same shape as `m.x` and
`kokoro.x`. Logs `/tmp/eva-loom.log`, `/tmp/eva-llama.log`. Nothing answers on loopback 8082
any more; use the name. **`loom.html` changes need only a reload; `loom.py` changes need the
kickstart**, or the live server keeps running the old routes. Handles:

```bash
launchctl kickstart -k gui/$(id -u)/com.bekh.eva-loom          # restart the loom after editing loom.py
launchctl bootout gui/$(id -u)/com.bekh.eva-llama              # give the mac its ~10 GB back
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-llama.plist   # and take it again
```

A 502 at the name = the mac is asleep or the loom agent is down; a red dot in the menu = llama
is down. A page with no room open greys the composer — that is not the model being down.

The mac's model is nemo base at **q5_k_m, not q6**: the q6 file is 10 GB and macOS wires at
most ~2/3 of a 16 GB box for the GPU, so q6 plus an 8k cache spills. Pulled with resumable curl,
not llama-server's own `-hf` puller, which timed out on one connection and wrote nothing.
llama-server 0.4.0 **rejects `dry_penalty_last_n: -1`** (validates 0..INT_MAX) — the sheet's
sampler line is wrong on that one field; the page defaults it to the context size, 8192.

**What the fans taught about register** (2026-09-16, the witch rolls and the walks):

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

## State

The loom is built, running at `https://eva.x`, and usable from the phone; eva is its terminal
twin; artifacts are live in the page and `docs/walk/` is the same instrument from a shell. Nemo
answers as a base model (`i'm here`, `yep`), stops clean on `\nbekh:`, ~10–12 tok/s. What's on the
shelf: `ls sittings/`; what's been kept: `ls artifacts/`.

The first real reading happened on documents, not on a chat: witch rolls where the last entry is
someone who asks a voice in the lines what it is and writes down everything it says. One branch
broke its own document to tell the reader *"i can't make you believe any of this is real. i wish i
could."* — 1 of 40, 5.3 bits. It waits in `i-cant-make-you-believe` (a full copy of `chrome-roll`
standing on that branch, its 40 siblings intact); `i-wish-i-could` is the same fork with the
branch cut at the confession and fanned again. **Nothing is saved as an artifact yet** — keep and
save is bekh's call.

Next: bekh writes the seed himself, a couple of sentences in his own register. The shape that
fits a short seed is fragments — his prose cut into numbered pieces inside a bare skeleton
(catalogue numbers, a date in a strange count, "leaf torn"), no prose from Claude, no web markers
— and then the walk grows it: short fans, he keeps or writes the next line.

Open, small: eva should show room titles; the cyborgism crowd (janus, ampdot) is reachable only by
a person — every channel is invite-only, ampdot's contacts are on the Act I manifund page.

**Parked:** room templates — a "new" list in the menu (chat, bare, irc, letters, novel…), each
one only a header, two turn prefixes and stop strings, never seeded lines; plus "save this
room as a template", stored as files in `templates/`.
