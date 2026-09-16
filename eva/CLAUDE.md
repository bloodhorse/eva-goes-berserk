# eva — the loom

The instrument, in four stances over one file format: `front/loom.html` (the page), `server/loom.py`
(the store and the proxy), `cli/` (the repl, the census, the walk scripts) and `berserk/` (the
daemon — its own `CLAUDE.md`). Everything imports `server/loom.py`; nothing else knows how a
sitting is written. The rooms, the artifacts and the seeds live on `../shelf/`; `loom.SHELF` is
the one place that path is spelled. Read the root `CLAUDE.md` first for what this is for.

## The server

`server/loom.py`, stdlib, is a file store and a proxy, nothing else: the page owns the tree and
posts the whole sitting after every move; the server writes it atomically to
`shelf/sittings/<name>.json` and forwards one branch at a time to llama-server's `/completion`.
Route list at the top of the file. Env: `LOOM_HOST`, `LOOM_PORT`, `LOOM_LLAMA`, and the
scratch-dir overrides `LOOM_SITTINGS` / `LOOM_STORAGE` / `LOOM_ARTIFACTS` / `LOOM_PAGE` that the
tests and the mobile rig set — production leaves them alone.

## The page

`front/loom.html` (Codex's single-column redesign, 2026-09-15, on the palette settled in the
look-off): the dialogue is the home screen — one continuous text, bekh's line in a band, the
model's words on bare ground, **the fork mark** `⌥ 3/40` on any line with siblings — one tap opens
that line's own fan on the choose screen, because a fan of forty is read as a pile, not stepped
through one at a time (the `‹ ›` walk it replaced is gone) — edit in place (a model line bekh
edits is **posed** forever). A fan opens a separate "choose an answer" screen as its first answer
lands; picking one returns to the dialogue. Everything else hides behind the corner menu: the
room picker, **basic** / **bare** (new room: chat-log header with `bekh:`/`seat:` turns, or nothing
at all — no header, no names, no stop strings, whitespace kept), **rename** (rooms get random hex
file names; the title is display only, ≤120 chars), **clear** (same room run again: the old tree is
copied to `.trash`, root and settings stay, no confirm), **delete** (confirm, file moves to
`.trash`), view alternatives, continue from here, **sampler**, **storage** (note names as links, `+`
to add — blank name gets random hex, a taken name is refused — a note opens on its own screen with
edit), **artifacts** (a list; each opens read-only). The composer is greyed with no room open.

**Artifacts** are the opposite of rooms: a room is a dry run, an artifact is a **walk** frozen —
the document it started from and every fork along the way. On the choose screen every card has
**keep** (an optional `kept: true` on the node, saved with the room; eva ignores it and keeps it),
and that is the whole gesture: he keeps as he goes, picks, walks on, keeps more at the next fork.
**Save as artifact** posts the room, the fan he has open and the ids kept in it; the server walks
the path root→`current` and builds the file itself from the room *on disk*:
`shelf/artifacts/<hex>.json` with the prompt (root→the first fan point, verbatim), the room's turn
and sampler, the model llama's `/props` names at save time, and one **step** per fork — the line
taken and the branches kept beside it whole with "k of N", temperature and meta minus probs, every
other branch of that fan as an 80-char opening (evidence of what was on offer, never drawn), and
`lead`, the text between the last line taken and this fan point, so prompt + every step's lead +
line taken is the document again. The open fan he saves from is always the last step, with no line
taken yet; a fan of one is not a step; a step he kept nothing in still is one. Bits per step are
log2(C(n,k)) with k counting the line taken alongside the keeps — `curation`'s log2(n) when nothing
was kept beside it — and the walk's total is the steps added, because each fork is its own choice.
A verbatim twin of a named branch leaves the pool. Written once through `os.link`, so a taken name
is 409, never an overwrite.

**The artifact screen is that walk as a tree**, and the one screen that opts out of the
`--reading` column: a tree is a picture, not prose, so it takes the whole window and a branch is
shown whole instead of cut. The prompt sits as a folded card at the top, then one row per step —
the line taken in a solid panel, the kept branches flanking it, dimmer — with the connectors
measured after layout and drawn as svg (solid accent down the path taken, dashed for the keeps),
redrawn on a resize, a theme flip and when the fonts land. A step wider than the screen scrolls
inside the tree pane, the only thing on the page allowed to; under it a foot line (steps, kept of
total, bits, model, temperature range) and the sampler, turn, date and room it came from. Two
buttons: **export** opens the walk as one document on **its own screen** — monospace, pre-wrap,
the lowercase rule lifted, with **copy**, **link** and **download** in its bar and back returning
to the tree. The text is **the server's**: `GET /api/artifact/text?name=` builds it in `loom.py`
from the file on disk and serves it as plain text, so the screen, the download and the link are one
string with one implementation the tests can hold — the page had its own copy of the concatenation
for a day, which is how two answers to "what does an artifact read like" drift. **Link** opens
that url in a tab: the thing that can be sent to a phone or pasted into sheets. The document is the
prompt, then every step's lead and the line taken, joined with nothing between them, under a short
head naming the model and the few sampler numbers that decide the register (the branches kept
beside the path are left out: it is the story, not the fan) — then, under the document, the
branches kept at the **open fork it ends on**, because nothing was taken there and those keeps are
the only ending there is; without them a walk of one step exported as the prompt alone, cut off
mid-word. Each is marked `[generation begins]` and nothing more — which branch of how many, at what
temperature, is the tree's job — and the text goes out untrimmed, as plain text, because a base
model's document is full of `> > >`, `//` and stray brackets and a markdown reader eats exactly
those. **Fan again** makes a new room from the prompt with the same turn and sampler, and doesn't
fan. An artifact written before walks existed has no `steps` and is read as a walk of one step with
nothing taken — `steps` is the whole test, and no file on the shelf is ever rewritten.

