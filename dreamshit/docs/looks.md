# looks — pictures behind the words

## Principle

The plate carries the dream's meaning, so it stays whole: **style lives in the glass in front of the picture, not in the picture.** (The reference crushed its images only because Neocities gave it 10MB.) Dither is for time and attention, not the look of a painting.

**Focus follows reading:** the passage you're in shows its plate sharp; all others show the current *look* — this is what calms "everything everywhere all at once".

**Sameness is the main risk** (bekh): tens of plates from one model under one strong treatment become wallpaper. Variety must be designed in (treatment that reads the picture, per-dream dials, a mix of looks) — the search stays loose.

## Presets — shelved, never deleted

Judgments made on one page flip on another (wash, width, density all change them). So every look ever tried lives in `front/looks.js` as a named preset; reconsidering costs one url (`?look=name`), never a re-implementation. Same rule for fonts.

| look | what | verdict |
|---|---|---|
| **glass** (default) | plate dithered to the house palette (4px dots), then a clean pane: blur 8px, saturate 1.35, faint sheen | **chosen 2026-09-21** — palette-shaped colour, dots melt, calm, readable |
| **dots** | the raw 4px house-palette dither | bekh: "sexy as fuck" but noisy — on the quick switch next to glass |
| bloom | dots + 1.6px glow | the ornament bekh loves, still just as noisy |
| frost | heavy blur + grain on the painting itself | fine, not quite ours |
| fogdots | blur the plate, then dither | calm, but kills the ornament |
| quiet | muted palette, 6px cells | dumbing the colours defeats the point |
| signal | plate as wide horizontal bars (lost sync) | most CRT; reads broken, not dreamy |

## Wash (readability over the focused plate)

One even wash over the focused row, its darkness tuned by eye: `w` lighter, `W` darker (`?wa=`), remembered. bekh's best moments were at a light wash, the painting nearly clear — the heavy default (0.72) may be guarding against a ghost: most plates are dark and read fine lightly washed; only the occasional bright plate needs more. Idea, not built: a wash that **reads the picture** (brightness behind the text column → only as much wash as that plate needs).

Rejected: **hug** — darkness only behind the blocks of words, painting open elsewhere. bekh: "looks just too lame". Wash strength still waits on the font (see `reading.md`).

## Neural filters (parked)

Researched 2026-09-21: neural cellular automata, autoencoders/latent corruption (TAESD), fast style transfer, pixelization, learned halftoning, deepdream, cyclegan. bekh: mostly sucky; the one novel result (TAESD channel-shifted ghost doubles) would make every plate look the same. Revisit only with real references. A tiny CPPN seeded from the dream text was floated as a second, abstract image per dream — never a replacement for the plate.
