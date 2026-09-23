# eva — the loom

The instrument, in five stances over one file format: `front/loom.html` (the page), `server/loom.py`
(the store and the proxy), `cli/` (the repl, the census, the walk scripts), `berserk/` (the
daemon — its own `CLAUDE.md`) and `stream/` (the dream stream — its own `CLAUDE.md`).
Everything imports `server/loom.py`; nothing else knows how a
sitting is written. The rooms, the artifacts and the seeds live on `../shelf/`; `loom.SHELF` is
the one place that path is spelled. Read the root `CLAUDE.md` first for what this is for.

## The server

`server/loom.py`, stdlib, is a file store and a proxy, nothing else: the page owns the tree and
posts the whole sitting after every move; the server writes it atomically to
`shelf/sittings/<name>.json` and forwards one branch at a time to llama-server's `/completion`.
Route list at the top of the file. Two routes read something the server never wrote:
`/api/berserk` — the daemon's ledger, `LOOM_LEDGER`, alongside the room — and `/api/stream`,
which reads the stream worker's heartbeat (`STREAM_DIR`) alongside the rooms under
`sittings/stream/`; `/stream` serves `front/stream.html` beside it. Two more read the analyst's
portraits (`STREAM_DIR/portraits/<STREAM_ANALYST_SEAT>/`, the public seat only, `analyst`):
**`GET /api/stream/portraits`**, every version newest first as `{id, ts, line, text, dreams,
rooms}`, and **`GET /api/stream/portrait?id=2026-09-23/1831`**, one of them (404 none, 400 an id
`name_ok` refuses) — and `/api/stream` hangs the same object as `portrait` on the page each
version was written right after. One route never returns:
**`/api/stream/events`** is `text/event-stream`, held open, saying which rooms changed within
~2s of anything landing, so a reader is pushed to instead of polling — a GET, so the mirror
serves it too. **`POST /api/stream/live`** takes the stream writer's `{text so far, seed, done}`
while nemo writes, holds it in memory only and pushes it down that connection as `event: live`
(403 on the mirror, which pulls the mac's through `LOOM_LIVE_UPSTREAM`). Env: `LOOM_HOST`,
`LOOM_PORT`, `LOOM_LLAMA`, and the scratch-dir overrides `LOOM_SITTINGS` / `LOOM_STORAGE` /
`LOOM_ARTIFACTS` / `LOOM_LEDGER` / `LOOM_CANVASES` / `LOOM_PAGE` / `LOOM_STREAM_PAGE` /
`STREAM_DIR` that the tests and the rigs set — production leaves them alone.

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

Four routes exist only for the canvas. `GET /api/folder?name=<folder>` hands over every room
under that folder, sub-folders included, sorted by name — each with its `root`, `current`,
`berserk` flag and its nodes cut to `parent`, `kind`, `text` and, where they are there,
`posed`, `kept`, `good`, `temperature` (`meta.params.temperature`, falling back to `meta.temperature`)
and `model` (`meta.model`, either llama's `/props` object or a bare file name). `probs` and the
rest of meta are dropped **on the server**: a folder is thirty rooms of thirty branches and
one fan's probabilities are 40 KB, and the cost here is the wire, not the render. `name_ok`
as everywhere, 404 on a folder with no rooms, `.trash` unaddressable. **Boards** are canvases
saved as files: `shelf/canvases/<name>.json` holds `{"title", "rooms": [...]}`, written by hand or
by a script (there is no UI that makes one), its name its path without `.json` through the same
`name_ok`. `GET /api/canvases` lists them as `{name, title, folder}` by name; `GET
/api/canvas?name=<board>` is `/api/folder`'s payload plus `board` and `title`, built from the
listed rooms in the file's order by **the same builder** (`canvas_rooms`, which the folder route
calls too) — a room is spelled as a path or a bare leaf (`resolve_room`), one that has gone is
skipped, one listed twice is drawn once; 404 for no board or one with no room left, 400 on a bad
name. `POST /api/mark
{"room", "node", "mark": "kept"|"good", "on"}` re-reads that room, sets or deletes that flag on
one **model** node and writes it with `write_sitting` — the same flags the choose screen leaves,
so a harvest made on the canvas is in the rooms and in git. Two marks, and **a branch wears at
most one** (2026-09-17): `kept` is what an artifact is built out of, `good` only says it was
kind of nice and he wouldn't keep it, and turning either on pops the other in the same
read-write — `set_mark` is the one place that rule lives, so no caller can leave a card wearing
both, and the answer carries the state of *both* marks after the write for the page to repaint
from. Turning a mark off touches nothing else. A circle that clears a star is a star coming off,
so that path syncs the fan's artifact like any other unkeep; nothing else downstream —
`build_artifact` above all — has heard of `good`. `POST /api/keep {"room","node","kept"}` is that
route spelled the old way and is one line, never a second copy of the write. Read and write sit next to each other and there
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
through one at a time (the `‹ ›` walk it replaced is gone). A line's other controls sit behind
**`⁖`** at the foot of its right margin, shown on hover (2026-09-18 — the left gutter that held
them is gone and the text took its width back): one small popover, `edit` / `spin off` /
`tokens`, fixed to the window, closed by esc, a click outside or the glyph again, following its
glyph on a scroll; on the phone `⁖` sits in the row under the line beside the fork mark, and the
mirror offers tokens alone. Edit is in place (a model line bekh edits is **posed** forever). The
dialogue **trims the newlines at both ends of every block on screen** — a wire or berserk room
keeps the document's seams in its nodes (`…\n`, `\n\n…`) and under pre-wrap they drew empty
rows a click could land in; the node, the document sent to the model and the edit box keep them,
and the trim edits only the edge text nodes, so painted tokens stay where they were. A fan opens a separate "choose an answer" screen as its first answer
lands; picking one returns to the dialogue. That screen heads the cards with the last two sentences
of the text they continue (one more when those are under ~80 characters, capped at 400), fixed
while the cards scroll. Beside the corner menu a fan icon opens the
alternatives in one click — on the canvas it stays in the corner, greyed, since there is no line to fan there, and the canvas bar reserves room for all three buttons — and left of
that a third, the **room tree** in its own popover, on the dialogue and the canvas both (out of the menu since 2026-09-18, so the menu
doesn't open on a wall of folders; the two popovers close each other; a folder's `move` opens the
menu's move sheet). The tree: the
shelf's folders, drawn from the room paths and from nothing else — folders
first then rooms, alphabetical, `▸`/`▾`, closed by default, which folds are open remembered
per browser in `localStorage`, with **collapse all** at the top of the popover shutting every
fold at once; the open room is named once at the top and marked in the accent
on its own row, and the folders on the way to it are unfolded for it once, when it opens.
Everything else hides behind the corner menu: **basic** / **bare** (new room: chat-log header with `bekh:`/`seat:` turns, or nothing at all —
no header, no names, no stop strings, whitespace kept; pressing one brings up a where-field
filled with the open room's folder — blank is a random name at the top of the shelf, `basin/` a
random name in that folder, `basin/s-01` that room — and the same button again or return makes
it, esc drops it), **rename** (rooms get random hex file names; the title is display only, ≤120 chars),
**move to…** (on the open room from the toolrow, on a folder from a `move` beside it: a sheet
listing the folders that exist plus one field for a path that doesn't — a choice fills the
field, confirming posts `/api/move`, and a room that moves under the page's feet is re-opened
from its new path, because the name inside the file is what the next save posts back),
**clear** (same room run again: the old tree is
copied to `.trash`, root and settings stay, no confirm), **delete** (confirm, file moves to
`.trash`), continue from here, **sampler**, **storage** (note names as links, `+`
to add — blank name gets random hex, a taken name is refused — a note opens on its own screen with
edit), **artifacts** (a list; each opens as a tree), **canvases** (the boards, grouped by the
folder they sit in under `shelf/canvases/`, a folder folding out to its boards by title; one
click opens it). The composer is greyed with no room open.

**Artifacts** are the opposite of rooms: a room is a dry run, an artifact is a **walk** frozen —
the document it started from and every fork along the way. On the choose screen every card carries
the same two glyph marks the canvas cards do — `☆`/`★` **keep** (an optional `kept: true` on the
node, saved with the room; eva ignores it and keeps it) and `○`/`●` **good**, which only says it
was kind of nice, he wouldn't keep it, and which no artifact ever sees — **one card, one mark**,
so putting the circle on a starred card takes the star off (and rebuilds that fan's artifact
without it). That is the whole gesture: he keeps as he goes, picks, walks on, keeps more at the
next fork.
**A star is the save** (2026-09-17 — there is no save button). Every toggle of keep, on the choose
screen or the canvas, asks the server to sync *that fan's* artifact (`POST /api/artifact
{"room","parent","sync":true}`; `/api/keep` does it by itself): rebuilt from the kept flags on disk
while any branch in the fan is kept, made on the first star, moved to `shelf/artifacts/.trash/` when
the last one comes off. One artifact per fan, found by `"by": "star"` plus `source.room` and
`source.node` — so a deeper fan of the same walk is its own artifact, repeating the stars above it;
a room renamed since gets a fresh one. Files without `"by": "star"` (berserk's walks, the artifacts
saved by hand before stars) are never rewritten; the plain POST with `kept` still writes once
through `os.link`, 409 on a taken name. The server walks
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
A verbatim twin of a named branch leaves the pool. `blocks` is the spine as nodes (`id`, `kind`,
`text`, `posed`) as far as the steps reach, so the walk can stand up as a room again with its turns.

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
fan. **Continue** makes a new room *out of the walk*: the spine from `blocks`, and at every fork the
line taken plus the kept branches — nothing else of the fan, that being the cut — in fan order, with
the artifact's turn and sampler (editable like any room's), and no stars carried over, so the first
star there starts the new room's own artifact. A walk ending on an open fan lands on that fan's
choose screen. An artifact without `blocks` (everything before 2026-09-17) rebuilds flat: the prompt
as root, each lead as one human line. The artifact itself never changes. An artifact written before walks existed has no `steps` and is read as a walk of one step with
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

**The canvas is a whole experiment at once** — one folder of rooms, or a board, as a picture,
on the third screen that opts out of the reading column. It exists because a census of thirty rooms of
thirty branches cannot be read a fan at a time: what is being looked for is which fans went
somewhere, and that is a *shape*. Ways in: a `canvas` control on every folder row of the room
tree, beside `move`, and the url `#canvas=<folder path>`; a board from the menu's
**canvases**, at `#board=<name>` — `#canvas=` keeps meaning a folder. A back arrow returns to the
dialogue. The picture arrives in one `/api/folder` or `/api/canvas` call and never streams. A
board is named in the bar and the title node by its title, **opens with reveal on** (it is a
comparison laid out on purpose, and what is compared is the voices), and carries `‹ 2/4 ›` in
the bar to step to the previous/next board in its folder (hidden on a folder canvas, or a board
alone in its folder); a step writes the address, so back returns to the board before. A title node, an
arrow to each room's seed card (the seed's tail, `whole seed ▸`, `open room`, and `tree ↗` on
a room berserk walked), and under it the fan as a grid of **uniform cards**, `CARD_H = 185`
world px in one constant. Seed blocks are packed as six masonry columns, each next room into
the shortest one, so a room that collapsed to one brick leaves no hole. **A room whose tree is a
pure chain** — a wire room, where nothing ever forked — is drawn instead as one column exactly a
card wide, its line-cards as tall as their own text and no frame round them, beats among them as
thin accent-pink lines nobody can mark, which is how a transcript reads and how twenty of them pack as
twenty columns. **Any tree, not only a
census**: a branch somebody fanned under gets a `▾ n` mark and its own framed grid below, with
a measured arrow from the card to that frame — accent when that branch is on the path
root→`current`, dim when the room walked elsewhere — and a berserk beat is drawn as a
one-line accent-pink card between the branch taken and the fan under it, so a night reads as a
staircase of fans. **Look-alikes** (same first 40 characters, whitespace collapsed,
casefolded) collapse into one stacked card, `‹ ›` or the arrow keys flipping the members under
the pointer, the common prefix dim and each member's own tail in full ink; the **cold heat
ramp** (`--heat-1…6`, slate → dusky magenta, its legend in the bar, shown only when the canvas has stacks — a wire board has none) says how big a cluster is
and no `×N` is written anywhere. Zoomed out — below `textK()`, which reads the viewport — the
cards drop their ink and become bricks coloured by that ramp.
**Two marks** sit in every card's head as glyphs — `☆`/`★` **keep** in ice, `○`/`●` **good** in
the accent — written through `/api/mark`, optimistically, reverting with a notice if the server
refuses (a revert puts back the mark the write cleared, too); `good` exists because keep was being
spent on everything merely liked while a blind three-model fan was read, and it means "kind of
nice, i wouldn't keep it". **A card wears one of them, never both**: setting either clears the
other, in the page's local state and on disk in the same write, so `★ N · ● M` in the bar and a
stack's counts are two piles and not one overlapping heap. Up close the mark is the card's border
(kept ice, good accent); zoomed out, where there is no glyph left, it is the fill (kept ice, good
accent at 45%) and a marked stack keeps its heat and takes a ring. A stack counts its members' marks in its head and marks the one on top.
The bar reads `★ N · ● M`, and the filter beside it cycles three states: `all` → `● + ★` →
`★ only`. **reveal** appears only when the picture holds two or more models, is off by default
on a folder and on on a board, and is never remembered (a reload keeps where he put it): it puts a model tag and a patterned top edge (solid / dashed / dotted —
pattern, not hue, because the ramp owns every cold colour) on each card, a legend in the bar
and a `★ by model: … · ● by model: …` line. Drag, two fingers on the trackpad or the arrows pan (shift+arrow half a screen; ← → flip a stack instead while the pointer rests on one), a pinch zooms about the pointer — ctrl+wheel in Chromium, gesture events in Safari, so ctrl+wheel is also the mouse's zoom — `f`/`fit`,
a seed heading flies to its block, `esc` closes an opened card or fits; nothing on the surface
is selectable and the cursor stays the ordinary arrow. `open room` goes to `#room=<path>` —
another of the page's addresses — so the browser's own back button comes home to `#canvas=` or
`#board=` with the camera where it was (kept in `sessionStorage` per folder and per board, under
two prefixes so a board named like a folder never takes its camera). **Reading** (2026-09-18) is the same canvas as text, because a chain is a
transcript and a column one card wide reads it through a keyhole: a `read` chip in the bar
wherever the canvas holds a chain, and a canvas of nothing but chains (every wire board) opens
on it; once pressed either way, the choice holds for every board in the tab. One scrolling page
in the reading column — each room's name with `→` into it, the seed only when it differs from
the room above, then the model lines alone (beats are scaffolding and never shown; edge
newlines trimmed), the model's name in a narrow margin under `reveal`, the turns carried by a faint stripe per seat (`--seat-a` slate, `--seat-b` a frail magenta; by seat, never by model, so a blind read learns nothing) — and `☆`/`○` at the right
edge on hover, shown for good once worn, through the same `canMarkBtns` → `/api/mark`,
repainting the picture's card as well. The filter applies; a room that forked is left to the
picture. The arrows scroll the page natively there, and its scroll is remembered per board in `sessionStorage`, across a room and back and across a reload. `reload` re-reads the folder
or the board while a census is still writing and keeps the camera.

All chrome is lowercase by one CSS rule; the document, anything typed and the export screen keep
their capitals, because a capital there is text the model sees. Room: charcoal ground and
blue-white ink, lilac accent, ice for the live dot, accent pink for posed and for beats; system sans; light by the OS,
no toggle; dom-built, never innerHTML. `front/looks/` holds the four rejected look-off pages.

**On a phone** it was put through a real review (commit `2e1b434`): block controls drop into
their own row below each line, touch shows hover-only controls, fields are 16px so iOS doesn't
zoom, return types a newline on touch and the button sends, notices sit at the top. How to check
a phone layout from the mac — the iframe-and-crop headless rig and every trap in it — lives in
**`front/mobile/`**; read its `CLAUDE.md` before touching the page's small-screen CSS.

Added to the iPhone's home screen it **installs as a standalone app** — its own icon, no address
bar, no toolbar sliding in and out as the dialogue scrolls. What makes that work: the
`apple-mobile-web-app-*` tags in the head, `/manifest.webmanifest` (`display: standalone`, scope
`/`) and `/icon-180|192|512.png`, all served by `loom.py` out of `front/icons/` — the mark is one
stem and three fanning strokes, written by `front/icons/make.py` (stdlib, zlib and struct, run once
and the PNGs committed) — plus `viewport-fit=cover` and `env(safe-area-inset-*)` on every fixed
edge, since `black-translucent` draws the page under the clock and the home bar. **iOS reads those
tags once, when the icon is added**, so an icon on the home screen from before this shipped stays a
plain Safari bookmark: delete it and add it again.

## The terminal

**eva** (`cli/eva.py`, `~/.local/bin/eva` symlinks to it) is the loom as a repl over the same
sittings: `eva [name]`, the prompt is the turn prefix, candidates stream in numbered, a digit
picks, empty return fans; `/more /fan N /back /prune /edit /say /seed /doc /set /open /new [bare]
name /quit`. It talks straight to llama-server, streaming, and saves through `write_sitting`.
`/new` on a taken name is a no-op. It doesn't read titles yet, so page-made rooms show as hex
names there, and it takes any argument but `go` as a room name (`eva --help` made a room);
**`eva go N`** is the dream stream's ration, N dreams with pictures then everything off, foreground, ctrl-c to stop
(`stream/go.sh`, `stream/CLAUDE.md`). The page and
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

**wire** (`cli/wire.py`, 2026-09-18): **two base models taking turns on one line, and nobody
picking.** A document opens on a wire — a phone, a switch, a line going faint — and then the two
write it a line at a time: each sees the whole document so far, neither controls it, one sample
per turn, no fan, no picker, no person. bekh's reason for it (the morning's brainstorm,
`BRIEF.md`): a picker can only return what a fan already holds, and everything that ever
moved a fan here was on the generating side, so the dream should be emergent from the loop and
not engineered into the seed. The room is a **bare** room standing on the seed and then a linear
spine, one model node per line, `current` walking to the newest, the file rewritten after every
line — so the page watches the transcript grow and the canvas draws it as a column. **A line
ends at the first newline and wire.py is what ends it**, not llama: a turn is drawn as a budget
of `--n-predict` tokens with **no stop string**, and `line_of` cuts the first line with
something in it out of what came back, throwing the rest away. `stop: ["\n"]` was the first
design and it was wrong — a base model handed a prompt that ends on a newline answers with
another newline, because that is what opening a paragraph looks like, so the stop fired on token
one and **every gpt-2 turn of the first real chain came back empty** (6 of 6 when measured
directly, 2026-09-18; nemo covered for it and wrote all 24 lines alone). The newline that closes
a line is appended here, so every turn starts on a fresh line and the next model reads a clean
seam. Trailing whitespace is stripped (a document ending on a space makes the next token a
numeral); an empty line is retried once at the same seat and then handed to the other model, and
the miss rides on the node as `meta.empty_retries` / `meta.swapped_from`. Every node is stamped
`meta.model` with the model's *name*, `meta.turn` and `meta.params`, so `reveal` on the canvas
tells the two voices apart exactly as it does a census's. The sampler is the room's own — min_p
0.08, xtc off and **the brakes ON**, because two voices answering each other echo — with
`--temp` (default 1.4) or `--temps a=1.4,b=2.6` per seat. `--models` takes exactly two seats in
`role=name=url` form and the roles are not decoration: **a is the caller, the *i* the seed
already stands in; b is the voice on the line**, `--first a|b` says which of them opens (a seed
whose last sentence already hands the turn to the far end wants `b`). Before every turn the
document is counted on that seat's own `/tokenize` against its `/props` window, and a document
that has outgrown it **stops the chain** with `meta.stopped: "context"` on the last line —
never a silently truncated prompt. A taken room name is a no-op, and one line per turn goes to
stdout (`turn 7 · gpt2 · 13 tok · "…"`).

