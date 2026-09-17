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
Route list at the top of the file. The one route that reads something it never wrote is
`/api/berserk` — the daemon's ledger, `LOOM_LEDGER`, alongside the room. Env: `LOOM_HOST`,
`LOOM_PORT`, `LOOM_LLAMA`, and the scratch-dir overrides `LOOM_SITTINGS` / `LOOM_STORAGE` /
`LOOM_ARTIFACTS` / `LOOM_LEDGER` / `LOOM_PAGE` that the tests and the mobile rig set —
production leaves them alone.

**A room's name IS its path** under `sittings/`, without the `.json`:
`experiments/basin/smoke-01` is one file two folders deep, and that string is also the `name`
inside the file, what `/api/sitting?name=` takes and what the page shows. A folder exists
because a room is in it — nothing on disk declares one, there are no index files, and a folder
the last room leaves is dropped. One validator, `name_ok`, stands in front of every name that
becomes a file (`sitting_path` raises on anything it refuses): segments of `[A-Za-z0-9_.-]`,
up to 64 each, no empty segment and **no segment starting with a dot**, which is what keeps
`.` , `..` and `.trash` unaddressable however they are spelled. An artifact name is still one
flat segment — artifacts are not filed. `POST /api/move {"from","to"}` moves a room or a whole
folder (rename is a move): one `os.rename`, folders made on the way, the emptied ones pruned up
to but never including the shelf root, `name` re-stamped inside every file that moved and
`updated` left alone. 400 on a path that doesn't read or a folder into itself, 404 on nothing
there, 409 on a name already taken by a room **or** a folder. `.trash` mirrors the folders, so
two rooms called `smoke-01` can both be thrown away.

