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
let lastDream = null, waiting = 0, status = null;

const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const when = ts => new Date(ts * 1000).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).toLowerCase();
const api = q => fetch('/api/stream?' + q, { cache: 'no-store' }).then(r => { if (!r.ok) throw r.status; return r.json(); });

const grainURL = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), id = x.createImageData(256, 256);
  for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() * 255 | 0; id.data[i] = id.data[i+1] = id.data[i+2] = v; id.data[i+3] = 255; }
  x.putImageData(id, 0, 0); return c.toDataURL();
})();

// ---- rendering -------------------------------------------------------------------------
function buildRow(p) {
  const row = document.createElement('section'); row.className = 'row';
  const trickle = document.createElement('div'); trickle.className = 'trickle';
  const dream = p.story && p.story.dream;
  // the trickle runs once per dream, starting beside its first passage
  if (dream && dream !== lastDream && !trickles.has(dream)) { trickle.textContent = p.story.text; trickles.set(dream, trickle); }
  lastDream = dream;
  const text = document.createElement('div'); text.className = 'text';
  text.innerHTML = String(p.text || '').trim().split(/\n\s*\n/).map(t => `<p>${esc(t).replace(/\n/g, '<br>')}</p>`).join('')
    + `<span class="when">${when(p.ts)}</span>`;
  const reading = document.createElement('div'); reading.className = 'reading';
  row.append(trickle, text, reading);
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
    plate.append(img, cv, grain, sheen, wash); r.row.prepend(plate);
    Object.assign(r, { plate, img, cv });
    img.onload = () => { r.dither = null; paint(r); };
    cv.style.filter = LOOKS[LOOK].css || '';
  }
  r.img.src = url;
}

// pages come newest first; the feed reads down, oldest first
function render(pages) {
  const fresh = pages.slice().reverse().filter(p => !rooms.has(p.room));
  for (const p of fresh) {
    const r = buildRow(p);
    rooms.set(p.room, r);
    $('#feed').appendChild(r.row);
  }
  return fresh.length;
}

// update what already exists: late paintings, late readings, the trickle growing
function sync(pages) {
  const seen = new Set();
  for (const p of pages) {
    const r = rooms.get(p.room);
    if (r) { if (p.plate) setPlate(r, p.plate); setReading(r, p.reading); }
    const dream = p.story && p.story.dream;
    if (dream && !seen.has(dream) && trickles.has(dream)) { trickles.get(dream).textContent = p.story.text; seen.add(dream); }
  }
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
const lastRow = () => $('#feed').lastElementChild;
function toNewest(smooth) {
  const r = lastRow(); if (!r) return;
  scrollTo({ top: r.offsetTop + r.offsetHeight / 2 - innerHeight / 2, behavior: smooth ? 'smooth' : 'auto' });
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
  document.body.className = 'k-' + look.kind + (look.sheen ? ' sheen' : '');
  document.body.style.setProperty('--gb', GB + 'px');
  for (const r of rooms.values()) if (r.plate) { r.cv.style.filter = look.css || ''; r.dither = null; r.step = r.target; paint(r); }
  for (const b of document.querySelectorAll('#flip button')) b.classList.toggle('on', b.dataset.look === name);
  try { localStorage.setItem('look', name); } catch {}
  const l = $('#label');
  l.textContent = `look: ${name}   [1-${LOOK_NAMES.length}]` + (/--gb/.test(look.css || '') ? `   blur ${GB}px  [ ]` : '');
  l.style.opacity = 1; clearTimeout(l.t); l.t = setTimeout(() => l.style.opacity = 0, 1800);
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
for (const b of document.querySelectorAll('#flip button')) b.onclick = () => setLook(b.dataset.look);

setLook(LOOK);
// ?tail=N: only the newest N passages, no scrolling — for headless screenshots, which come out
// blank whenever the page scrolls itself
const TAIL = +params.get('tail') || 0;
api('n=' + (TAIL || FIRST_LOAD)).then(d => {
  render(d.pages || []);
  sync(d.pages || []);
  drawStatus(d.status);
  if (TAIL) { $('#feed').style.padding = '40px 0 0'; return; }
  toNewest(false);
  // fonts landing late reflow the page; stand on the newest passage again once they have
  addEventListener('load', () => toNewest(false), { once: true });
}).catch(() => trouble("can't reach eva"));
setInterval(poll, POLL_MS);
setInterval(() => drawStatus(), 30000);
requestAnimationFrame(loop);
