// dream stream front — reads eva's stream live (through serve.py), oldest at the top, newest at
// the bottom. The passage under the middle of the screen is the one you're in: its painting is
// sharp; every other painting is shown through the current look (looks.js).

const $ = s => document.querySelector(s);
const params = new URLSearchParams(location.search);
const LOOK_NAMES = Object.keys(LOOKS);
// which look: ?look= wins, then the one the tumbler last left, then the first in looks.js
const saved = (() => { try { return localStorage.getItem('look'); } catch { return null; } })();
let LOOK = LOOKS[params.get('look')] ? params.get('look') : LOOKS[saved] ? saved : LOOK_NAMES[0];
let GB = params.has('gb') ? +params.get('gb') : 8;
const FIRST_LOAD = 48;       // passages on open; eva's own page takes a day, we keep it lighter for now
const POLL_MS = 60000;       // same pace as eva's page; a passage lands every ~5 min anyway

const rooms = new Map();     // room -> row state; a poll never renders a passage twice
const trickles = new Map();  // dream -> its trickle (the dream so far), which grows as the story does
let lastPack = null, lastRowEl = null, waiting = 0, status = null;

const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const when = ts => new Date(ts * 1000).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).toLowerCase();
const api = q => fetch('/api/stream?' + q, { cache: 'no-store' }).then(r => { if (!r.ok) throw r.status; return r.json(); });

const grainURL = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), id = x.createImageData(256, 256);
  for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() * 255 | 0; id.data[i] = id.data[i+1] = id.data[i+2] = v; id.data[i+3] = 255; }
  x.putImageData(id, 0, 0); return c.toDataURL();
})();

