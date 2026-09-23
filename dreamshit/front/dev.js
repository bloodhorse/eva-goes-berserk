// ---- the dev hub ---------------------------------------------------------------------------
// bekh, 2026-09-24: "one meta all-encompassing dev page … just buttons for different categories
// … a hub for all the dev things, compacted well and easily accessed." Every dial the page has,
// in one panel on the real page (the type, the wash and the band can only be judged over the
// real dreams and paintings), by tab. Opened by ?dev and nothing else, remembered per browser;
// ?dev=0 puts it away and forgets. ?tune=ribbon still works: it opens here on the analyst's tab.
//
// Mouse only, never keys alone — bekh browses with vimium, which eats bare keypresses
// (dreamshit/CLAUDE.md). The old keys still work for whoever has them; the panel re-reads its
// values whenever one is pressed, so it never shows a stale number.
//
// It drives the page through app.js's own setters (a classic script's top-level names are shared
// with this one), so a dial here does exactly what its key or button does, remembered the same way.
// A dial is { label, min, max, step, get, set, fmt? }; a choice is { label, options, get, set }.
// To add one: a line in its tab below.

// one function scope: app.js's top-level names (sync, draw…) are shared with this script, and a
// second top-level declaration of one would throw and take the hub down with it
(() => {
const DEV_ON = (() => {
  if (params.get('dev') === '0') { store('dev', ''); return false; }
  if (params.has('dev') || params.get('tune') === 'ribbon') { store('dev', '1'); return true; }
  return store('dev') === '1';
})();

// his line's face and base size — dials that exist only here, applied on every load in the
// browser that set them (like the ribbon's), whether or not the panel is open
function setRibbonFont(name) {
  const st = document.body.style;
  if (name && FONTS[name]) {
    loadFace(FONTS[name]);
    st.setProperty('--rf', FONTS[name].family); st.setProperty('--rw', FONTS[name].weight || 400);
  } else { st.removeProperty('--rf'); st.removeProperty('--rw'); name = ''; }
  store('rfont', name);
  refit();
}
function setRibbonSize(v) {
  if (v) document.body.style.setProperty('--rfs0', v + 'px'); else document.body.style.removeProperty('--rfs0');
  store('rfs0', v || '');
  refit();
}
setRibbonFont(store('rfont') || '');
setRibbonSize(+(store('rfs0') || 0));

// a url-only experiment (not remembered by design — app.js says why): the dial reloads the page
// with the param set, which is what those experiments have always been
const reloadWith = (k, v) => { const q = new URLSearchParams(location.search); v === null ? q.delete(k) : q.set(k, v); location.search = q; };
const fontSize = () => +(store('fsize:' + FONT) || FONTS[FONT].size);
const fontWeight = () => +(store('fw:' + FONT) || FONTS[FONT].weight || 400);
const fontLead = () => +(store('flead:' + FONT) || FONTS[FONT].lead);

const TABS = {
  type: [
    { label: 'passage', options: SHORTLIST.concat(FONT_NAMES.filter(n => !SHORTLIST.includes(n))), get: () => FONT, set: setFont, wrap: true },
    { label: 'size', min: 12, max: 30, step: .5, get: fontSize, set: v => { store('fsize:' + FONT, v); setFont(FONT); }, fmt: v => v + 'px' },
    { label: 'weight', min: 200, max: 800, step: 50, get: fontWeight, set: v => { store('fw:' + FONT, v); setFont(FONT); } },
    { label: 'leading', min: 1, max: 2.4, step: .05, get: fontLead, set: v => { store('flead:' + FONT, v); setFont(FONT); }, fmt: v => v.toFixed(2) },
    { label: 'sides', min: 10, max: 20, step: .5, get: () => TSIZE, set: v => { setSides(v); store('tsize', TSIZE); }, fmt: v => v + 'px', note: 'the telling and the reading (the reading a pixel above)' },
    { label: 'his line', options: ['passage', ...SHORTLIST], get: () => store('rfont') || 'passage', set: n => setRibbonFont(n === 'passage' ? '' : n), wrap: true },
    { label: 'his size', min: 11, max: 28, step: 1, get: () => +(store('rfs0') || 18), set: setRibbonSize, fmt: v => v + 'px', note: 'where his line starts before it steps down to fit' },
  ],
  analyst: 'ribbon',   // the ribbon tuner's own dials (app.js RT), moved in whole
  'wash & look': [
    { label: 'look', options: LOOK_NAMES, get: () => LOOK, set: setLook },
    { label: 'glass', min: 0, max: 20, step: 1, get: () => GB, set: v => { GB = v; setLook(LOOK); }, fmt: v => v + 'px', note: 'blur on the unfocused plates' },
    { label: 'wash', min: 0, max: .95, step: .01, get: () => WA, set: v => { WA = v; setWash(); }, fmt: v => v.toFixed(2), note: 'the focused plate under the words' },
    { label: 'ink', button: 'open the ink panel', set: () => inkPanel(true) },
  ],
  layout: [
    { label: 'trickle', options: TRICKLE_MODES, get: () => TRICKLE, set: setTrickleMode },
    { label: 'align', options: ALIGNS, get: () => ALIGN, set: a => reloadWith('align', a === 'even' ? null : a), note: 'stretch only · reloads, never remembered' },
    { label: 'band', min: 0, max: 1, step: .05, get: () => BAND, set: v => reloadWith('band', v), fmt: v => v.toFixed(2), lazy: true, note: 'align=band only · reloads on release' },
    { label: 'seed line', options: ['on', 'off'], get: () => GHOST ? 'on' : 'off', set: o => reloadWith('ghost', o === 'off' ? '0' : null), note: 'reloads' },
  ],
  benches: [
    { label: 'band', link: '/band/', text: 'the analyst\'s band, three in a row — sketch/band' },
    { label: 'stills', link: '?tail=12', text: 'the newest twelve, nothing live — what headless shots see' },
    { label: 'eva', link: 'https://eva.x/stream', text: 'eva\'s own stream page, the placeholder this front replaces' },
  ],
};

const dev = $('#dev');
const TAB_NAMES = Object.keys(TABS);
let tab = TAB_NAMES.includes(store('devtab')) ? store('devtab') : 'type';
if (params.get('tune') === 'ribbon') tab = 'analyst';

function sync() {   // every control in the open tab shows what the page is doing right now
  for (const c of dev.querySelectorAll('[data-dial]')) c._sync && c._sync();
}
function control(d) {
  const row = document.createElement('div'); row.className = 'drow'; row.dataset.dial = d.label;   // not .row: that is a dream's row
  const name = document.createElement('span'); name.className = 'name'; name.textContent = d.label;
  if (d.note) name.title = d.note;
  row.append(name);
  if (d.options) {
    const box = document.createElement('div'); box.className = 'opts' + (d.wrap ? ' wrap' : '');
    for (const o of d.options) {
      const b = document.createElement('button'); b.textContent = o;
      b.onclick = () => { d.set(o); sync(); };
      box.append(b);
    }
    row.append(box);
    row._sync = () => { const v = d.get(); for (const b of box.children) b.classList.toggle('on', b.textContent === v); };
  } else if (d.button) {
    const b = document.createElement('button'); b.className = 'act'; b.textContent = d.button;
    b.onclick = e => { e.stopPropagation(); d.set(); };
    row.append(b);
  } else if (d.link) {
    const a = document.createElement('a'); a.href = d.link; a.textContent = d.text; a.target = d.link.startsWith('http') ? '_blank' : '';
    row.append(a);
  } else {
    const r = document.createElement('input'); r.type = 'range'; r.min = d.min; r.max = d.max; r.step = d.step;
    const out = document.createElement('output');
    const fmt = d.fmt || (v => String(v));
    r[d.lazy ? 'onchange' : 'oninput'] = () => { d.set(+r.value); out.textContent = fmt(+r.value); };
    if (d.lazy) r.oninput = () => { out.textContent = fmt(+r.value); };
    row.append(r, out);
    row._sync = () => { const v = d.get(); r.value = v; out.textContent = fmt(v); };
  }
  if (d.note) { const n = document.createElement('span'); n.className = 'note'; n.textContent = d.note; row.append(n); }
  row._sync && row._sync();
  return row;
}

function draw() {
  // the ribbon tuner goes home before the clear: app.js writes into its inputs from any tab
  const rt = $('#ribbontune'); if (dev.contains(rt)) { rt.hidden = true; document.body.append(rt); }
  dev.innerHTML = '';
  const head = document.createElement('div'); head.className = 'tabs';
  for (const t of TAB_NAMES) {
    const b = document.createElement('button'); b.textContent = t; b.classList.toggle('on', t === tab);
    b.onclick = () => { tab = t; store('devtab', t); draw(); };
    head.append(b);
  }
  const x = document.createElement('button'); x.className = 'x'; x.textContent = '–'; x.title = 'fold (the dev chip opens it again)';
  x.onclick = () => fold(true);
  head.append(x);
  dev.append(head);
  const body = document.createElement('div'); body.className = 'body';
  if (TABS[tab] === 'ribbon') {
    // the ribbon tuner's own box, moved in as it is: app.js keeps driving its inputs
    const rt = $('#ribbontune'); rt.hidden = false; body.append(rt);
  } else for (const d of TABS[tab]) body.append(control(d));
  dev.append(body);
}
function fold(f) {
  dev.classList.toggle('folded', f); store('devfold', f ? '1' : '');
  if (!f) draw();
}

let opened = false;
function openHub() {
  opened = true; store('dev', '1');
  dev.hidden = false;
  const chip = document.createElement('button'); chip.id = 'devchip'; chip.textContent = 'dev';
  chip.onclick = () => fold(false);
  document.body.append(chip);
  draw();
  if (store('devfold') === '1') fold(true);
  // the old keys still move things: show their result here too
  addEventListener('keyup', () => { if (!dev.classList.contains('folded')) sync(); });
}
if (DEV_ON) openHub();
// the secret door (bekh, 2026-09-24): the status dot, top left. A press opens the hub on the spot;
// with it open, a press folds or unfolds it. Nothing on the dot gives it away — no hover, no title.
$('#status .dot').addEventListener('click', e => {
  e.stopPropagation();
  if (!opened) openHub();
  else fold(!dev.classList.contains('folded'));
});
})();
