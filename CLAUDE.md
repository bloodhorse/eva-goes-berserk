# dream engine (dreamst)

A web page made of many streams of text flowing in parallel columns, with images living underneath them. CRT / wired / lain-adjacent atmosphere, but its own thing. The end goal: writing a new dream means editing a small readable file, not code.

## Reference and the one rule

Reference site: fauux.neocities.org ("wired sound for wired people"). We studied its mechanics, not its details. **Steal techniques, never their art, gifs or text.** We bring our own images and words. Nothing from their site lives in this repo.

## Primitives we took from the reference

- **Layering with transparency.** Full-page tiles and cut-out images stacked; empty pixels let the layer below through. Depth without 3D.
- **Palette as identity.** 3–4 colors per dream, applied to images at bake time and to text/CSS at runtime. This is what makes images from anywhere read as one world. When the reference dropped its palette, it went generic instantly.
- **Fake signal.** Phosphor-style row roll on the ground, occasional horizontal line jitter, flashes. Small, dumb loops that feel like one scene once stacked.
- **Time-based decay.** The page has a lifespan: it darkens the longer you stay (reference: nothing for 30s, fast fill to ~85% by 3 min, slow crawl to full by 5.5 min). We do it live, driven by time-since-open, so decay can also act on the streams.
- **Staggered rhythm.** Several clocks at different scales (texture ~40ms, text seconds, decay minutes); shared periods with staggered delays make waves, not strobes.
- **Parallax by speed.** A column's speed is its depth: far = slow, small, dim.
- **Navigation as drift.** One dream = one room with one hidden exit to the next dream.
- **Sound.** One loop per dream (two with coprime lengths phase nicely). Needs a click to unlock audio — make that click in-world.

## Baked vs live

Baked: only the art — palette crush, ordered dither, cut-out transparency (`tools/crush.py`). Live: anything that depends on time (streams, jitter, decay, flicker), because live effects can respond to decay and gifs can't.

## The dream file (planned, not built)

Header (palette, sound, decay, next) + stream blocks separated by `---`, each with image and speed, text inline — writing a dream is writing. Anything beyond that waits until a second real dream needs it.

## State

- `sketch/index.html` — one hand-coded page, no dream file yet. It exists to answer one question: does text streaming over images feel good, or turn into unreadable soup? Open it directly in a browser; `?fast=20` speeds up decay 20x for testing.
- `tools/crush.py` — image → palette + bayer dither + transparency. Run via uv (`.venv`).
- Images and text in the sketch are placeholders. Open questions: where real images come from, where stream text comes from, where the page will live (local vs the mini).

Next after the sketch verdict: the engine and the dream file, shaped by what the sketch taught us.