// ---- the passage's words, as eva shows them (ported from eva's stream page, same rules) -----
// the reader's two marks: magenta = what touched most, cyan = what felt most mysterious and
// meaningful (bekh, 2026-09-21). display is trimmed back to the last sentence end (the shelf keeps
// all of it), and anything before a [dream] label is dropped. always textContent: the text came
// back from a cli, and nothing in it may become markup.
const SENT_END = /[.!?…]["'”’»)\]]*/g;
const KEEP_AT_LEAST = 0.6;   // trimming away more than ~40% says there was no sentence to end
function trimAt(text) {
  let last = null, m;
  SENT_END.lastIndex = 0;
  while ((m = SENT_END.exec(text)) !== null) last = m;
  if (!last) return text.length;
  const cut = last.index + last[0].length;
  return cut < text.length * KEEP_AT_LEAST ? text.length : cut;
}
function afterDreamLabel(segs) {
  const LABEL = '[dream]';
  for (let i = segs.length - 1; i >= 0; i--) {
    const at = (segs[i].t || '').lastIndexOf(LABEL);
    if (at < 0) continue;
    const rest = segs[i].t.slice(at + LABEL.length).replace(/^[ \t]/, '');
    return [Object.assign({}, segs[i], { t: rest })].concat(segs.slice(i + 1)).filter(x => x.t);
  }
  return segs;
}
// old readings carry mark:true on any number of runs: first → magenta, second → cyan, rest plain
function twoMarks(segs) {
  if (!segs.some(s => s.mark === true)) return segs;
  let seen = 0;
  return segs.map(s => {
    if (s.mark !== true) return s;
    seen += 1;
    return Object.assign({}, s, { mark: seen === 1 ? 'touched' : seen === 2 ? 'strange' : false });
  });
}
function drawBody(body, p) {
  body.textContent = '';
  const segs = Array.isArray(p.segments) && p.segments.length
    ? twoMarks(afterDreamLabel(p.segments.filter(s => s.kind !== 'gone'))) : null;
  if (!segs || !segs.length) { const t = String(p.text || '').trim(); body.textContent = t.slice(0, trimAt(t)); return; }
  // a passage often begins with the space left over from the cut before it; don't indent the first line
  segs[0] = Object.assign({}, segs[0], { t: (segs[0].t || '').replace(/^\s+/, '') });
  const plain = segs.map(s => s.t).join(''), cut = trimAt(plain);
  let at = 0;
  for (const s of segs) {
    let t = s.t || '';
    if (at >= cut) break;
    if (at + t.length > cut) t = t.slice(0, cut - at);
    at += (s.t || '').length;
    if (!t) continue;
    if (!s.mark) { body.appendChild(document.createTextNode(t)); continue; }
    const span = document.createElement('span');
    span.className = s.mark === 'strange' ? 'lit-b' : 'lit-a';
    span.textContent = t;
    body.appendChild(span);
  }
}

// ---- rendering -------------------------------------------------------------------------
function buildRow(p) {
  const row = document.createElement('section'); row.className = 'row';
  // an empty first cell keeps the grid; the dream's trickle lives in its pack's rail, over this column
  const slot = document.createElement('div'); slot.className = 'slot';
  const text = document.createElement('div'); text.className = 'text';
  const body = document.createElement('div'); body.className = 'body';
  drawBody(body, p);
  // the name first — it's the first thing read and the thing a dream is chosen by (eva's order)
  const head = titleLine(p.name, p.verse);
  if (head) text.append(head);
  // the seed (the found text the dream grew from) stays out of the way: a small button above
  // the passage, opening a floating box over it (bekh: without the seed the page is right)
  if (p.seed && String(p.seed).trim()) {
    const btn = document.createElement('button'); btn.className = 'seedbtn'; btn.textContent = 'seed';
    const box = document.createElement('div'); box.className = 'seedbox'; box.hidden = true;
    box.textContent = String(p.seed).trim();
    btn.onclick = e => { e.stopPropagation(); const open = box.hidden; closeSeeds(); box.hidden = !open; };
    box.onclick = e => e.stopPropagation();
    text.append(btn, box);
  }
  const w = document.createElement('span'); w.className = 'when'; w.textContent = when(p.ts);
  text.append(body, w);
  const reading = document.createElement('div'); reading.className = 'reading';
  row.append(slot, text, reading);
  const r = { row, reading, plateUrl: null, step: 0, target: 0 };
  setReading(r, p.reading);
  if (p.plate) setPlate(r, p.plate);
  return r;
}

function setReading(r, rd) {
  if (!rd || r.readingTs === rd.ts) return;
  r.readingTs = rd.ts;
  r.reading.innerHTML = esc(rd.text) + `<span class="when">${when(rd.ts)}</span>`;
}

// a passage often gets its painting minutes after its text — so plates attach late, in place
function setPlate(r, url) {
  if (r.plateUrl === url) return;
  r.plateUrl = url;
  if (!r.plate) {
    const plate = document.createElement('div'); plate.className = 'plate';
    const img = new Image();
    const cv = document.createElement('canvas');
    const grain = document.createElement('div'); grain.className = 'grain'; grain.style.backgroundImage = `url(${grainURL})`;
    const sheen = document.createElement('div'); sheen.className = 'sheen';
    const wash = document.createElement('div'); wash.className = 'wash';
    plate.append(img, cv, grain, sheen, wash); r.row.prepend(plate); r.row.classList.add('plated');
    Object.assign(r, { plate, img, cv });
    img.onload = () => { r.dither = null; paint(r); };
    cv.style.filter = LOOKS[LOOK].css || '';
  }
  r.img.src = url;
}

// pages come newest first; the feed reads down, oldest first
// eva's title line: 'verse · name' (a passage: '10:4 · the body man'; a dream: '10 · its title').
// the number is grey, the name is ink; either may be missing
function titleLine(name, number) {
  if (!name && !number) return null;
  const h = document.createElement('p'); h.className = 'title';
  if (number) { const n = document.createElement('span'); n.className = 'verse'; n.textContent = name ? number + ' · ' : number; h.appendChild(n); }
  if (name) h.appendChild(document.createTextNode(name));
  return h;
}
// the trickle: the dream's own header (chapter · title), then the dream so far
function setTrickle(el, story) {
  if (el.dataset.text === (story.text || '') && el.dataset.title === (story.title || '') && el.dataset.ch === String(story.chapter || '')) return;
  el.dataset.text = story.text || ''; el.dataset.title = story.title || ''; el.dataset.ch = String(story.chapter || '');
  el.textContent = '';
  const head = titleLine(story.title, story.chapter ? String(story.chapter) : '');
  if (head) el.appendChild(head);
  el.appendChild(document.createTextNode(story.text || ''));
}

// one pack per dream: its passages, plus a rail down the left column holding the trickle.
// the trickle is sticky inside the rail, so it rides along through its own dream's passages
// and hands over to the next dream's trickle at the boundary
function newPack(p) {
  const dream = p.story && p.story.dream || null;
  const el = document.createElement('div'); el.className = 'pack';
  const rail = document.createElement('div'); rail.className = 'rail';
  const trickle = document.createElement('div'); trickle.className = 'trickle';
  if (dream) { setTrickle(trickle, p.story); trickles.set(dream, trickle); }
  rail.appendChild(trickle); el.appendChild(rail);
  $('#feed').appendChild(el);
  return { el, rail, trickle, dream };
}
function render(pages) {
  const fresh = pages.slice().reverse().filter(p => !rooms.has(p.room));
  for (const p of fresh) {
    const dream = p.story && p.story.dream || null;
    if (!lastPack || !dream || lastPack.dream !== dream) lastPack = newPack(p);
    const r = buildRow(p);
    rooms.set(p.room, r);
    lastPack.el.appendChild(r.row);
    lastRowEl = r.row;
  }
  if (fresh.length) placeRails();
  return fresh.length;
}
// the rail sits exactly over the rows' first column; measured, because the grid decides it
function placeRails() {
  for (const pack of document.querySelectorAll('.pack')) {
    const slot = pack.querySelector('.slot'); if (!slot) continue;
    const rail = pack.querySelector('.rail');
    rail.style.left = slot.offsetLeft + 'px'; rail.style.width = slot.offsetWidth + 'px';
  }
  stickTrickles();
}
// a trickle that fits sticks under the status bar; a taller one scrolls until its END meets the
// bottom of the screen and sticks there — read top to bottom as you scroll, nothing ever cut off
function stickTrickles() {
  for (const t of trickles.values()) {
    const h = t.offsetHeight;
    t.style.top = Math.min(48, innerHeight - h - 24) + 'px';
  }
}
addEventListener('resize', placeRails);
addEventListener('load', placeRails);

// update what already exists: late paintings, late readings, the trickle growing
function sync(pages) {
  const seen = new Set();
  for (const p of pages) {
    const r = rooms.get(p.room);
    if (r) { if (p.plate) setPlate(r, p.plate); setReading(r, p.reading); }
    const dream = p.story && p.story.dream;
    if (dream && !seen.has(dream) && trickles.has(dream)) { setTrickle(trickles.get(dream), p.story); seen.add(dream); }
  }
  stickTrickles();
}

function ago(t) {
  const m = Math.max(0, Math.round((Date.now() / 1000 - t) / 60));
  return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : Math.round(m / 60) + ' h ago';
}
function drawStatus(s) {
  if (s) status = s;
  const el = $('#status');
  if (!status) return;
  el.className = status.state || '';
  el.querySelector('.what').textContent = `${status.state} · ${ago(status.since)}`;
}
function trouble(msg) { const el = $('#status'); el.className = ''; el.querySelector('.what').textContent = msg; }

// ---- reading position --------------------------------------------------------------------
const lastRow = () => lastRowEl;
function toNewest(smooth) {
  const r = lastRow(); if (!r) return;
  // page coordinates, not offsetTop: rows sit inside packs, so offsetTop is measured from the pack
  const b = r.getBoundingClientRect();
  scrollTo({ top: scrollY + b.top + b.height / 2 - innerHeight / 2, behavior: smooth ? 'smooth' : 'auto' });
}
let focused = null;
function focusRow() {
  const mid = innerHeight / 2;
  let best = null, bestD = Infinity;
  for (const r of rooms.values()) {
    const b = r.row.getBoundingClientRect();
    if (b.bottom < -innerHeight || b.top > 2 * innerHeight) continue;
    const d = b.top <= mid && b.bottom >= mid ? 0 : Math.min(Math.abs(b.top - mid), Math.abs(b.bottom - mid));
    if (d < bestD) { bestD = d; best = r; }
  }
  if (best === focused) return;
  if (focused) { focused.row.classList.remove('focus'); focused.target = 0; }
  if (best) { best.row.classList.add('focus'); best.target = STEPS; }
  focused = best;
  if (focused && focused.row === lastRow()) { waiting = 0; $('#fresh').hidden = true; }
}

// ---- the looks ---------------------------------------------------------------------------
const STEPS = 6;   // 0 = full look, STEPS = the sharp painting
const B4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const PAL = Object.fromEntries(Object.entries(PALETTES).map(([k, v]) => [k, v.map(rgb)]));

function cover(ctx, img, w, h) {
  const s = Math.max(w / img.naturalWidth, h / img.naturalHeight);
  ctx.drawImage(img, (w - img.naturalWidth * s) / 2, (h - img.naturalHeight * s) / 2, img.naturalWidth * s, img.naturalHeight * s);
}

function paint(r) {
  if (!r.plate || !r.img.naturalWidth) return;
  const look = LOOKS[LOOK], W = r.plate.clientWidth, H = r.plate.clientHeight, k = r.step;
  if (look.kind === 'frost') return;   // pure css
  r.cv.style.display = k >= STEPS ? 'none' : 'block';
  if (k >= STEPS || !W || !H) return;
  if (look.kind === 'signal') {
    const t = 1 - k / STEPS;
    const bw = Math.max(1, Math.round(2 + 70 * t * t)), bh = Math.max(1, Math.round(1 + 5 * t));
    r.cv.width = Math.max(1, Math.round(W / bw)); r.cv.height = Math.max(1, Math.round(H / bh));
    const c = r.cv.getContext('2d'); c.imageSmoothingEnabled = true; cover(c, r.img, r.cv.width, r.cv.height);
    return;
  }
  // dots: nearest house colour per pixel with an ordered dither between them; focusing thins
  // the dots away in the same bayer order, so the painting shows through a thinning screen
  const S = look.cell, w = Math.ceil(W / S), h = Math.ceil(H / S), pal = PAL[look.pal];
  if (!r.dither || r.dither.width !== w || r.dither.height !== h || r.ditherLook !== LOOK) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    const x = c.getContext('2d', { willReadFrequently: true });
    if (look.fog) {
      // shrink hard, stretch back smooth: the brush strokes are gone before the dither sees them
      const t = document.createElement('canvas'); t.width = Math.max(2, w / look.fog | 0); t.height = Math.max(2, h / look.fog | 0);
      cover(t.getContext('2d'), r.img, t.width, t.height);
      x.imageSmoothingQuality = 'high'; x.drawImage(t, 0, 0, w, h);
    } else cover(x, r.img, w, h);
    const id = x.getImageData(0, 0, w, h), d = id.data;
    for (let y = 0; y < h; y++) for (let xx = 0; xx < w; xx++) {
      const i = (y * w + xx) * 4, o = (B4[(y & 3) * 4 + (xx & 3)] / 16 - .5) * 64;
      let bi = 0, bd = Infinity;
      for (let j = 0; j < pal.length; j++) {
        const q = pal[j], dr = d[i] + o - q[0], dg = d[i+1] + o - q[1], db = d[i+2] + o - q[2];
        const dist = dr * dr * .3 + dg * dg * .59 + db * db * .11;
        if (dist < bd) { bd = dist; bi = j; }
      }
      const q = pal[bi]; d[i] = q[0]; d[i+1] = q[1]; d[i+2] = q[2]; d[i+3] = 255;
    }
    r.dither = id; r.ditherLook = LOOK;
  }
  r.cv.width = w; r.cv.height = h;
  const keep = 1 - k / STEPS, out = new ImageData(new Uint8ClampedArray(r.dither.data), w, h);
  if (keep < 1) for (let y = 0; y < h; y++) for (let xx = 0; xx < w; xx++) {
    if (B4[(y & 3) * 4 + (xx & 3)] / 16 >= keep) out.data[(y * w + xx) * 4 + 3] = 0;
  }
  r.cv.getContext('2d').putImageData(out, 0, 0);
}

