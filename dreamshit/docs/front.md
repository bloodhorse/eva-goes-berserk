# front — the project (`front/`)

The dream-stream front, reading eva live. Plain html/css/js, no build step: whatever sits in `front/` is the site.

## Where it runs

- **Live: `https://dreamshit.x`** (also `d.x`) on the mini. Caddy serves `/srv/dreamshit` and sends `/api/*` and `/stream/plate/*` to eva's own upstream — the `eva_upstream` snippet in `~/tower/forge/mini/minidns/etc/caddy/Caddyfile`, shared with eva.x so the two can't drift. Same origin, so no CORS, and the looks can read plate pixels.
- **Public: `https://dreamshit.net`** (and `www.`), the same `/srv/dreamshit` through a Cloudflare named tunnel into a caged loopback caddy on the mini, which passes only `/api/stream*` (the feed and the events) and `/stream/plate/*` on to eva's read-only mirror (`127.0.0.1:8083`) — so the public site reads what the mirror holds, never the mac directly, and cannot mark. The pipe is its own repo: `~/tower/forge/mini/dreamshit-site-tunnel/` (`README.md`, `deploy.sh`, `check.sh up`, `rollback.sh`). One deploy of the page feeds both names.
- **Deploy:** `front/deploy.sh` (rsyncs the page files, prints the status code). New page file → add it to the rsync list. Cloudflare's edge still rewrites the page files' `no-cache` into a 4-hour browser cache until the zone's Browser Cache TTL is set to "respect existing headers" in the dashboard (bekh's, needs a browser).
- **Caddy rollback** (backup made when dreamshit.x was added):
  `ssh bek@miniarch 'sudo cp /etc/caddy/Caddyfile.bak-pre-dreamshit /etc/caddy/Caddyfile && sudo systemctl reload caddy'`
- **Local:** `uv run --python 3.12 front/serve.py` (from `dreamshit/`; stdlib only) → `http://127.0.0.1:8766/`. Serves the folder and forwards the same two paths to eva.x server-side, verifying eva against `front/eva-root.crt` (the mini's public Caddy root).

## Files

- `index.html` — shell: status bar (state · age, font button, glass·dots switch), feed, lightbox.
- `style.css` — layout, voices, plates, wash, looks' css.
- `app.js` — live stream, packs, focus, looks painting, font/wash knobs, lightbox.
- `looks.js` — the picture-look presets (see `looks.md`).
- `fonts.js` — the passage-font presets and the `SHORTLIST` (see `reading.md`).

## How it behaves

- Loads the newest 48 passages, lands on the newest at the reading line, then **listens**: an `EventSource` on `/api/stream/events` (eva holds it open) names the rooms that changed within a couple of seconds of a passage, a note, a story, a plate or a name landing. Anything inside the window it holds — the pages are one contiguous newest-first run — is one refetch of that window; anything older is ignored. On a reconnect it refetches once, so nothing missed stays missed. The 60s poll is gone; a 5-minute poll survives only as insurance while the events have *never* connected, and is cleared the moment they do. New passages append at the bottom: followed if you're on the newest, otherwise counted on a "new" button. Late plates and readings attach in place; the trickle is re-cut and redrawn whole as its story grows. (`?tail` / `?only`, the screenshot modes, don't listen at all.)
- **Packs:** one per dream. Rows are 3-column grids (`slot | text | reading`), and **the trickle is cut into parts, one beside each passage** (bekh, 2026-09-22): the sleeper marks his seams with `|`, `story.parts` is the telling split there, and part n goes into passage n's own `slot` cell, top-aligned with it, 60% of the column, centred. The dream's header (`chapter · title`) sits once, above part 1. There is no rail and nothing is measured — the grid places it. Mismatches are not errors: fewer parts than passages leaves the later rows bare, a surplus is appended to the last passage's part, and one part (no marks at all — every dream on the shelf from before this) sits whole beside the first passage, which is what the page did before. A scene landing rewrites the whole telling, so **every part of that pack is redrawn**, on the event refetch and on the slow poll alike. `?tail` / `?only` follow the same rule.
- **The trickle has two modes**, `?trickle=` / key `g`. **`parts`** is the default, above.
  **`stretch`** is bekh's fallback idea (2026-09-22): the seams are ignored, the whole telling
  stands as *one* thread in the first passage's slot, and its column is made **as narrow as it
  needs to be to reach the bottom of the dream's last passage** — the column's full 60% beside a
  single scene, a thread of two or three words a line beside four. The header (`chapter · title`)
  stays above it at the normal width. The width is measured, not guessed: an offscreen twin of
  the column is handed a width and asked how tall it comes out, ~10 of those in a binary search
  per dream, between a floor of one word per line (the telling's widest word, never under 4
  characters, so the thread can't spill into the passage) and the column's full width. A telling
  too short to reach the bottom even at the floor stays at the floor; one too long for the full
  width keeps the full width and runs past the bottom — nothing is clipped. Re-measured whenever
  a row can have moved: a resize, a scene landing, a reading landing late, `,` `.` `t` `T`, the
  webfont arriving. The thread is lifted out of the row's flow (`position: absolute`) on purpose:
  in the flow it would grow the row it hangs from, which would grow the pack it is being measured
  against. Verdict pending; the shots are `shots/stretch/`.
- **Focus follows reading:** the passage under the middle of the screen is focused — its plate sharp and washed dark behind the words; every other plate shows the current look. Works on phones (no hover).
- **Names** (eva's convention): `verse · name` at the top of each passage (`10:4 · the body man`), `chapter · title` heading each trickle, a size up — all in the label face.
- **Seed** (the found text a dream grew from): not shown inline — bekh: without it the page is right. A small `seed` button above each passage opens it in a floating box over the passage; click again / elsewhere / esc closes.
- **pic**: a quiet word next to `seed` (it appears once the plate has landed) → the plate full screen, uncropped. Click / esc closes. (Double-click on a dream used to do the same; let go 2026-09-22.) The cursor is a plain arrow everywhere — no hand on buttons, no zoom glass — bekh's call the same day.
- Phones (<820px): one column — each part of the trickle above its own passage, the header above part 1; a passage with no part of its own hides that cell, or the row gap would leave a hole. **stretch is not sensible in one column** (a thread there is just a narrow block over the passage it belongs to), so a phone draws `parts` whichever mode is on; crossing the breakpoint on a resize redraws.

## Knobs (all remembered per browser in localStorage; url params win)

| what | ui / keys | url |
|---|---|---|
| look | glass·dots switch; keys 1–7 | `?look=` |
| glass blur | `[` `]` | `?gb=` |
| font | font button / `f` `F` walk the shortlist | `?font=` (any) |
| passage size | `,` smaller · `.` bigger (per font) | — |
| passage weight | `t` thinner · `T` thicker, steps of 50 (per font; moves only on a variable face — newsreader loads 200–800) | `?fw=300` |
| wash darkness | `w` lighter · `W` darker (also `-` `=`) | `?wa=0.72` |
| trickle mode | `g` toggles parts ↔ stretch | `?trickle=parts\|stretch` |
| screenshots | — | `?tail=N` (newest N, no scrolling) · `?only=<room>` (one passage, waits for its font) |
