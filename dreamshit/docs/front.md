# front — the project (`front/`)

The dream-stream front, reading eva live. Plain html/css/js, no build step: whatever sits in `front/` is the site.

## Where it runs

- **Live: `https://dreamshit.x`** (also `d.x`) on the mini. Caddy serves `/srv/dreamshit` and sends `/api/*` and `/stream/plate/*` to eva's own upstream — the `eva_upstream` snippet in `~/tower/forge/mini/minidns/etc/caddy/Caddyfile`, shared with eva.x so the two can't drift. Same origin, so no CORS, and the looks can read plate pixels.
- **Public: `https://dreamshit.net`** (and `www.`), the same `/srv/dreamshit` through a Cloudflare named tunnel into a caged loopback caddy on the mini, which passes only `/api/stream*` (the feed and the events) and `/stream/plate/*` on to eva's read-only mirror (`127.0.0.1:8083`) — so the public site reads what the mirror holds, never the mac directly, and cannot mark. The pipe is its own repo: `~/tower/forge/mini/dreamshit-site-tunnel/` (`README.md`, `deploy.sh`, `check.sh up`, `rollback.sh`). One deploy of the page feeds both names.
- **Deploy:** `front/deploy.sh` (rsyncs the page files, prints the status code). New page file → add it to the rsync list. A deploy reaches a visitor on the next plain reload: the zone's Browser Cache TTL is set to "respect existing headers" (bekh flipped it in the Cloudflare dashboard, 2026-09-22 — before that the edge rewrote the page files' `no-cache` into a 4-hour browser cache and every deploy needed a hard reload).
- **Caddy rollback** (backup made when dreamshit.x was added):
  `ssh bek@miniarch 'sudo cp /etc/caddy/Caddyfile.bak-pre-dreamshit /etc/caddy/Caddyfile && sudo systemctl reload caddy'`