function setLook(name) {
  LOOK = name;
  const look = LOOKS[name];
  // only our own classes: the font's (rough) lives on body too
  for (const c of [...document.body.classList]) if (c.startsWith('k-')) document.body.classList.remove(c);
  document.body.classList.add('k-' + look.kind);
  document.body.classList.toggle('sheen', !!look.sheen);
  document.body.style.setProperty('--gb', GB + 'px');
  for (const r of rooms.values()) if (r.plate) { r.cv.style.filter = look.css || ''; r.dither = null; r.step = r.target; paint(r); }
  for (const b of document.querySelectorAll('#flip button')) b.classList.toggle('on', b.dataset.look === name);
  try { localStorage.setItem('look', name); } catch {}
  tell(`look: ${name}   [1-${LOOK_NAMES.length}]` + (/--gb/.test(look.css || '') ? `   blur ${GB}px  [ ]` : ''));
}
addEventListener('keydown', e => {
  const i = +e.key - 1; if (LOOK_NAMES[i]) return setLook(LOOK_NAMES[i]);
  if (e.key === '[' || e.key === ']') { GB = Math.max(0, Math.min(20, GB + (e.key === ']' ? 1 : -1))); setLook(LOOK); }
});
addEventListener('resize', () => { for (const r of rooms.values()) { r.dither = null; paint(r); } });