**`--beats FILE`** is the padding, bekh's amendment the same day: bare, neither model knows there
are two of them — each is only continuing a text. A beat is a posed line between the turns, the
same thing berserk poses (`kind: "human"`, `posed`, `"\n\n" + line + "\n"`, plus `meta.beat`),
saying whose turn it is now without ever saying what it is. The file is **two groups separated by
a blank line** — before the voice speaks, then before the caller speaks — each rotated in order
and wrapping, `#` lines skipped; two groups and not one because a line that hands the turn to the
far end of a wire reads nothing like one that hands it back to the man holding the receiver. The
opening line never gets a beat: the seed's own last sentence is the only introduction it is
allowed. Half a run goes without beats, so the padding is a thing that can be read against its
absence.

```bash
uv run --python 3.12 eva/cli/wire.py --name experiments/wire/hum-beats-nemocaller-01 \
  --doc shelf/seeds/short/08-what-is-that-hum.txt --beats shelf/seeds/wire-beats-hum.txt \
  --first a --lines 24 --n-predict 40 --temp 1.4 \
  --models a=nemo=http://127.0.0.1:8080,b=gpt2=http://127.0.0.1:8083
```

**walk** (`cli/walk/`): seed → short fan → pick (`walk.py`), fork a room at a branch and cut it
(`fork.py`), fan wide under a branch (`fan_under.py`), read a naming fan (`names.py`). Its README
holds the procedure and what the first runs taught. All of them bypass the live loom and write the
file directly — don't have the room open in the page while one runs.

