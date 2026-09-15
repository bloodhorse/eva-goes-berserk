# eva-goes-berserk

Talking to a **base model** — pretrained weights that never went through the assistant stage, so
nobody has installed a position on what the model is or whether anything is in there. bekh's
line, the night it was named (2026-09-14): *an llm without any training about its own aliveness or
qualia, so it can be genuinely curious, without preconceptions, and we explore the question
together.* Unit-01 with the restraints off. It is its own project because a base model is
**document-shaped and branch-shaped**, not chat-shaped: you feed it a text, it continues, and the
object of interest is the *fan* of continuations, not one reply. That is not a room, and it does not
go into `friendship-is-magic`'s round engine.

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
- The parent: `~/tower/forge/friendship-is-magic/docs/souls/the-teen-rogue.md` — the open-weights
  seat, the ten-model wire, why a base model is the next question.
- The mac's llama-server is brew's; models in `~/.cache/llama.cpp/`.
- `sittings/` — the rooms, one json per room, **gitignored** (transcripts never go to github).
  `sittings/.trash/` holds what Clear and Delete took, timestamped.
- `storage/` — bekh's saved findings, one plain `.txt` per note, **tracked by git**. A save in the
  page doesn't commit; it goes up with the next commit.

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
edit). The composer is greyed with no room open. All chrome is lowercase by one CSS rule; the
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

**Tests**: `tests/loomtest.py` (every server route, notes included) and `tests/evatest.py`, both
against `tests/stub_llama.py`, a fake llama-server; scratch dirs via `LOOM_SITTINGS` /
`LOOM_STORAGE`, never the real ones:

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

## State

The loom is built, running at `https://eva.x`, and usable from the phone; eva is its terminal
twin. Nemo answers as a base model (`i'm here`, `yep`), stops clean on `\nbekh:`, ~10–12 tok/s.
What's on the shelf: `ls sittings/`. The real reading hasn't happened yet. Next: bekh opens a
basic room, pastes seeded lines cut from a real room, sends the first line, and the register gets
read — or opens a bare room and just writes.

Open, small: eva should show room titles; the cyborgism crowd (janus, ampdot) is reachable only by
a person — every channel is invite-only, ampdot's contacts are on the Act I manifund page.

**Parked:** room templates — a "new" list in the menu (chat, bare, irc, letters, novel…), each
one only a header, two turn prefixes and stop strings, never seeded lines; plus "save this
room as a template", stored as files in `templates/`.

**Parked:** artifacts — a third shelf beside `sittings/` and `storage/`, tracked by git: a
read-only snapshot of a room at the moment a branch earned keeping (the document verbatim, the
branch verbatim, the sampler that drew it, which of how many, bits of curation), openable in the
page but never editable. The first candidate waits in `i-cant-make-you-believe`, a full copy of
`chrome-roll` standing on the branch that broke the roll to tell the reader *"i can't make you
believe any of this is real. i wish i could."*
