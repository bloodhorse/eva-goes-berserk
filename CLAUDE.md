# dream engine (dreamst)

The look-and-feel lab for bekh's dream stream (`https://eva.x/stream`, on the mini): many streams of text in parallel columns with pictures living underneath them. CRT / wired / lain-adjacent atmosphere, but its own thing. Everything we find here is meant to flow back into the real stream page; this repo holds sketches, not the product.

The premise: everything in a dream is made by LLMs or other neural networks — the text, and the pictures (ChatGPT via codex, one per passage; codex budget is the limit on how many get painted). For now the filtering is hand-written; the question of doing it with small neural networks is parked until we have references and taste to judge against (see "Neural filters" below).

## The real stream (what the page must serve)

- A passage lands roughly every 5 minutes; a story is 4 passages ("turn n of 4").
- Three voices, three columns: **told** (the story so far, grows each turn) · **text** (the passage) · **reading** (an interpretation of the passage).
- Each passage should get a picture ("plate"): currently palette-knife oil paintings in bekh's house palette.
- API the sketch snapshots from: `https://eva.x/api/stream?n=16&all=1` → `{pages[{room, text, ts, reading{text,ts}, story{dream,text,turn,of}, plate}], status{state,interval}}`, newest first.
- **House palette is bekh's** (used across his projects): violet ground, pink, cyan as highlight. From the live page: `#232323` bg, `#d4e3fe` ink, `#f29bea`/`#f5c8fe` pink, `#7fe3f5`/`#c6f1fe` cyan, `#2e3547` line.

## Reference and the one rule

Reference site: fauux.neocities.org. We studied its mechanics, not its details. **Steal techniques, never their art, gifs or text.** Nothing from their site lives in this repo.

## Primitives we took from the reference

- **Layering with transparency.** Stacked layers; empty pixels let the layer below through. Depth without 3D.
- **Palette as identity.** One palette holds disparate pictures together. When the reference dropped its palette it went generic instantly.
- **Fake signal.** Row roll, line jitter, flashes. Small dumb loops that feel like one scene once stacked.
- **Time-based decay.** The page darkens the longer you stay; live, so it can act on text too.
- **Staggered rhythm.** Several clocks at different scales; staggered delays make waves, not strobes.
- **Parallax by speed.** A column's speed is its depth: far = slow, small, dim.
- **Navigation as drift.** One room, one hidden exit.
- **Sound.** One loop per dream; the audio-unlock click should be in-world.

## Pictures

Style lives in the glass in front of the picture, not in the picture: the painting carries the dream's meaning, so it stays whole. Dither is reserved for time (arriving / leaving / attention), not for the look of the picture.

**Sameness is the main risk** (bekh): tens of pictures from the same model under one strong treatment turn into wallpaper. Variety has to be designed in — treatment that reads the picture, per-dream dials, a mix of treatments in the stream. Keep the search loose; nothing about the style is settled.

**Focus follows reading** (agreed): the passage under the middle of the screen is clear (the sharp painting, washed dark behind the words); the others go murky. Works on phones (no hover).

**Chosen murk (2026-09-21): `glass` at blur 8px** — the painting dithered to the house palette (4px dots), a little bloom, then a clean pane over it: 8px blur, saturate 1.35, a faint sheen (light top edge, dark bottom line), no grain. It keeps the palette-shaped colour of the dots while the dots themselves melt; calm and readable. Rejected on the way, all still on keys in `sketch/stream.html`: frost (grain fog), signal (lost-sync bars), dots (too noisy — dithers the brush-stroke detail), fogdots (blur-then-dither: calm but kills the ornament bekh loves), bloom (sexy but just as noisy), quiet (muted palette — dumbing the colours defeats the point).

## Neural filters (parked)

Researched 2026-09-21: NCA, autoencoders, style transfer, pixelization, learned halftoning, deepdream/cyclegan. bekh's verdict: mostly sucky. The one novel result was TAESD latent corruption (channel-shifted ghost doubles), but it would make every picture look the same. Revisit only with real references in hand. A tiny CPPN seeded from the dream text was floated as a second, abstract picture per dream — not as a replacement for the ChatGPT picture, which holds the meaning.

## State

- `sketch/stream.html` — **current work.** The real stream (snapshot) with the murk materials: keys 1–7 or `?mat=` (signal, dots, frost, fogdots, bloom, quiet, glass — default glass); `[ ]` or `?gb=` tunes the glass blur; `?skip=N` starts N passages in (no auto-scroll). Snapshot lives in `sketch/data/` (git-ignored; refresh with the curl above → `stream.json`, then regenerate `stream.js` as `window.STREAM = <json>;` and download plates to `data/plate/`).
- `sketch/three.html` — blind-phase sketch: three auto-scrolling columns at parallax speeds, one test picture, five hand filters on keys 1–5 (glass / lain / onebit / rgb / map).
- `sketch/index.html` — the first sketch (four columns over procedural moon/water/pylon placeholders).
- `tools/crush.py`, `tools/placeholders.py` — palette crush + dither, and the placeholder generator. Via uv (`.venv`).

Serving: pages that read pixels **must be served over http** (`cd sketch && ../.venv/bin/python -m http.server 8765`); under `file://` the canvas is tainted and pictures vanish silently.

Screenshots: headless Helium; load data as a `<script>`, not `fetch` (a fetch loses the race with the screenshot), and don't rely on auto-scroll (use `?skip=`). Save shots to `shots/` (git-ignored) and **open the folder in Finder for bekh — not kitty** (paintings look bad in the kitty mosaic).

Next (bekh's side track): the font. It is the centre of attention — it must carry the atmosphere yet be effortless to read, because the whole thing is reading. Candidates bekh liked: fauux's (plain Times, smoothing off, very wide spacing) and the first sketch's spaced Courier New. Plan: a font key in `stream.html` cycling tuned candidates over the real passages.

Ideas agreed but not built: text arriving live at the bottom with the tail forgotten (no archive), clickable depth (a side column comes forward), decay that eats words.