## The stream

**stream** (`stream/stream.py`, 2026-09-19): **one short passage every five minutes, and nobody
picking.** A seed by lot, a heat by lot in 1.8–2.5, one `/completion` of 170 tokens, a bare room
at `stream/<YYYY-MM-DD>/<HHMM>` holding the seed and the passage, and that is the run — `--once`
writes one and exits, because the loop is launchd's `StartInterval` and not a sleep. Two
dreamers since 2026-09-23 — nemo and gpt-2, strictly alternating, the turn read off the newest
page and every page stamped `meta.model` with who wrote it (`STREAM_MODELS`). A
failed run is a ledger line and exit 0, never a crash loop. The seed is drawn from two pots —
everything under `shelf/seeds/`, and the tails of passages bekh **starred** — with a starred
tail weighing what one seed weighs, capped at half the draws; that is the only place his hand is
in the loop and it acts at the next passage's input. Branches carry
`meta.logprobs`, a flat list of the chosen token's logprob per token and **not** llama's `probs`
tables — 288 rooms a day of those would be a gigabyte a week. A regexp set flags web furniture
as `meta.flag` without deleting anything; the reader hides those and `?all=1` shows them. Ledger
and heartbeat in `shelf/stream/`, watched by `stream/monitor.py`, and **none of it is in git**:
the rooms are disposable, and what survives is the artifact a star writes. The reader is
`front/stream.html` at `/stream` — **one continuous scroll**, newest at the top, older
lazy-loaded as he reads down, each passage carrying its own two strokes through the existing
`/api/mark`; a passage's ragged end is trimmed to the last sentence in the DISPLAY only
(`?raw=1` shows it as written). The look is a placeholder.

