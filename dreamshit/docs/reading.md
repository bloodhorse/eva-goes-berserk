# reading — type and calm

It's all about reading. Everything visual is judged by one test: does it help or hurt someone reading for twenty minutes?

## Nothing moves on its own

bekh's rule: no rolling scanlines, breathing dots, crawling grain, blinking words — fauux can afford constant motion, a page for reading can't. Motion only answers the reader (focus changes on scroll, new passages arriving, the lightbox). Scanlines are out entirely, even still ones. The fauux motion tricks stay in the lab unless tied to a reader's action.

## The font

The passage font is the centre of attention. Target: the sharp, hard balance — stylish, carries the atmosphere, yet effortless to read. Only the passage is in a reading face; every label (names, numbers, seed, timestamps, trickle, reading) wears the same spaced Courier.

- **Chosen: `newsreader` at 19px** (2026-09-21). 18 ran ~95-character lines; 20 was too big (bekh). Fine-tuning is live: `,` / `.` nudge the size, then the number bekh lands on gets baked into `fonts.js`. **Weight is the open dial** (bekh, 2026-09-22: almost good, wants it thinner, or a new round): newsreader is a variable face and now loads its whole axis, `t` / `T` walk it in steps of 50 from 400 down to 200 (or up); the weight he lands on gets baked in as `weight:` the same way, and if none of them is it, round three.
- **The show** (`SHORTLIST` in `fonts.js`, what the font button and `f` / `F` cycle): bekh, 2026-09-22 — the serious faces, each at its thinnest cut, majormono the reference for how thin; the cutesy ones (typewriter imitations `courier`, `typewriter`, `specialelite`; pixel `vt323`, `dotgothic`) are out of the walk but stay as presets behind `?font=`. Thin where a face has it: spectral 200, cormorant 300, plex mono 200, gill sans light, avenir next ultralight, newsreader on its axis; the rest have a single weight. The bar names the one showing.
- **Everything tried stays** in `fonts.js` (29 faces, each with its own tuned size/leading/tracking), reachable by `?font=`. Round one: only `lain` (Times, smoothing off, wide) came close. Round two went as wide as possible — lain variants, sharp serifs, old print, sans, monos, typewriters, dot-matrix. Specimens: `shots/fonts/NN_name.png`, one passage per font over one painting (`?only=<room>&font=<name>`, see `lab.md`).

Coupling with the wash: colour alone doesn't buy readability over a painting (a pink font at white's brightness reads the same; a darker one needs *more* wash). Weight and size do. So: pick the font first, then tune the wash for it by eye.