// steps move one notch every ~70ms toward their target: a lock that clicks in, not a fade
let lastStep = 0;
function loop(now) {
  focusRow();
  if (now - lastStep > 70) {
    lastStep = now;
    for (const r of rooms.values()) if (r.plate && r.step !== r.target) { r.step += Math.sign(r.target - r.step); paint(r); }
  }
  requestAnimationFrame(loop);
}

// ---- live --------------------------------------------------------------------------------
function poll() {
  api('n=5').then(d => {
    drawStatus(d.status);
    sync(d.pages || []);
    const wasAtNewest = focused && focused.row === lastRow();
    const n = render(d.pages || []);
    if (!n) return;
    if (wasAtNewest) return toNewest(true);
    waiting += n;
    const f = $('#fresh'); f.textContent = waiting === 1 ? 'new' : waiting + ' new'; f.hidden = false;
  }).catch(() => trouble("can't reach eva"));
}
$('#fresh').onclick = () => toNewest(true);
for (const b of document.querySelectorAll('#flip button[data-look]')) b.onclick = () => setLook(b.dataset.look);

// double-click a painted dream anywhere but its words → the painting full screen
$('#feed').addEventListener('dblclick', e => {
  if (e.target.closest('.text, .reading, .trickle, button')) return;
  const row = e.target.closest('.row.plated'); if (!row) return;
  const r = [...rooms.values()].find(x => x.row === row); if (!r || !r.img.src) return;
  getSelection().removeAllRanges();
  $('#lightbox img').src = r.img.src; $('#lightbox').hidden = false;
});
const closeBox = () => { $('#lightbox').hidden = true; };
function closeSeeds() { for (const b of document.querySelectorAll('.seedbox')) b.hidden = true; }
addEventListener('click', closeSeeds);
$('#lightbox').addEventListener('click', closeBox);
addEventListener('keydown', e => { if (e.key === 'Escape') { closeBox(); closeSeeds(); } });