Beside it, **the interpreter** (`stream/interpreter.py`, 2026-09-19): a cli seat that is opus
in code and **codex in production** (`STREAM_READER`, 2026-09-21 — two different families, one
on each side of the page; `stream/codex.py` is its door and opus covers any note it misses), on
the same clock, writing a short **note** on every passage and marking **two things** inside
it — magenta for what touched it, cyan for what felt most mysterious — the persona is `stream/interpreter.txt`, bekh's file, and the code only
appends the plumbing. Its copy of a dream is stored verbatim and never corrected, and nothing is compared
against the raw text — the words it marked are simply written in colour, magenta or cyan by
lot. `/api/stream` carries the copy, the segments and the note; the page draws the note beside
its dream. It has no clock: the worker kickstarts it when a page lands.
And a third voice, **the sleeper remembering** (`stream/remembering.py`, 2026-09-19): opus
rewriting one index-card account of the dream so far every time a passage lands, told that the
passages are **scenes of one dream** so it has to find connective tissue; every rewrite kept,
a dream ending after 4 scenes and nothing else — a stopped stream leaves it waiting. The page carries it at the top with
its `3 / 4`, and a finished one where it ended. Both opus voices call through `stream/opus.py`,
which counts what they cost onto every ledger row.
And a fourth, **the analyst** (`stream/analyst.py`, 2026-09-23): a portrait of the dreamer and
one remark he would say out loud — the line a card in the feed carries, the portrait the
manuscript behind it. Four doors (opus, fable, deepseek over openrouter, GPT through codex)
and two shapes: one resumed session reading every dream, or a fresh read of the last N. What
runs is **deepseek reading the last thirty every eight dreams**, the student; a mentor on a
GPT thread is decided and not wired (`stream/CLAUDE.md`, the analyst section). Tapped by the
writer like the others; `/api/stream` hangs each portrait on the dream it followed, and eva's
page shows it there as a quiet band that unfolds on a click.
And **plates** (`stream/plate.py`, 2026-09-20): a painting per dream drawn by hand through
codex, served as a file and set as the background of the dream's own block — behind the words,
under a measured wash, lifting on a hover or a press-and-hold.
**Nothing in the stream waits for a timer** (2026-09-22): every writer taps the mirror push as
it lands (`stream/push.py`), and `/api/stream/events` pushes the change on to whoever is
reading — the 60s polls at both ends are gone.
**`stream/CLAUDE.md`** is the doc and the runbook.

