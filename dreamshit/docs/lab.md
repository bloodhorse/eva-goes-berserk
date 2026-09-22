# lab — sketches, tools, screenshots

## Sketches (`sketch/`, the attic the front grew out of)

- `index.html` — first sketch: four auto-scrolling columns over procedural moon/water/pylon placeholders, live decay (`?fast=20`).
- `three.html` — blind phase: three parallax columns with bekh's pasted text, one test picture (`sketch/pic/test.jpg`, macOS Sonoma wallpaper, git-ignored), five hand filters on keys 1–5.
- `stream.html` — a snapshot of the real stream with the looks on keys 1–7 (`?mat=`, `?gb=`, `?skip=N`). Snapshot in `sketch/data/` (git-ignored): `stream.json` from the API, `stream.js` = `window.STREAM = <json>;`, plates in `data/plate/`.
- Pages that read pixels must be served over http: `cd sketch && uv run --python 3.12 -m http.server 8765` (under `file://` the canvas is tainted and pictures vanish silently).

## Tools

- `tools/crush.py` — image → palette + bayer dither + transparency. `tools/placeholders.py` — the procedural placeholder images. Python only via uv, no venv: `uv run --python 3.12 --with pillow --with numpy tools/crush.py …`.

## Screenshots (headless Helium)

**After every deploy, screenshot the live page and look at it.** A probe that checks attributes can pass while the page is broken (2026-09-21: the lightbox's `display:flex` beat its `hidden` attribute and covered dreamshit.x in black; the probe said `hidden=true`).

`/Applications/Helium.app/Contents/MacOS/Helium --headless=new --disable-gpu --hide-scrollbars --window-size=1440,1400 --virtual-time-budget=5000 --screenshot=<png> <url>`

- Use `--virtual-time-budget`, not `--timeout` (with `--timeout` the page's own fetches never run).
- A page that scrolls itself comes out blank — use `?tail=N` (front) / `?skip=N` (sketch).
- In sketches, load data as a `<script>`, not `fetch` (a fetch loses the race).
- Probing state: `--dump-dom` with an injected `window.onerror` + a `setTimeout` that writes findings into `document.title`.
- A timed-out run leaves Helium helpers alive: kill them by numeric PID, never `pkill -f`.
- Font specimens: loop over the names in `front/fonts.js` (`grep -oE '^  [a-z_0-9]+:'`), one `?only=<room>&font=<name>` shot each into `shots/fonts/NN_name.png`; about one in seven stalls — retry those by name. (zsh doesn't word-split `$VAR` in a `for`: use a `while read` over a file.)
- Save to `shots/` (git-ignored), tag `claude`, and **open the folder in Finder for bekh — not kitty** (paintings look bad in the kitty mosaic).
