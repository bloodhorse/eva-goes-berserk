// Fonts for the passage (the centre column), as presets like the looks: tried ones stay, never
// deleted. Each gets its own size / leading / spacing, so none loses to bad settings.
// The trickle and the reading keep their spaced mono for now — the passage is what gets read.
// google = a Google Fonts family spec to load on demand (the rest are Apple system fonts).

const FONTS = {
  iowan:     { family: '"Iowan Old Style", Palatino, Georgia, serif', size: 18, lead: 1.7, track: '.02em' },
  // fauux's trick: plain Times, smoothing off, wide spacing — the style is the treatment
  lain:      { family: '"Times New Roman", Times, serif', size: 19, lead: 1.75, track: '.09em', rough: true },
  // the first sketch's spaced typewriter (the pylon page)
  courier:   { family: '"Courier New", Courier, monospace', size: 16, lead: 1.8, track: '.12em', weight: 600 },
  charter:   { family: 'Charter, "Bitstream Charter", Georgia, serif', size: 18, lead: 1.7, track: '.01em' },
  baskerville: { family: 'Baskerville, "Baskerville Old Face", serif', size: 19.5, lead: 1.65, track: '.015em' },
  garamond:  { family: '"EB Garamond", Garamond, serif', size: 20, lead: 1.65, track: '.01em', google: 'EB+Garamond:wght@400;500' },
  plexmono:  { family: '"IBM Plex Mono", Menlo, monospace', size: 15.5, lead: 1.8, track: '0', google: 'IBM+Plex+Mono:wght@400;500' },
  // the wild card: a CRT terminal face, readable only because it's big
  vt323:     { family: 'VT323, monospace', size: 25, lead: 1.35, track: '.02em', google: 'VT323' },

  // ---- round two (2026-09-21): as diverse as possible ----
  // lain's neighbourhood: the same treatment, dials moved
  lain_tight:  { family: '"Times New Roman", Times, serif', size: 19, lead: 1.7, track: '.03em', rough: true },
  lain_big:    { family: '"Times New Roman", Times, serif', size: 21, lead: 1.65, track: '.06em', rough: true },
  // sharper serifs
  oldstandard: { family: '"Old Standard TT", serif', size: 18.5, lead: 1.75, track: '.03em', google: 'Old+Standard+TT:wght@400;700' },
  spectral:    { family: 'Spectral, serif', size: 17.5, lead: 1.75, track: '.01em', google: 'Spectral:wght@300;400' },
  caslon:      { family: '"Libre Caslon Text", serif', size: 17, lead: 1.8, track: '.01em', google: 'Libre+Caslon+Text' },
  didot:       { family: 'Didot, "Bodoni 72", serif', size: 20, lead: 1.6, track: '.02em' },
  hoefler:     { family: '"Hoefler Text", serif', size: 19, lead: 1.65, track: '.01em' },
  // bekh's pick — 19px: 18 ran ~95-character lines, 20 was too big (bekh). a variable font: the
  // whole weight axis is loaded so t / T can walk it thinner (bekh, 2026-09-22: almost good, thinner)
  newsreader:  { family: 'Newsreader, serif', size: 19, lead: 1.65, track: '0', google: 'Newsreader:opsz,wght@6..72,200..800' },
  // elegant / old print
  cormorant:   { family: '"Cormorant Garamond", serif', size: 21, lead: 1.55, track: '.01em', weight: 500, google: 'Cormorant+Garamond:wght@400;500;600' },
  fell:        { family: '"IM Fell English", serif', size: 19, lead: 1.6, track: '.01em', google: 'IM+Fell+English' },
  // sans
  futura:      { family: 'Futura, sans-serif', size: 16.5, lead: 1.8, track: '.04em' },
  gill:        { family: '"Gill Sans", sans-serif', size: 18, lead: 1.7, track: '.02em' },
  avenir:      { family: '"Avenir Next", sans-serif', size: 16.5, lead: 1.8, track: '.01em' },
  optima:      { family: 'Optima, sans-serif', size: 18, lead: 1.7, track: '.01em' },
  syne:        { family: 'Syne, sans-serif', size: 17, lead: 1.7, track: '.01em', google: 'Syne:wght@400;500' },
  // monos and typewriters
  spacemono:   { family: '"Space Mono", monospace', size: 15, lead: 1.85, track: '0', google: 'Space+Mono' },
  sharetech:   { family: '"Share Tech Mono", monospace', size: 17, lead: 1.75, track: '.02em', google: 'Share+Tech+Mono' },
  typewriter:  { family: '"American Typewriter", serif', size: 16.5, lead: 1.8, track: '.02em' },
  specialelite:{ family: '"Special Elite", monospace', size: 16.5, lead: 1.8, track: '.01em', google: 'Special+Elite' },
  // oddballs
  dotgothic:   { family: 'DotGothic16, monospace', size: 17, lead: 1.8, track: '.04em', google: 'DotGothic16' },
  majormono:   { family: '"Major Mono Display", monospace', size: 15, lead: 1.9, track: '.05em', google: 'Major+Mono+Display' },
};

// what the font button and f / F cycle through: the whole show, every face ever tried, in the
// order above (bekh, 2026-09-22: put them all on the site so he can shuffle them over real
// dreams). the two he had kept — newsreader, majormono — open the walk; the leash is gone.
const SHORTLIST = ['newsreader', 'majormono', ...Object.keys(FONTS).filter(n => n !== 'newsreader' && n !== 'majormono')];