Two routes exist only for the canvas. `GET /api/folder?name=<folder>` hands over every room
under that folder, sub-folders included, sorted by name — each with its `root`, `current`,
`berserk` flag and its nodes cut to `parent`, `kind`, `text` and, where they are there,
`posed`, `kept`, `temperature` (`meta.params.temperature`, falling back to `meta.temperature`)
and `model` (`meta.model`, either llama's `/props` object or a bare file name). `probs` and the
rest of meta are dropped **on the server**: a folder is thirty rooms of thirty branches and
one fan's probabilities are 40 KB, and the cost here is the wire, not the render. `name_ok`
as everywhere, 404 on a folder with no rooms, `.trash` unaddressable. `POST /api/keep
{"room", "node", "kept"}` re-reads that room, sets or deletes `kept` on one **model** node and
writes it with `write_sitting` — the same flag the choose screen's keep leaves, so a harvest
made on the canvas is in the rooms and in git. Read and write sit next to each other and there
is no lock: a census appending to that room in the same instant loses a branch or loses the
flag, which is the dry-run law and not a bug to fix.

**A bare name still finds a filed room.** The berserk ledger names a room the way the daemon
made it (`berserk-c80-p01`) and every `#tree=` link the sheets pages ever printed spells it
that way, so `resolve_room` takes a path first and then, for a name with no slash, the unique
room whose last segment matches — two rooms with one leaf is a question, not a pick, and comes
back 404. `/api/berserk`, `/api/berserk/text`, the `berserk` flag on the listing and
`berserk.load` (which is how `anthology.py` opens a room) all go through it.

## The page

`front/loom.html` (Codex's single-column redesign, 2026-09-15, on the palette settled in the
look-off): the dialogue is the home screen — one continuous text, bekh's line in a band, the
model's words on bare ground, **the fork mark** `⌥ 3/40` on any line with siblings — one tap opens
that line's own fan on the choose screen, because a fan of forty is read as a pile, not stepped
through one at a time (the `‹ ›` walk it replaced is gone) — edit in place (a model line bekh
edits is **posed** forever). A fan opens a separate "choose an answer" screen as its first answer
lands; picking one returns to the dialogue. Everything else hides behind the corner menu: the
**room tree** (the shelf's folders, drawn from the room paths and from nothing else — folders
first then rooms, alphabetical, `▸`/`▾`, closed by default, which folds are open remembered
per browser in `localStorage`; the open room is named once at the top and marked in the accent
on its own row, and the folders on the way to it are unfolded for it), **basic** / **bare**
(new room: chat-log header with `bekh:`/`seat:` turns, or nothing at all — no header, no names,
no stop strings, whitespace kept; the field under those two buttons says where it goes — blank
is a random name at the top of the shelf, `basin/` a random name in that folder, `basin/s-01`
that room), **rename** (rooms get random hex file names; the title is display only, ≤120 chars),
**move to…** (on the open room from the toolrow, on a folder from a `move` beside it: a sheet
listing the folders that exist plus one field for a path that doesn't — a choice fills the
field, confirming posts `/api/move`, and a room that moves under the page's feet is re-opened
from its new path, because the name inside the file is what the next save posts back),
**clear** (same room run again: the old tree is
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

**The same screen draws a berserk walk**, because an artifact is the wrong record of one: it
keeps the branches nobody took as 80-character openings and not a word of what the reader said,
and those two are the point. The record is the **room plus the ledger**, and
`GET /api/berserk?name=<room>` hands both over — the room whole, its fork rows in fork order
with the `lead` each fan was finishing computed per row, and the document root→`current` as one
string; `GET /api/berserk/text?name=` is that string alone, which is what **export** reads and
links to. 404 on a room with no fork rows, and a half-written last ledger line is skipped rather
than raised, because berserk appends to that file for hours while somebody watches. The way in is
the **tree** control beside the open room's name — shown when that room's `/api/sittings` row
says `berserk: true`, one ledger read for the whole list — or the url `#tree=<room>`, which is
what the sheets page links to and which takes a path or the bare name the ledger keeps,
wherever the room has since been filed. Top to bottom: the seed as the folded card, then per fan its lead
in dim mono, the branches **whole** and lettered `a b c` in the order the reader saw them (the one
taken solid on the accent, the rest dimmer, an empty one a single `(empty)` line, each carrying
its margin note under `margin`), and under the row every ask that fan cost — `attempt 2 ·
reshuffled`, `widened to 10`, what was said and why, `→ e` or `not in the fan`, `random → c`. The
accent runs branch taken → those attempts → the next fan's lead → its branches, which is why no
connector is ever drawn across a paragraph of text. Rows written before `tries` existed have their
attempts rebuilt out of `wished` exactly as the sheets page rebuilds them. Nothing about opus,
substring, agree or bits appears anywhere: two renderings of one record, and the resolver is not a
character in either.

**The canvas is a whole experiment at once** — one folder of rooms as a picture, on the third
screen that opts out of the reading column. It exists because a census of thirty rooms of
thirty branches cannot be read a fan at a time: what is being looked for is which fans went
somewhere, and that is a *shape*. Ways in: a `canvas` control on every folder row of the room
tree, beside `move`, and the url `#canvas=<folder path>`; a back arrow returns to the
dialogue. The folder arrives in one `/api/folder` call and never streams. A title node, an
arrow to each room's seed card (the seed's tail, `whole seed ▸`, `open room`, and `tree ↗` on
a room berserk walked), and under it the fan as a grid of **uniform cards**, `CARD_H = 185`
world px in one constant. Seed blocks are packed as six masonry columns, each next room into
the shortest one, so a room that collapsed to one brick leaves no hole. **Any tree, not only a
census**: a branch somebody fanned under gets a `▾ n` mark and its own framed grid below, with
a measured arrow from the card to that frame — accent when that branch is on the path
root→`current`, dim when the room walked elsewhere — and a berserk beat is drawn as a
one-line rose card between the branch taken and the fan under it, so a night reads as a
staircase of fans. **Look-alikes** (same first 40 characters, whitespace collapsed,
casefolded) collapse into one stacked card, `‹ ›` or the arrow keys flipping the members under
the pointer, the common prefix dim and each member's own tail in full ink; the **cold heat
ramp** (`--heat-1…6`, slate → dusky magenta, its legend in the bar) says how big a cluster is
and no `×N` is written anywhere. Zoomed out — below `textK()`, which reads the viewport — the
cards drop their ink and become bricks coloured by that ramp; **kept is ice** in both modes.
**keep** writes through `/api/keep`, optimistically, and reverts with a notice if the server
refuses. **reveal** appears only when a folder holds two or more models, is off by default and
is never remembered: it puts a model tag and a patterned top edge (solid / dashed / dotted —
pattern, not hue, because the ramp owns every cold colour) on each card, a legend in the bar
and a `kept by model:` line. Drag to pan, wheel or pinch to zoom about the pointer, `f`/`fit`,
a seed heading flies to its block, `esc` closes an opened card or fits; nothing on the surface
is selectable and the cursor stays the ordinary arrow. `open room` goes to `#room=<path>` —
the page's third address — so the browser's own back button comes home to `#canvas=` with the
camera where it was (kept per folder in `sessionStorage`). `reload` re-reads the folder while
a census is still writing and keeps the camera.

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
eva on one room: last writer wins, by the dry-run law. **Names are paths**, through loom's own
validator and never a second copy of it: `eva experiments/basin/smoke-01`,
`/new bare experiments/basin/smoke-02`, `/open experiments/witch/witch-bekh-10` — the folders on
the way are made by `write_sitting`, and the shelf listing spells every room as its path.

**census** (`cli/census.py`): one document, n continuations across a set of temperatures,
unattended; the room is left standing on its root with every branch hanging off it, which is the
shape the choose screen already reads. `--name` is a path too
(`--name experiments/basin/free-01`), which is how a night of thirty censuses files itself as
it is made instead of landing in one flat list. **`--models nemo=URL,pythia=URL,gpt2=URL`**
turns a census into a blind comparison: the branches are split evenly between the servers,
each model's share walking the same round-robin through `--temps`, and every branch stamped
`meta.model` — the key, in the file and nowhere on the choose screen, so the pile is read
first and told apart after. The order the branches are **written in is shuffled**, seeded
from the room name, so position carries nothing and a rerun under that name lays out the
same way; a model whose `/props` window can't hold the seed plus `n_predict` is skipped with
a line on stderr and its share simply missing, never quietly truncated. **`--tail N`** cuts
the document to its last N tokens (the first model's tokenizer, forward to a whole
paragraph, sentences where no paragraph break falls in range) **before** the room is made,
so the root IS what every model was handed — a long seed is a style lesson, and the fan
spends itself imitating prose instead of standing on the seam.

**walk** (`cli/walk/`): seed → short fan → pick (`walk.py`), fork a room at a branch and cut it
(`fork.py`), fan wide under a branch (`fan_under.py`), read a naming fan (`names.py`). Its README
holds the procedure and what the first runs taught. All of them bypass the live loom and write the
file directly — don't have the room open in the page while one runs.

## Tests

`tests/` — `loomtest.py` (every server route, notes and artifacts included, plus `Canvas` and
`Keep` for the two canvas routes, and `Folders`:
the recursive listing with the bin hidden, every rule a path has, the move of a room and of a
folder with its collisions and its pruning, and a walked room answering to its bare name after
it moves), `evatest.py`,
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
