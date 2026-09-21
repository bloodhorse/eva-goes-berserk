# front — the project (`front/`)

The dream-stream front as its own project, reading eva live. Merging it into eva's own page comes later, on our terms — so: plain html/css/js, no build step, merge = copy-paste, not a port.

## Where it runs

- **Live: `https://dreamshit.x`** (also `d.x`) on the mini. Caddy serves `/srv/dreamshit` and sends `/api/*` and `/stream/plate/*` to eva's own upstream — the `eva_upstream` snippet in `~/tower/forge/mini/minidns/etc/caddy/Caddyfile`, shared with eva.x so the two can't drift. Same origin, so no CORS, and the looks can read plate pixels.
- **Deploy:** `front/deploy.sh` (rsyncs the page files, prints the status code). New page file → add it to the rsync list.
- **Caddy rollback** (backup made when dreamshit.x was added):
  `ssh bek@miniarch 'sudo cp /etc/caddy/Caddyfile.bak-pre-dreamshit /etc/caddy/Caddyfile && sudo systemctl reload caddy'`
- **Local:** `.venv/bin/python front/serve.py` → `http://127.0.0.1:8766/`. Serves the folder and forwards the same two paths to eva.x server-side, verifying eva against `front/eva-root.crt` (the mini's public Caddy root).

## Files

- `index.html` — shell: status bar (state · age, font button, glass·dots switch), feed, lightbox.
- `style.css` — layout, voices, plates, wash, looks' css.
- `app.js` — live stream, packs, focus, looks painting, font/wash knobs, lightbox.
- `looks.js` — the picture-look presets (see `looks.md`).
- `fonts.js` — the passage-font presets (see `reading.md`).

## How it behaves

- Loads the newest 48 passages, lands on the newest at the reading line, polls `n=5` every 60s. New passages append at the bottom: followed if you're on the newest, otherwise counted on a "new" button. Late plates and readings attach in place; the trickle updates as its story grows.
- **Packs:** one per dream. Rows are 3-column grids (`slot | text | reading`); the pack's **rail** lies over the slot column (measured in js) and holds the dream's **trickle**, `position: sticky`, 60% of the column, centred. It rides along through its own dream only and hands over at the boundary. A trickle taller than the screen scrolls until its end meets the bottom edge, then sticks (top = `min(48, vh − h − 24)`).
- **Focus follows reading:** the passage under the middle of the screen is focused — its plate sharp and washed dark behind the words; every other plate shows the current look. Works on phones (no hover).
- **Double-click** a painted dream outside its words → the plate full screen, uncropped. Click / double-click / esc closes.
- Phones (<820px): one column, trickle static above its passages.

## Knobs (all remembered per browser in localStorage; url params win)

| what | ui / keys | url |
|---|---|---|
| look | glass·dots switch; keys 1–7 | `?look=` |
| glass blur | `[` `]` | `?gb=` |
| font | font button (shift = back); `f` / `F` | `?font=` |
| wash | `w` even↔hug; `-` `=` darkness | `?wash=hug&wa=0.72` |
| screenshots | — | `?tail=N` (newest N, no scrolling) |
