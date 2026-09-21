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
};