- **Local:** `uv run --python 3.12 front/serve.py` (from `dreamshit/`; stdlib only) → `http://127.0.0.1:8766/`. Serves the folder and forwards the same two paths to eva.x server-side, verifying eva against `front/eva-root.crt` (the mini's public Caddy root).

## Files

- `index.html` — shell: status bar (state · age, font button, ink button, glass·dots switch), the ink panel under it, the ribbon tuner, feed, lightbox, manuscript.
- `style.css` — layout, voices, plates, wash, looks' css.
- `dev.js` — the dev hub (`?dev`): every dial of the page in one panel by tab, drawn from one list (`TABS`), driving app.js's own setters; loaded after app.js, in its own function scope because a classic script's top-level names are shared.
- `app.js` — live stream, packs, focus, looks painting, font/wash knobs, lightbox.
- `looks.js` — the picture-look presets (see `looks.md`).
- `analyst.jpg` — the analyst's face (a copy of `eva/stream/analyst.jpg`; re-copy if it is ever repainted), for the ribbon and the manuscript.
- `fonts.js` — the passage-font presets and the `SHORTLIST` (see `reading.md`), and `INKS`, the passage-ink presets.

## How it behaves

- Loads the newest 48 passages, lands on the newest at the reading line, and **reaches back on scroll** (bekh, 2026-09-24): an IntersectionObserver on a sentinel above the feed's top margin (`#older`, seen two screens early) asks the api for the 48 before the oldest room held (`/api/stream?n=48&before=<room>` — loom.py's own paging) and prepends them, holding the camera: the first row is measured before and after and the scroll moves by the difference (0 if the browser's scroll anchoring already held it). A story cut by the window's edge joins the pack on top, so it stays one pack with one header and one thread; every pack touched is redrawn and re-measured like any other. Again at the top, again 48, until the api answers `more: false` — then it stops asking, with no message. Off until the page has landed on the newest, and never in `?tail` / `?only`. (`loadOlder` / `renderOlder` in `app.js`.) Then it **listens**: an `EventSource` on `/api/stream/events` (eva holds it open) names the rooms that changed within a couple of seconds of a passage, a note, a story, a plate or a name landing. Anything inside the window it holds — the pages are one contiguous newest-first run — is one refetch of that window; anything older is ignored. Because older pages keep that run contiguous, the refetch covers everything reached back to — its cost grows with every trip up, and the api caps `n` at 400, so pages further back than that stop getting late plates and readings (a refetch sized to the oldest room an event names would fix both; not built). On a reconnect it refetches once, so nothing missed stays missed. The 60s poll is gone; a 5-minute poll survives only as insurance while the events have *never* connected, and is cleared the moment they do. New passages append at the bottom: followed if you're on the newest, otherwise counted on a "new" button. Late plates and readings attach in place; the trickle is re-cut and redrawn whole as its story grows. (`?tail` / `?only`, the screenshot modes, don't listen at all.)
- **Plates load near the screen only** (bekh, 2026-09-23): a row's painting (~500 KB, 1400×933) is fetched when the row comes within two screens of view (`plateSight`, an IntersectionObserver in `app.js`) and kept once fetched. Before, all 48 were requested on open and the newest — where the page lands — queued behind the rest; at `?tail=48` from the top it is now 5 of 48. Next if scrolling still stutters: a small copy (~480px) for the unfocused plates, since glass and dots hide the difference and the full size only matters focused and under `pic` — that one needs eva (or the mirror) to cut the copies and the api to name them.
- **Packs:** one per dream. Rows are 3-column grids (`slot | text | reading`), and the left cell
  is where the telling of that dream runs. **What the page does is `trickle=stretch`,
  `align=even`** — bekh's verdict, 2026-09-22: *"unfortunately actually the best
  stylistically"*. The seams are joined up, the whole telling stands as *one* thread in the first
  passage's slot, and it is stretched to **reach the bottom of the dream's last passage**. The
  header is the first passage's slot's own first child, above the thread at the cell's full
  width, stacked: the number on its own line (`13 ·`), the name under it on ONE line — an
  inline-block that refuses to wrap while `fitTitle` steps its size down from 14px to a floor of
  10 (`--tfs`) until it fits the cell; only past the floor does `.wrap` let it break (bekh,
  2026-09-24: "i really want the title to fit in one line"; inside the thread's box it was cut to
  a word a line with the drip). Re-fitted on `refit()`, so a resize or a font change re-measures. The stretched
  thread has no `top`, so it sits at its static position right under the header, and the drip is
  paced from the words' own top: the header's height is never counted as room for them. **Three dials, each
  moving only when the one before it ran out: narrow the column, then one word to a line, then
  open the leading.** So a 45-word telling beside four scenes becomes a column of single words
  paced down the whole dream, while the same telling beside one scene is just the full-width
  block it always was. The floor of dial 1 is the telling's widest word (`min-content`), never
  under 4 characters, so the thread can't spill sideways into the passage; dial 2 is a
  `word-spacing` wider than any column, which turns every space into a break; dial 3 searches the
  leading (on the words alone) and goes below 1.7 as well as up to
  14 — breaking every space can overshoot a room that normal wrapping fell short of, and the
  one-word-a-line is not given back to save a line. A telling too long for even the full width
  keeps the full width and runs past the bottom; nothing is clipped. It is all measured, never
  guessed: an offscreen twin of the column, wearing whichever dials the real thread will wear, is
  handed a width or a leading and asked how tall it comes out, ~10 of those per binary search per
  dream. Re-measured whenever a row can have moved: a resize, a scene landing, a reading landing
  late, `,` `.` `t` `T`, the webfont arriving. The thread is lifted out of the row's flow
  (`position: absolute`) on purpose: in the flow it would grow the row it hangs from, which would
  grow the pack it is being measured against. A scene landing rewrites the whole telling, so
  **every pack of it is redrawn and re-measured**, on the event refetch and on the slow poll
  alike. `?tail` / `?only` follow the same rule. The shots are `shots/stretch/`.
- **Everything it was tried against is still here**, nothing deleted, behind the url and the `g`
  key — the page remembers only a choice actually made, never the default it opened with:
  - **`?trickle=parts`** (key `g` toggles it): the seams are kept and nothing is measured — the
    sleeper marks them with `|`, `story.parts` is the telling split there, and part n goes into
    passage n's own `slot` cell, top-aligned, 60% of the column, centred; the header above part
    1, at the cell's full width; the grid places it all. Mismatches are not errors: fewer parts than passages leaves the
    later rows bare, a surplus is appended to the last passage's part, and one part (no marks at
    all — every dream on the shelf from before the seams) sits whole beside the first passage.
  - **`?align=dreams`** — stretch with the drip lined up to the scenes: the seams are kept
    instead of joined, part n hangs in passage n's own slot as in parts, one width for the whole
    pack (the widest word in the *whole* telling, or the parts would step in and out down the
    dream) and dial 1 skipped — each part goes straight to one word a line and gets its own
    leading, so it lands on the bottom of its own scene; a part with more words than the tightest
    leading holds runs on into the next. A telling with no seam has nothing to line up and is
    `even` whatever is asked.
  - **`?align=band`** — `dreams` with the pace reined in: the even leading for the whole telling
    is worked out first, and every part's own leading is clamped to within `?band=` of it (0.4 by
    default; 0 pins every part to the even pace). A part that can't reach its scene's bottom
    inside the band stops early with air under it; one that can't fit runs past into the next
    scene, and nothing clips it — the later row's own words are simply drawn over it, since they
    come later in the page.