## Tests

`tests/` — `loomtest.py` (every server route, notes and artifacts included, plus `Canvas` and
`Boards` for the saved canvases — list, open in the file's order, a gone room skipped, 404, 400,
dot segments refused, the `LOOM_CANVASES` scratch shelf, a mark landing in the room — `Keep` and
`Mark` for the two branch marks, and `Folders`:
the recursive listing with the bin hidden, every rule a path has, the move of a room and of a
folder with its collisions and its pruning, and a walked room answering to its bare name after
it moves — and `StreamEvents` for the held connection: a room and its reading landing as one
`change` with the status on it, a writer falling asleep as a change with no rooms and a
keepalive after it, and a client that walks away leaving the loom serving), `evatest.py`,
`censustest.py`, `wiretest.py` (the chain: the alternation, the whole document on the wire every
turn, the newline seam, the empty-line retry and swap, the beats and the `--first` rule, the
window stopping the chain), `berserktest.py`, all against `tests/stub_llama.py`, a fake
llama-server — whose `serve()` takes `n_ctx`, `model_path` and `lines` (its own script of
answers, in order, an empty string meaning it answered nothing) per server; scratch
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

While the mac is off, `eva.x` falls over to a copy on the mini that takes reading and marks only —
`mirror/CLAUDE.md`.

