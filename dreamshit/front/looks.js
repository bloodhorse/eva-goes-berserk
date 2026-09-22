// The looks: how an unfocused dream's painting is shown while you read another one.
// Every look we ever tried stays here as a named preset, never deleted — judgments made on
// one page flip on another, so reconsidering a look must cost one url (?look=name), not a
// re-implementation. Keys 1–n pick them live in this order; the first is the default.
//
// kind 'dots'  : the painting dithered to the house palette on a canvas, then css on top
//                (cell = dot size px, fog = blur the painting before dithering, 0 = off)
// kind 'frost' : the painting itself under a heavy css blur with grain pushed through
// kind 'signal': the painting as wide horizontal bars — lost sync; focus locks it in
//
// css may use var(--gb): the glass blur, tunable live with [ ] and ?gb=

const PALETTES = {
  // bekh's house palette (violet ground, pink and cyan light), as dot colours
  house: ['#1e1e22', '#2e3547', '#5b4a86', '#f29bea', '#7fe3f5', '#d4e3fe'],
  // the same hues pulled down and together — rejected: dumbing the colours defeats the point
  quiet: ['#1b1a20', '#262c3c', '#3a3155', '#6e4a72', '#3f6b78', '#7c8499'],
};

const LOOKS = {
  // chosen 2026-09-21: dots under a clean pane — palette-shaped colour, calm, readable
  glass:   { kind: 'dots', cell: 4, pal: 'house', css: 'blur(var(--gb)) saturate(1.35) brightness(1.12)', sheen: true },
  // sexy, but keeps all the brush-stroke noise
  bloom:   { kind: 'dots', cell: 4, pal: 'house', css: 'blur(1.6px) saturate(1.25) brightness(1.1)' },
  // grain fog: fine, not quite ours
  frost:   { kind: 'frost' },
  // blur-then-dither: calm, but kills the ornament
  fogdots: { kind: 'dots', cell: 4, pal: 'house', fog: 12 },
  // raw dither: too noisy, it dithers every brush stroke
  dots:    { kind: 'dots', cell: 4, pal: 'house' },
  quiet:   { kind: 'dots', cell: 6, pal: 'quiet' },
  // lost-sync bars: the most CRT, reads as broken rather than dreamy
  signal:  { kind: 'signal' },
};