- **Focus follows reading:** the passage under the middle of the screen is focused — its plate sharp and washed dark behind the words; every other plate shows the current look. Works on phones (no hover).
- **Names** (eva's convention): `verse · name` at the top of each passage (`10:4 · the body man`), `chapter · title` heading each trickle, a size up — all in the label face.
- **Seed** (the found text a dream grew from): not shown inline — bekh: without it the page is right. A small `seed` button above each passage opens it in a floating box over the passage; click again / elsewhere / esc closes.
- **ink**: an `ink` word in the bar with a chip of the current colour in front of it → a panel drops under the bar: the presets (`INKS` in `fonts.js`), the native `<input type=color>` (on a mac, the system colour panel — wheel, sliders, eyedropper) and `reset`. Hovering a swatch names it in the corner label, clicking applies it, dragging in the picker recolours live. The button opens and closes it (esc and `c` too) — **a click anywhere else does not**, or reaching for the picker would shut it. **Only the passage takes the colour** (`--ink-text` on body): labels, names, trickle, reading and seed keep the house palette, and the reader's two marks blend out of the passage's ink instead of the house one, so a marked run keeps its 30% step from the words around it whatever they are wearing.
- **pic**: a quiet word next to `seed` (it appears once the plate has landed) → the plate full screen, uncropped. Click / esc closes. (Double-click on a dream used to do the same; let go 2026-09-22.) The cursor is a plain arrow everywhere — no hand on buttons, no zoom glass — bekh's call the same day.
- **The ribbon's fill** (bekh, 2026-09-24, out of `sketch/band/`): the band's black gives way to the two neighbouring paintings bled into it — `drawRibbon` in `app.js` paints the band's canvas from the last row of the pack above and the first row of the next pack below (the plate's `cover` run backwards to find each edge in its painting), the lower one fading in from mid-band; the newest band has nothing below yet, so its fill fades out into black until the next dream is painted. Redrawn in one frame when a neighbouring plate lands, when the band resizes, and on every tuner move. Under the words a black `b.wash` keeps them readable; the ribbon's own gradient and gloss still sit over it. Dials in the tuner row below.
- **The analyst's ribbon** (bekh, 2026-09-23): every sixteen dreams eva's analyst writes a fresh portrait of the dreamer, and the page it was written right after carries `portrait` (`docs/stream.md`). The page draws a black ribbon for it — the full width of the page, `--rh` tall (71px) with `--rgap` (0px) of air between it and the painted rows above and below (a row's plate fills the row, so the ribbon's margin *is* that gap; 0 = flush), glassy but still: a hairline of light on the top edge (pink into cyan), a sheen over the top half, a shadow under — all softened to about two thirds the same afternoon (bekh: "a little less 3D, a little less protruding"). **Height means height**: the band never grows. The line starts at its size and steps down a pixel at a time to 11 until it fits (measured by `scrollHeight`, in `fitRibbon`, on landing, on the band's resize and on `refit()`); past the floor it is top-aligned and clipped on its last whole line (`.clip`: the box cut to n whole lines, `--rclip`, with its vertical padding dropped — overflow clips at the padding edge, so the bottom padding was a window the next line showed through half-cut — and a line clamp for the ellipsis), never spilling onto the next row. The padding shrinks with a low band (12% of `--rh`, at most 16px). At the default 95 a ~280-character line now comes out around 14px where it used to grow the band to ~110. The left third is his face (`analyst.jpg`, the front's own copy of `eva/stream/analyst.jpg` — not served through the api), `cover` at `50% 33%` so the strip runs across the eyes and the mustache, its right edge masked away into the black; the other two thirds are `portrait.line` — the portrait's own last two sentences, cut by eva (since 2026-09-23 late the analyst is asked for the portrait only, no remark) — no quote marks and no dash (a hanging dialogue dash was tried and taken out the same night, 2026-09-23), in the passage's face at 18px (15 on a phone), vertically centred. No line (the versions written before any line existed) → the portrait's first sentence, italic and dimmer. The face's crop follows the height by itself (`cover` shows a thinner strip at the same 33%). **It goes after the dream's pack, not after the passage**: the stretched telling hangs from a pack's first row down to its last, and a ribbon between two rows would sit on the drip and cover words of it — so a portrait written after scene 2 shows where that story ends. It attaches late like a plate: the event names the room, the refetch brings `portrait`, `sync()` hangs the ribbon on a pack already drawn. The only hover answer is the top edge catching a little more light. Phone: the same card, narrower.
- **The manuscript**: a press on a ribbon (or return on it) opens that version whole on its own layer over the feed — the lightbox's kind, opaque, closed by esc, a click outside the sheet, or `×`. The face small at the sheet's corner, `the analyst · after N dreams` and the date, the line in italic grey, then the portrait in the passage's font at 640px, and `‹ k / n ›` (and ← →) stepping to earlier / later versions from `/api/stream/portraits`, fetched on open (until it lands, or if it fails, the one version with nowhere to step). While it is open it owns the keyboard: the page's own keys (1–7, f, t, , .) don't reach the feed behind it. `?portrait=<id>` opens a version on load — a link to one portrait, and how a headless shot gets the sheet open. Shots: `shots/analyst/`.
- Phones (<820px): one column — each part of the trickle above its own passage, the header above part 1; a passage with no part of its own hides that cell, or the row gap would leave a hole. **The law is that the page is a desktop page**, and stretch is not sensible in one column (a thread there is just a narrow block over the passage it belongs to), so a phone draws `parts` whatever the desktop is set to — the default included. Crossing the breakpoint on a resize redraws.

