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

- Loads the newest 48 passages, lands on the newest at the reading line, then **listens**: an `EventSource` on `/api/stream/events` (eva holds it open) names the rooms that changed within a couple of seconds of a passage, a note, a story, a plate or a name landing. Anything inside the window it holds — the pages are one contiguous newest-first run — is one refetch of that window; anything older is ignored. On a reconnect it refetches once, so nothing missed stays missed. The 60s poll is gone; a 5-minute poll survives only as insurance while the events have *never* connected, and is cleared the moment they do. New passages append at the bottom: followed if you're on the newest, otherwise counted on a "new" button. Late plates and readings attach in place; the trickle updates as its story grows. (`?tail` / `?only`, the screenshot modes, don't listen at all.)
- **Packs:** one per dream. Rows are 3-column grids (`slot | text | reading`); the pack's **rail** lies over the slot column (measured in js) and holds the dream's **trickle**, 60% of the column, centred, **pinned at the dream's start**. It used to be sticky and ride along through its dream; bekh called that a mistake once trickles ran long — four passages is short enough to scroll back.
- **Focus follows reading:** the passage under the middle of the screen is focused — its plate sharp and washed dark behind the words; every other plate shows the current look. Works on phones (no hover).
- **Names** (eva's convention): `verse · name` at the top of each passage (`10:4 · the body man`), `chapter · title` heading each trickle, a size up — all in the label face.
- **Seed** (the found text a dream grew from): not shown inline — bekh: without it the page is right. A small `seed` button above each passage opens it in a floating box over the passage; click again / elsewhere / esc closes.
- **pic**: a quiet word next to `seed` (it appears once the plate has landed) → the plate full screen, uncropped. Double-clicking a painted dream outside its words does the same. Click / double-click / esc closes.
- Phones (<820px): one column, trickle static above its passages.

## Knobs (all remembered per browser in localStorage; url params win)

| what | ui / keys | url |
|---|---|---|
| look | glass·dots switch; keys 1–7 | `?look=` |
| glass blur | `[` `]` | `?gb=` |
| font | font button / `f` `F` walk the shortlist | `?font=` (any) |
| passage size | `,` smaller · `.` bigger (per font) | — |
| wash darkness | `w` lighter · `W` darker (also `-` `=`) | `?wa=0.72` |
| screenshots | — | `?tail=N` (newest N, no scrolling) · `?only=<room>` (one passage, waits for its font) |