Three launchd agents on the mac — `com.bekh.eva-llama` (llama-server, nemo, loopback 8080),
`com.bekh.eva-loom` (the loom, bound to the mac's tailnet ip 100.91.166.121:8082, the only door)
and `com.bekh.eva-berserk` (one cycle per kickstart, never at load; see `berserk/CLAUDE.md`) —
plus `com.bekh.eva-gpt2` (llama-server, GPT-2 XL, loopback 8083, on the cpu — the stream's
second dreamer), `com.bekh.eva-stream` (one passage every 300s, loaded 2026-09-19) and the
voices it kickstarts, `com.bekh.eva-stream-interpreter`, `com.bekh.eva-stream-remembering`,
`com.bekh.eva-stream-plating` and `com.bekh.eva-stream-analyst` (deepseek, a fresh read of the
last thirty every eight dreams, loaded 2026-09-23), none of which has an interval of its own (those plists, gpt-2's included,
live in `stream/`; log `/tmp/eva-stream-analyst.log` for the analyst) — and
one caddy block on the mini (`~/tower/forge/mini/minidns`) proxying the name to that address, same
shape as `m.x` and `kokoro.x`. Logs `/tmp/eva-loom.log`, `/tmp/eva-llama.log`,
`/tmp/eva-gpt2.log`, `/tmp/eva-berserk.log`. Nothing answers on loopback 8082; use the name. **`loom.html` changes need
only a reload; `loom.py` changes need the kickstart**, or the live server keeps running the old
routes. **A plist edit needs bootout + bootstrap** — kickstart restarts the process from
launchd's cached copy of the plist, which is how the loom died on a stale path once.

```bash
launchctl kickstart -k gui/$(id -u)/com.bekh.eva-loom          # restart the loom after editing loom.py
launchctl bootout gui/$(id -u)/com.bekh.eva-loom; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-loom.plist   # after editing the plist
launchctl bootout gui/$(id -u)/com.bekh.eva-llama              # give the mac its ~10 GB back
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-llama.plist   # and take it again
launchctl kickstart gui/$(id -u)/com.bekh.eva-gpt2             # gpt-2 up (loaded once, stays loaded)
launchctl kill SIGTERM gui/$(id -u)/com.bekh.eva-gpt2          # gpt-2 off, gracefully
```

The page saying *the mac is off* = caddy fell over to the mirror (the mac asleep or the loom
agent down); a 502 at the name = the mirror is down too; a red dot in the menu = llama is down. A page with no room open greys the composer — that is not the model being down.

The mac's llama-server is brew's; models in `~/.cache/llama.cpp/`. The model is nemo base at
**q5_k_m, not q6**: the q6 file is 10 GB and macOS wires at most ~2/3 of a 16 GB box for the GPU,
so q6 plus an 8k cache spills. Pulled with resumable curl, not llama-server's own `-hf` puller,
which timed out on one connection and wrote nothing. Nemo answers as a base model (`i'm here`,
`yep`), stops clean on `\nbekh:`, ~10–12 tok/s. llama-server 0.4.0 **rejects
`dry_penalty_last_n: -1`** (validates 0..INT_MAX) — the sheet's sampler line is wrong on that one
field; the page defaults it to the context size, 8192.

**A second base model beside nemo** (2026-09-17), for blind comparisons with `census.py --models`
and, since 2026-09-23, **the stream's second dreamer**, writing every other page
(`stream/CLAUDE.md`): GPT-2 XL, `~/.cache/llama.cpp/gpt2-xl.Q8_0.gguf` (mradermacher/gpt2-xl-GGUF,
1.75 GB, 1024 window, ~21 tok/s on the cpu with nemo busy on the gpu). **A launchd agent now**,
`com.bekh.eva-gpt2` (`stream/com.bekh.eva-gpt2.plist`, tracked, copied to
`~/Library/LaunchAgents/` and bootstrapped once): `127.0.0.1:8083`, `-c 1024 -ngl 0
--no-webui`, log `/tmp/eva-gpt2.log`, crash restarted and a clean exit left exited, the shape
of nemo's — so it is started with `launchctl kickstart gui/$(id -u)/com.bekh.eva-gpt2` and
stopped with `launchctl kill SIGTERM gui/$(id -u)/com.bekh.eva-gpt2`, and `eva go` does both.
Pythia 2.8b
(`EleutherAI_pythia-2.8b.Q8_0.gguf`, port 8081, `-c 2048`) is on disk too and was dropped after
the first run: fewest marks, under 5 tok/s, ends the document early three times in ten. Port
8082 is the loom's; don't use it.

```bash
launchctl kickstart gui/$(id -u)/com.bekh.eva-gpt2
until curl -sf http://127.0.0.1:8083/health >/dev/null; do sleep 2; done
cd ~/tower/forge/eva-goes-berserk && uv run --python 3.12 eva/cli/census.py \
  --name experiments/<folder>/<room> --doc shelf/seeds/short/<seed>.txt --tail 260 \
  --bare --n 30 --temps 1.4,2.2 --n-predict 60 --set xtc_probability=0 --set min_p=0.08 \
  --models nemo=http://127.0.0.1:8080,gpt2=http://127.0.0.1:8083
launchctl kill SIGTERM gui/$(id -u)/com.bekh.eva-gpt2     # unless the stream is dreaming on it
```