## Knobs (all remembered per browser in localStorage; url params win)

The trickle's mode and the ink remember **only a choice actually made** — a url
param, the `g` key, a swatch, the picker. The look, font and wash write themselves on every load, which is fine while their
defaults never change; a trickle default written that way froze each browser on whatever the page
opened with the day it first saw it, which is why those two don't.

**An experiment is never remembered — url only, gone on the next plain load.** The precedent
(2026-09-23): `?align=dreams`, opened once in Helium for the three-drip comparison, was stored
like a dial, and for a day that one browser ran the dreams drip while every other ran the even
one. It showed as the thread stopping a scene short of its dream — three parts paced to three
scenes, the fourth bare — in Helium alone, and a whole session went to fonts, observers, zoom and
caches before the storage was read. A knob with no key and no ui has no business in localStorage.

| what | ui / keys | url |
|---|---|---|
| look | glass·dots switch; keys 1–7 | `?look=` |
| glass blur | `[` `]` | `?gb=` |
| font | font button / `f` `F` walk the shortlist | `?font=` (any) |
| passage ink | ink button / `c` opens the panel: presets, the system picker, `reset` | `?ink=f5c8fe` (no `#`; a preset's name works too) · `?ink=` resets |
| passage size | `,` smaller · `.` bigger (per font) | — |
| passage weight | `t` thinner · `T` thicker, steps of 50 (per font; moves only on a variable face — newsreader loads 200–800) | `?fw=300` |
| wash darkness | `w` lighter · `W` darker (also `-` `=`) | `?wa=0.72` |
| side voices size | `;` smaller · `'` bigger, half a pixel a step, 10–20 — **one dial for both**: the trickle at the number, the reading a pixel above it (bekh, 2026-09-22: moving one alone throws the pair off balance). Headers and timestamps keep their own | `?tsize=14` |
| trickle mode | `g` toggles stretch ↔ parts | `?trickle=stretch` (default) `\|parts` |
| stretch's drip | — (a dev option, no key, not remembered) | `?align=even` (default) `\|dreams\|band` |
| the band's width | — (not remembered) | `?band=0.4` (align=band only) |
| the ribbon | `?tune=ribbon` (and nothing else) opens the ribbon tuner, bottom right in the ink panel's clothes, every dial live with its number beside it and the whole set printed plainly underneath: `height` 40–200px (`--rh`, 86), `gap` 0–48px (`--rgap`, 0), `face` 0–100% (`--rpos`, 29 — where the crop sits down his portrait), `gloss` 0–200 (`--rg`, 25 — one factor over every light and shadow on the band), `wash` 0–100 (`--rwash`, 59 — his face darkened toward black), and the fill (2026-09-24): `fill` 1 streak · 2 mirror · 3 overlap (`--rfill`, 2), `edge` 1–80 rows for streak (`--redge`, 1), `reach` 1–12 band heights for mirror/overlap (`--rreach`, 1), `blur` 0–40px (`--rblur`, 0), `b.wash` 0–95 (`--rbw`, 50 — black over the fill so the words read). `reset` forgets them all and gives back `style.css`'s `:root`. Remembered per browser (`ribbon-*`) and applied without the param too — so after tuning, a browser keeps its own numbers until `reset`. When bekh reads his numbers out they go into `:root` | `?rh=60&rgap=0&rpos=40&rg=60&rwash=0&rfill=1&redge=3&rreach=2&rblur=4&rbw=40` — the same as dragging there, remembered; `?rh=` empty resets that one |
| a portrait's manuscript | press a ribbon; ← → step, esc closes | `?portrait=2026-09-23/1943` (not remembered) |
| a link to one dream | — | `#24:3` (a dream by its number), `#24` (a story's first scene), `#2026-09-27/1126` (a room; `stream/` optional). The page pulls earlier pages until that dream is held and stands it mid-screen, instantly; a hash changed in place jumps the same way. Not remembered |
| screenshots | — | `?tail=N` (newest N, no scrolling) · `?only=<room>` (one passage, waits for its font) |