// ---- font picker + wash knobs ------------------------------------------------------------
const store = (k, v) => { try { v === undefined ? v = localStorage.getItem(k) : localStorage.setItem(k, v); } catch {} return v; };
const FONT_NAMES = Object.keys(FONTS);
// newsreader: bekh's pick from round two (2026-09-21). the picker order stays as the specimens were numbered
const DEFAULT_FONT = 'newsreader';
let FONT = FONTS[params.get('font')] ? params.get('font') : FONTS[store('font')] ? store('font') : DEFAULT_FONT;
const loadedGoogle = new Set();
function setFont(name) {
  FONT = name; const f = FONTS[name], st = document.body.style;
  if (f.google && !loadedGoogle.has(f.google)) {
    loadedGoogle.add(f.google);
    const l = document.createElement('link'); l.rel = 'stylesheet';
    l.href = `https://fonts.googleapis.com/css2?family=${f.google}&display=swap`; document.head.appendChild(l);
  }
  st.setProperty('--tf', f.family); st.setProperty('--ts', f.size + 'px'); st.setProperty('--tlead', f.lead);
  st.setProperty('--ttrack', f.track); st.setProperty('--tw', f.weight || 400);
  document.body.classList.toggle('rough', !!f.rough);
  $('#fontbtn').textContent = 'font: ' + name;
  store('font', name);
  tell(`font: ${name}   ${f.size}px   [f / shift-f]`);
}
$('#fontbtn').onclick = e => step(e.shiftKey ? -1 : 1);
function step(d) { const i = FONT_NAMES.indexOf(FONT); setFont(FONT_NAMES[(i + d + FONT_NAMES.length) % FONT_NAMES.length]); }