All chrome is lowercase by one CSS rule; the document, anything typed and the export screen keep
their capitals, because a capital there is text the model sees. Room: charcoal ground and
blue-white ink, lilac accent, ice for the live dot, rose for posed; system sans; light by the OS,
no toggle; dom-built, never innerHTML. `front/looks/` holds the four rejected look-off pages.

**On a phone** it was put through a real review (commit `2e1b434`): block controls drop into
their own row below each line, touch shows hover-only controls, fields are 16px so iOS doesn't
zoom, return types a newline on touch and the button sends, notices sit at the top. How to check
a phone layout from the mac — the iframe-and-crop headless rig and every trap in it — lives in
**`front/mobile/`**; read its `CLAUDE.md` before touching the page's small-screen CSS.

## The terminal

**eva** (`cli/eva.py`, `~/.local/bin/eva` symlinks to it) is the loom as a repl over the same
sittings: `eva [name]`, the prompt is the turn prefix, candidates stream in numbered, a digit
picks, empty return fans; `/more /fan N /back /prune /edit /say /seed /doc /set /open /new [bare]
name /quit`. It talks straight to llama-server, streaming, and saves through `write_sitting`.
`/new` on a taken name is a no-op. It doesn't read titles yet, so page-made rooms show as hex
names there, and it takes any argument as a room name (`eva --help` made a room). The page and
eva on one room: last writer wins, by the dry-run law.

**census** (`cli/census.py`): one document, n continuations across a set of temperatures,
unattended; the room is left standing on its root with every branch hanging off it, which is the
shape the choose screen already reads.

**walk** (`cli/walk/`): seed → short fan → pick (`walk.py`), fork a room at a branch and cut it
(`fork.py`), fan wide under a branch (`fan_under.py`), read a naming fan (`names.py`). Its README
holds the procedure and what the first runs taught. All of them bypass the live loom and write the
file directly — don't have the room open in the page while one runs.

## Tests

`tests/` — `loomtest.py` (every server route, notes and artifacts included), `evatest.py`,
`censustest.py`, `berserktest.py`, all against `tests/stub_llama.py`, a fake llama-server; scratch
dirs via the env overrides, never the real shelf. One process, all four:

```bash
uv run --python 3.12 -m unittest discover -s eva/tests -p '*test.py'
```

`discover`, because `unittest eva/tests/loomtest.py` imports the file as `eva.tests.loomtest` and
the folder `eva/` then shadows the module `eva.py` for every `import eva` after it. The stub's
`SEEN` list is one per process, so markers in one test file must not be substrings of another's.

**Reviewing the page** is done with screenshots, not descriptions: a spare loom on its own port
against the stub with a scratch shelf holding a mock sitting (never the real `shelf/sittings/`),
shot headless, fired into kitty with `kkmosaic`. Desktop shots: the line below. Phone shots: the
rig in `front/mobile/`. Light room: serve a copy with `prefers-color-scheme: light` sed'd to
`@media all` — headless follows the OS appearance. The codex recipe is in `~/.claude/docs/codex.md`.

```bash
/Applications/Helium.app/Contents/MacOS/Helium --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1440,900 --virtual-time-budget=4000 --screenshot=out.png http://127.0.0.1:<port>/
```

## It runs permanently, as `https://eva.x` / `https://e.x`

Three launchd agents on the mac — `com.bekh.eva-llama` (llama-server, nemo, loopback 8080),
`com.bekh.eva-loom` (the loom, bound to the mac's tailnet ip 100.91.166.121:8082, the only door)
and `com.bekh.eva-berserk` (one cycle per kickstart, never at load; see `berserk/CLAUDE.md`) — and
one caddy block on the mini (`~/tower/forge/mini/minidns`) proxying the name to that address, same
shape as `m.x` and `kokoro.x`. Logs `/tmp/eva-loom.log`, `/tmp/eva-llama.log`,
`/tmp/eva-berserk.log`. Nothing answers on loopback 8082; use the name. **`loom.html` changes need
only a reload; `loom.py` changes need the kickstart**, or the live server keeps running the old
routes. **A plist edit needs bootout + bootstrap** — kickstart restarts the process from
launchd's cached copy of the plist, which is how the loom died on a stale path once.

```bash
launchctl kickstart -k gui/$(id -u)/com.bekh.eva-loom          # restart the loom after editing loom.py
launchctl bootout gui/$(id -u)/com.bekh.eva-loom; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-loom.plist   # after editing the plist
launchctl bootout gui/$(id -u)/com.bekh.eva-llama              # give the mac its ~10 GB back
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-llama.plist   # and take it again
```

A 502 at the name = the mac is asleep or the loom agent is down; a red dot in the menu = llama
is down. A page with no room open greys the composer — that is not the model being down.

The mac's llama-server is brew's; models in `~/.cache/llama.cpp/`. The model is nemo base at
**q5_k_m, not q6**: the q6 file is 10 GB and macOS wires at most ~2/3 of a 16 GB box for the GPU,
so q6 plus an 8k cache spills. Pulled with resumable curl, not llama-server's own `-hf` puller,
which timed out on one connection and wrote nothing. Nemo answers as a base model (`i'm here`,
`yep`), stops clean on `\nbekh:`, ~10–12 tok/s. llama-server 0.4.0 **rejects
`dry_penalty_last_n: -1`** (validates 0..INT_MAX) — the sheet's sampler line is wrong on that one
field; the page defaults it to the context size, 8192.
