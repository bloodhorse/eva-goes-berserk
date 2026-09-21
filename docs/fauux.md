# fauux — the reference, studied 2026-09-21

fauux.neocities.org ("wired sound for wired people", since 2013). We studied its mechanics, not its details. **Steal techniques, never their art, gifs or text.** Nothing from their site lives in this repo.

## How it's made

One person, Photoshop throughout (XMP `CreatorTool` on 24 gifs: CS6 Mac 2013–16, PS 21/22.3 later, PS 26.6 in 2025 for the dither-decay tile). Sources: a big found-image hoard (a 3300-file Lain folder), their own 3D Lain renders, cut-outs "in PS". The dithered look started as a constraint — Neocities' 10MB limit (their 2023 post). Code is hand-written, Dreamweaver-era, with copy-pasted 2000s scripts. Animations are short (2–24 frames, 40–100ms): one drawing with its edges warped per frame (breath.html), or one cut-out moved like paper animation (enlightenment.html). Real skill = taste and a strict three-colour palette (`#000`, `#c1b492`, `#d2738a`); when they dropped it (later statue/glitch pages), it went generic.

## Mechanics as primitives

- **Layering with transparency** — full-page tiles and 1-bit cut-outs stacked; depth without 3D.
- **Palette as identity** — one palette unifies wildly different sources.
- **Fake signal** — 3×3 phosphor tile of the base pink split into R/G/B rows rolling every 40ms; a 1×1-pixel gif as a full-screen lightning storm; short horizontal streak jitter.
- **Time-based decay** — a dither tile that plays once: nothing for 30s, fast to ~85% by 3 min, full by 5:30; content panels erode over 12 min.
- **Staggered rhythm** — one 2s period, delays stepped 0.4s → blink waves; many clocks at different scales.
- **Parallax by speed** — rain tiles 64/128/256px, dimmer = smaller = slower.
- **Navigation as drift** — 115 of 157 pages have exactly one exit, the image itself; no menu, no back.
- **Sound** — a hidden looping track per page; two loops of coprime length phase against each other.

What survived into the front: palette as identity, layering, dither (as a look, not decay). Motion-based primitives are out of the front by the reading rule (`reading.md`).