// the focused plate's wash, tuned by eye: w lighter, W darker (also - and =). 0 = the bare painting
let WA = params.has('wa') ? +params.get('wa') : +(store('wa') || .72);
function setWash() {
  document.body.style.setProperty('--wa', WA.toFixed(2));
  store('wa', WA.toFixed(2));
  tell(`wash ${WA.toFixed(2)}   [w lighter · W darker]`);
}
function tell(msg) { const l = $('#label'); l.textContent = msg; l.style.opacity = 1; clearTimeout(l.t); l.t = setTimeout(() => l.style.opacity = 0, 1800); }
addEventListener('keydown', e => {
  if (e.key === 'f') step(1); else if (e.key === 'F') step(-1);
  else if ('wW-='.includes(e.key)) { WA = Math.max(0, Math.min(.95, WA + (e.key === 'W' || e.key === '=' ? .04 : -.04))); setWash(); }
});


setLook(LOOK);
setFont(FONT);
setWash();
// ?tail=N: only the newest N passages, no scrolling — for headless screenshots, which come out
// blank whenever the page scrolls itself
const TAIL = +params.get('tail') || 0;
// ?only=<room>: that one passage alone (focused) — for specimen screenshots; waits for the font
const ONLY = params.get('only');
const fontReady = () => ONLY ? Promise.race([document.fonts.load(`${FONTS[FONT].size}px ${FONTS[FONT].family}`), new Promise(r => setTimeout(r, 3000))]) : Promise.resolve();
api('n=' + (ONLY ? 60 : TAIL || FIRST_LOAD)).then(d => fontReady().then(() => d)).then(d => {
  if (ONLY) { d.pages = (d.pages || []).filter(p => p.room === ONLY); $('#feed').style.padding = '40px 0 0'; }
  render(d.pages || []);
  sync(d.pages || []);
  drawStatus(d.status);
  if (TAIL || ONLY) { if (TAIL) $('#feed').style.padding = '40px 0 0'; return; }
  toNewest(false);
  // fonts landing late reflow the page; stand on the newest passage again once they have
  addEventListener('load', () => toNewest(false), { once: true });
}).catch(() => trouble("can't reach eva"));
setInterval(poll, POLL_MS);
setInterval(() => drawStatus(), 30000);
requestAnimationFrame(loop);
