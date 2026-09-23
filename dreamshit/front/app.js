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
const SLOW_MS = 300000;      // the fallback poll, used only while the events have never connected
const RETRY_MS = 5000;       // how long before we open the event stream again after a refusal

const rooms = new Map();     // room -> row state; a poll never renders a passage twice
const packs = new Map();     // dream -> its pack (its rows, and the telling cut across them)
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
const GHOST = params.get('ghost') !== '0';
// the last line of the seed that has words in it. a long one (a seed is often one paragraph
// on one line) keeps only its tail — the words right before the dream begins — cut at a word.
function ghostLine(seed) {
  const lines = String(seed || '').split('\n').map(l => l.trim()).filter(Boolean);
  if (!lines.length) return '';
  const last = lines[lines.length - 1];
  if (last.length <= 120) return last;
  const tail = last.slice(-120);
  const cut = tail.indexOf(' ');
  // no '…' in front: the fade on the opening words already says it was cut, and a faded-out
  // ellipsis only left a gap that read as an indent
  return cut >= 0 ? tail.slice(cut + 1) : tail;
}

function buildRow(p) {
  const row = document.createElement('section'); row.className = 'row';
  // the first cell holds this passage's part of the telling — the trickle is cut at its seams
  // and each part sits beside its own scene (drawPack). an empty one keeps the grid standing.
  const slot = document.createElement('div'); slot.className = 'slot';
  const trickle = document.createElement('div'); trickle.className = 'trickle';
  slot.appendChild(trickle);
  const text = document.createElement('div'); text.className = 'text';
  const body = document.createElement('div'); body.className = 'body';
  drawBody(body, p);
  // the name first — it's the first thing read and the thing a dream is chosen by (eva's order)
  const head = titleLine(p.name, p.verse);
  if (head) text.append(head);
  // quiet words above the passage: seed and pic. the seed (the found text the dream grew from)
  // opens in a floating box over it (bekh: without the seed the page is right); pic opens the
  // painting full screen, and only shows once the painting has arrived (plates land late)
  const btns = document.createElement('div'); btns.className = 'btns';
  if (p.seed && String(p.seed).trim()) {
    const btn = document.createElement('button'); btn.textContent = 'seed';
    const box = document.createElement('div'); box.className = 'seedbox'; box.hidden = true;
    box.textContent = String(p.seed).trim();
    btn.onclick = e => { e.stopPropagation(); const open = box.hidden; closeSeeds(); box.hidden = !open; };
    box.onclick = e => e.stopPropagation();
    btns.append(btn); text.append(btns, box);
  } else text.append(btns);
  const pic = document.createElement('button'); pic.textContent = 'pic'; pic.hidden = true;
  btns.append(pic);
  // the seed's last line, ghostly, right above the passage (bekh, 2026-09-23): the dream
  // surfaces out of the last thing the found text said, and the whole seed stays behind its
  // button. ?ghost=0 takes it away.
  const g = ghostLine(p.seed);
  if (g && GHOST) {
    // only the opening words surface out of nothing — the fade is theirs, not the paragraph's,
    // or a wrapped second line fades at its left edge too
    const gh = document.createElement('p'); gh.className = 'ghost';
    const m = g.match(/^(\S+\s+\S+\s+\S+)(\s[\s\S]*)?$/);
    if (m) { const lead = document.createElement('span'); lead.className = 'lead'; lead.textContent = m[1];
             gh.append(lead, m[2] || ''); }
    else gh.textContent = g;
    text.append(gh);
  }
  const w = document.createElement('span'); w.className = 'when'; w.textContent = when(p.ts);
  text.append(body, w);
  const reading = document.createElement('div'); reading.className = 'reading';
  row.append(slot, text, reading);
  const r = { row, slot, trickle, reading, pic, plateUrl: null, step: 0, target: 0 };
  rowSizes.observe(text); rowSizes.observe(reading);
  pic.onclick = e => { e.stopPropagation(); openPlate(r); };
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
  r.pic.hidden = false;
}

// ---- the analyst's ribbon ------------------------------------------------------------------
// every ten dreams the analyst (eva/stream/analyst.py) rewrites his portrait of the dreamer, and
// the page it was written right after carries it as `portrait`. After that dream's PACK — not
// its row — a black ribbon: his face, his remark. After the pack because the stretched telling
// hangs absolutely from a pack's first row down to its last: a ribbon between two rows would
// sit right on the drip's column and cover words of it. So a portrait written after scene 2 is
// shown where the story ends; the order it keeps is the stories', which is the page's order.
// Like a plate it attaches late, in place: the event names the room, the refetch brings
// `portrait` on it, sync() lands here. The face is the front's own file, never the api's.
const FACE = 'analyst.jpg';
const firstSentence = t => {
  const s = String(t || '').trim(), m = /^[\s\S]*?[.!?…]["'”’)\]]*(?=\s|$)/.exec(s);
  const one = m ? m[0] : s;
  return one.length > 260 ? one.slice(0, 260).replace(/\s+\S*$/, '') + '…' : one;
};
function ribbonsOf(pack) {
  // one holder per pack, right after it — so rows appended to the pack later stay above it, and
  // the next pack, appended to the feed, lands below it
  if (!pack.ribbons) { pack.ribbons = document.createElement('div'); pack.ribbons.className = 'ribbons'; pack.el.after(pack.ribbons); }
  return pack.ribbons;
}
function setPortrait(r, v) {
  const key = v && v.id ? v.id + '@' + v.ts : '';
  if (r.portraitKey === key) return;
  r.portraitKey = key;
  if (r.ribbon) { r.ribbon.remove(); r.ribbon = null; }
  if (!key || !r.pack) return;
  const rb = document.createElement('div'); rb.className = 'ribbon';
  rb.tabIndex = 0; rb.setAttribute('role', 'button'); rb.dataset.room = r.room;
  rb.title = `the analyst, after ${v.dreams} dreams`;
  const face = document.createElement('div'); face.className = 'face';
  const img = new Image(); img.alt = ''; img.decoding = 'async'; img.src = FACE; face.append(img);
  const say = document.createElement('p'); say.className = 'say';
  // the three portraits written before the remark existed have no line: the first sentence of
  // the portrait stands in, dimmer, so it doesn't pass for something he said out loud
  const line = String(v.line || '').trim();
  say.textContent = line || firstSentence(v.text);
  if (!line) say.classList.add('quiet');
  rb.append(face, say);
  ribbonSizes.observe(rb);   // fitted once it has a size, and again whenever the band's size moves
  const open = e => { e.stopPropagation(); openManuscript(v); };
  rb.onclick = open;
  rb.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(e); } };
  // two portraits in one pack (possible, not yet seen) keep the rooms' order
  const box = ribbonsOf(r.pack);
  box.insertBefore(rb, [...box.children].find(c => c.dataset.room > r.room) || null);
  r.ribbon = rb;
}

// HEIGHT MEANS HEIGHT (bekh, 2026-09-23): the band is --rh tall whatever he says. The remark
// starts at its size (18, 15 on a phone — the stylesheet's) and steps down a pixel at a time to
// 11 until it fits; if it still doesn't, it is clipped on its last whole line (.clip), so it
// never spills onto the next row. Measured, not guessed: scrollHeight is the text's full height
// even while the box hides the rest. Runs when a ribbon lands, when its size moves (the height
// slider, a resize — the observer) and on refit() (a font change).
const RFS_FLOOR = 11;
function fitRibbon(rb) {
  const say = rb.querySelector('.say'); if (!say) return;
  say.classList.remove('clip'); say.style.removeProperty('--rfs'); say.style.removeProperty('--rclip');
  const room = rb.clientHeight; if (!room) return;
  const base = Math.round(parseFloat(getComputedStyle(say).fontSize)) || 18;
  for (let fs = base; fs >= RFS_FLOOR; fs--) {
    say.style.setProperty('--rfs', fs + 'px');
    if (say.scrollHeight <= room + 1) return;
  }
  const cs = getComputedStyle(say), pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  const lh = RFS_FLOOR * 1.45, n = Math.max(1, Math.floor((room - pad) / lh));
  say.style.setProperty('--rlines', n);
  say.style.setProperty('--rclip', Math.ceil(n * lh) + 'px');   // no padding in .clip (style.css)
  say.classList.add('clip');
}
const fitRibbons = () => { for (const rb of document.querySelectorAll('.ribbon')) fitRibbon(rb); };
const ribbonSizes = new ResizeObserver(es => { for (const e of es) fitRibbon(e.target); });

// the manuscript: the whole portrait of one version, and ‹ › through every version, which are
// fetched when it opens (newest first, as the api gives them). Until they arrive — or if they
// never do — it is the one version the page already holds, with nowhere to step.
const MS = { list: [], i: 0, open: false };
const msEl = () => $('#manuscript');
function drawManuscript() {
  const v = MS.list[MS.i], m = msEl();
  m.querySelector('.after').textContent = `the analyst · after ${v.dreams} dreams`;
  m.querySelector('.date').textContent = when(v.ts);
  m.querySelector('.remark').textContent = String(v.line || '').trim();
  m.querySelector('.words').textContent = String(v.text || '').trim();
  const n = MS.list.length;
  m.querySelector('.pos').textContent = n > 1 ? `${n - MS.i} / ${n}` : '';
  m.querySelector('.prev').disabled = MS.i >= n - 1;      // ‹ earlier = further down the list
  m.querySelector('.next').disabled = MS.i <= 0;
  m.scrollTop = 0;
}
function openManuscript(v) {
  MS.list = [v]; MS.i = 0; MS.open = true;
  drawManuscript(); msEl().hidden = false;
  fetch('/api/stream/portraits', { cache: 'no-store' }).then(r => { if (!r.ok) throw r.status; return r.json(); }).then(d => {
    const L = d.portraits || [], j = L.findIndex(x => x.id === v.id);
    // still on the one it opened with? then take the list; a closed or reopened sheet ignores it
    if (!MS.open || MS.list.length !== 1 || MS.list[0] !== v || j < 0) return;
    MS.list = L; MS.i = j;
    const top = msEl().scrollTop; drawManuscript(); msEl().scrollTop = top;
  }).catch(() => {});
}
function stepManuscript(d) {
  const i = MS.i + d;
  if (!MS.open || i < 0 || i >= MS.list.length) return;
  MS.i = i; drawManuscript();
}
function closeManuscript() { MS.open = false; msEl().hidden = true; }
// ?portrait=<id> opens that version's manuscript over the page — a link to one portrait, and the
// way a headless screenshot gets the sheet open without a click. Not remembered.
if (params.get('portrait')) fetch('/api/stream/portrait?id=' + encodeURIComponent(params.get('portrait')), { cache: 'no-store' })
  .then(r => { if (!r.ok) throw r.status; return r.json(); }).then(v => openManuscript(v.portrait || v)).catch(() => {});
msEl().querySelector('.x').onclick = closeManuscript;
msEl().querySelector('.prev').onclick = () => stepManuscript(1);
msEl().querySelector('.next').onclick = () => stepManuscript(-1);
// a click outside the sheet closes it, as the lightbox does; one on the sheet doesn't
msEl().addEventListener('click', e => { if (!e.target.closest('.sheet')) closeManuscript(); });
// while it is open it owns the keyboard: esc, ← →, and nothing reaches the page's own keys
// (1–7, f, t, , . would otherwise restyle the feed behind it). Capture, so this runs first.
addEventListener('keydown', e => {
  if (!MS.open) return;
  if (e.key === 'Escape') closeManuscript();
  else if (e.key === 'ArrowLeft') { e.preventDefault(); stepManuscript(1); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); stepManuscript(-1); }
  // anything else (the scroll keys included) keeps its browser default but never reaches the page
  e.stopImmediatePropagation();
}, true);

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
// one part of the telling, in a passage's own left cell: the dream's header (chapter · title)
// above the first one, then the words in a `.flow` of their own — the header keeps its normal
// width while stretch mode narrows the words. re-rendered only when something changed, so a
// refetch doesn't repaint the column under the reader.
function setTrickle(el, story, text, head) {
  const title = head ? (story && story.title || '') : '';
  const ch = head && story && story.chapter ? String(story.chapter) : '';
  if (el.dataset.text === text && el.dataset.title === title && el.dataset.ch === ch) return;
  el.dataset.text = text; el.dataset.title = title; el.dataset.ch = ch;
  el.textContent = '';
  const h = head ? titleLine(story && story.title, ch) : null;
  if (h) el.appendChild(h);
  const flow = document.createElement('div'); flow.className = 'flow';
  flow.textContent = text;
  el.appendChild(flow);
}
const flowOf = el => el.querySelector('.flow');

// the telling is ONE continuous narrative with a `|` where each later scene comes in (bekh,
// 2026-09-22 — eva/stream/remembering.py). the page cuts it there and puts part n beside
// passage n, so the part that belongs to a dream is always on its left. `parts` comes from the
// api; we split `text` ourselves by the same rule when it doesn't (an older mirror).
const partsOf = story => Array.isArray(story.parts) && story.parts.length
  ? story.parts : String(story.text || '').split('|').map(s => s.trim());
// a passage's scene number is its verse (`12:3` → 3); without one, its place in the pack
const verseTurn = v => { const m = /:(\d+)\s*$/.exec(v || ''); return m ? +m[1] : 0; };

// parts (the default) — the sleeper can come back with fewer marks than scenes, or more, and
// neither is an error: a missing part leaves that row bare, a surplus one is appended to the
// last passage's, and a telling with no mark at all sits whole beside the first passage — which
// is what the page did before the seams existed, so nothing changes for the older dreams.
// stretch — bekh's fallback (2026-09-22): the telling is stretched to reach the end of its dream.
// `align=even` joins the seams up and drips one thread down the whole pack; `align=dreams` keeps
// them and hangs each part from its own scene, paced to its own row; `align=band` is dreams with
// every part's pace held within a band of the even one, so the drip keeps something of one
// rhythm. A telling with no seam in it has nothing to line up, so it is even whatever is asked.
function drawPack(pack, story) {
  if (!pack.slots.length) return;
  const stretch = TRICKLE === 'stretch' && innerWidth > PHONE;   // one column has no room for it
  const parts = story ? partsOf(story) : [];
  const last = pack.slots.length - 1;
  pack.align = stretch && ALIGN !== 'even' && parts.length > 1 ? ALIGN : 'even';
  pack.el.classList.toggle('stretch', stretch);
  pack.slots.forEach((s, i) => {
    let text;
    if (stretch && pack.align === 'even') text = i ? '' : parts.join(' ');
    else {
      const n = parts.length > 1 ? s.turn : (i === 0 ? 1 : 0);
      text = !n ? '' : i === last ? parts.slice(n - 1).join(' ') : (parts[n - 1] || '');
    }
    setTrickle(s.el, story, text, i === 0);
    if (!stretch) bare(flowOf(s.el));
    // on a phone an empty cell would still cost a row gap above its passage
    s.el.parentNode.classList.toggle('has', !!(text || (i === 0 && story && story.title)));
  });
  if (stretch) refit();
}

// ---- stretch: the thread stretched to reach the end of its dream ---------------------------
// bekh (2026-09-22): "as narrow as it needs to be to reach the end of the existing story" —
// widest beside a single scene, a thread beside four. Nothing in the text says how wide that is,
// so it is measured, not guessed: an offscreen twin of the column is handed a width and asked
// how tall it comes out, ~10 times per dream in a binary search. The twin is offscreen on purpose
// — probing the real column would dirty the page's layout on every step of every search.
//
// THREE DIALS, IN ORDER (bekh, 2026-09-22, once the real tellings showed up): narrow it, then
// one word to a line, then spread the lines. A real telling is 40–60 words, and 50 words one to
// a line reach about one passage — no width on earth gets them to the bottom of a four-scene
// dream. So each dial only moves when the one before it ran out: the width stops at the widest
// word, every space becomes a line break, and last the LEADING opens until the final word lands
// on the bottom — a word, a gap, a word, running the whole height of the dream. The leading and
// the word gap are set on the words alone, never on the trickle, so the header keeps its own.
const PHONE = 820;           // the one-column breakpoint in style.css
const LEAD = 1.7;            // .trickle's own leading in style.css
const LEAD_MIN = .9, LEAD_MAX = 14;   // how close and how far apart the drops ever go
const ONE_WORD = '100vw';    // a word gap wider than any column: every space becomes a break
const probe = (() => {
  const t = document.createElement('div'); t.className = 'trickle probe';
  const f = document.createElement('div'); f.className = 'flow';
  t.appendChild(f); document.body.appendChild(t); return f;
})();
// the floor is the telling's widest word (min-content), never under 4 characters — narrower than
// that and the words hang out of the column and into the passage. Measuring is the whole trick,
// so the probe wears every dial the real thread will wear before it is asked for a height.
function fit(text, avail, full) {
  probe.textContent = text;
  probe.style.lineHeight = ''; probe.style.wordSpacing = '';
  const at = w => { probe.style.width = w + 'px'; return probe.offsetHeight; };
  probe.style.width = '4ch'; const ch4 = probe.offsetWidth;
  probe.style.width = 'min-content'; const floor = Math.min(full, Math.max(ch4, probe.offsetWidth));
  // dial 1: the width
  if (at(full) > avail) return { w: full, lh: LEAD, one: false };   // too long for any width
  if (at(floor) > avail) {                              // it fits somewhere between the two
    let lo = floor, hi = full;                          // lo never fits, hi always does
    for (let i = 0; i < 10 && hi - lo > 2; i++) {
      const mid = (lo + hi) >> 1;
      if (at(mid) <= avail) hi = mid; else lo = mid;
    }
    return { w: hi, lh: LEAD, one: false };
  }
  // dial 2: at the floor short words still pair up ("for the", "jay to"), so force the break
  probe.style.wordSpacing = ONE_WORD;
  // dial 3: the leading that lands the last word on the bottom. It searches downward as well as
  // up: breaking every space can overshoot a room that normal wrapping fell short of, and a
  // telling that has been put one word to a line is not given that back to save a line.
  const tall = lh => { probe.style.lineHeight = lh; return probe.offsetHeight; };
  if (tall(LEAD_MAX) <= avail) return { w: floor, lh: LEAD_MAX, one: true };
  let lo = LEAD_MIN, hi = LEAD_MAX;                     // lo always fits, hi never does
  for (let i = 0; i < 12 && hi - lo > .02; i++) {
    const mid = (lo + hi) / 2;
    if (tall(mid) <= avail) lo = mid; else hi = mid;
  }
  return { w: floor, lh: +lo.toFixed(2), one: true };
}
// align=dreams: one straight column down the whole pack, so the width is the widest word in the
// WHOLE telling, not each part's own — parts would otherwise step in and out as the dream goes.
function widestWord(texts, full) {
  probe.style.lineHeight = ''; probe.style.wordSpacing = '';
  probe.style.width = '4ch';
  let w = probe.offsetWidth;
  for (const t of texts) { probe.textContent = t; probe.style.width = 'min-content'; w = Math.max(w, probe.offsetWidth); }
  return Math.min(full, w);
}
// ...and then each part gets its own leading, so it lands on the bottom of its own scene. Dial 1
// is skipped here: a part is a dozen words and a per-row fit needs them one to a line anyway.
// More words than the tightest leading can hold and the part simply runs on into the next scene.
function fitLead(text, avail, w) {
  probe.textContent = text;
  probe.style.width = w + 'px';
  probe.style.wordSpacing = ONE_WORD;
  const tall = lh => { probe.style.lineHeight = lh; return probe.offsetHeight; };
  if (tall(LEAD_MIN) > avail) return LEAD_MIN;
  if (tall(LEAD_MAX) <= avail) return LEAD_MAX;
  let lo = LEAD_MIN, hi = LEAD_MAX;                     // lo always fits, hi never does
  for (let i = 0; i < 12 && hi - lo > .02; i++) {
    const mid = (lo + hi) / 2;
    if (tall(mid) <= avail) lo = mid; else hi = mid;
  }
  return +lo.toFixed(2);
}
const dress = (flow, w, lh, one) => {
  flow.style.width = w + 'px';
  flow.style.lineHeight = lh === LEAD ? '' : lh;
  flow.style.wordSpacing = one ? ONE_WORD : '';
};
// back to the column's own width, leading and word gap
const bare = flow => { flow.style.width = flow.style.lineHeight = flow.style.wordSpacing = ''; };
// every stretched pack at once, and all the geometry read before any of it is probed: a width
// written to one thread dirties the layout, so interleaving would cost a reflow per dream.
function fitAll() {
  const jobs = [];
  for (const pack of packs.values()) {
    if (!pack.slots.length || !pack.el.classList.contains('stretch')) continue;
    const full = pack.slots[0].el.clientWidth;
    if (full <= 0) continue;
    const foot = pack.slots[pack.slots.length - 1].row.getBoundingClientRect().bottom;
    const lines = [];
    for (const s of pack.slots) {
      const flow = flowOf(s.el);
      if (!flow || !flow.textContent) continue;
      // a part reaches for the end of its own scene; the even thread for the end of the dream
      const top = flow.getBoundingClientRect().top;
      lines.push({ flow, avail: s.row.getBoundingClientRect().bottom - top, top });
    }
    if (lines.length) jobs.push({ align: pack.align, full, lines, deep: foot - lines[0].top, n: pack.slots.length });
  }
  for (const j of jobs) {
    const texts = j.lines.map(l => l.flow.textContent);
    if (j.align === 'even') {
      const { w, lh, one } = fit(texts[0], j.deep, j.full);
      dress(j.lines[0].flow, w, lh, one);
      if (DEBUG) fitLog(j);
      continue;
    }
    const w = widestWord(texts, j.full);
    // band: the rate the whole telling would run at if it ignored the seams, and nothing is
    // allowed further than BAND from it. A part that can't reach its scene's bottom inside the
    // band stops early with air under it; one that can't fit runs on into the next scene.
    const even = j.align === 'band' ? fit(texts.join(' '), j.deep, j.full).lh : 0;
    const lo = even && Math.max(LEAD_MIN, even * (1 - BAND));
    const hi = even && Math.min(LEAD_MAX, even * (1 + BAND));
    for (const l of j.lines) {
      const lh = fitLead(l.flow.textContent, l.avail, w);
      dress(l.flow, w, even ? +Math.min(hi, Math.max(lo, lh)).toFixed(2) : lh, true);
    }
  }
}
// the thread reaches for the bottom of its dream, so anything that moves that bottom refits it.
// Row heights are WATCHED, not announced (2026-09-23): the webfont swapping in, a reading landing
// late, the passage resized — each used to call refit by hand, and the webfont's call hung on
// fonts.ready, which resolves before a runtime-injected stylesheet has even declared newsreader:
// the thread fitted the fallback serif and stopped a whole scene short. Only the passage and the
// reading are watched — a stretched thread is absolute and never sizes its row, so a refit can't
// feed itself. What's left calling refit by hand changes something no row height shows: the
// column widths (resize), the thread's own size (setSides), its text (drawPack).
// ?debug=1: per stretched dream — scenes at fit time, the height it was fitted to, and the height
// it is NOW (re-read every second), plus how often the row observer fired. Read off the page in
// the one browser where the thread stopped short (Helium, 2026-09-23).
const DEBUG = params.get('debug') === '1';
let fits = 0, roFired = 0;
function fitLog(j) { fits++; j.lines[0].flow.dataset.fit = `${j.n}sc ${Math.round(j.deep)}`; }
if (DEBUG) setInterval(() => {
  const out = [];
  for (const pack of packs.values()) {
    const flow = pack.slots.length && flowOf(pack.slots[0].el);
    if (!flow || !flow.dataset.fit) continue;
    const now = pack.slots[pack.slots.length - 1].row.getBoundingClientRect().bottom - flow.getBoundingClientRect().top;
    out.push(`${flow.dataset.fit}/${pack.slots.length}sc ${Math.round(now)}`);
  }
  const l = $('#label'); clearTimeout(l.t); l.style.opacity = 1;
  l.textContent = `fits ${fits} ro ${roFired} @${Math.round(performance.now() / 1000)}s · fitted→now ${out.join(' · ')}`;
}, 1000);
let refitting = 0;
function refit() { clearTimeout(refitting); refitting = setTimeout(() => { fitAll(); fitRibbons(); }, 50); }
const rowSizes = new ResizeObserver(() => { roFired++; refit(); });

// one pack per dream: its passages, and the telling running down their left cells
function newPack(p) {
  const dream = p.story && p.story.dream || null;
  const el = document.createElement('div'); el.className = 'pack';
  $('#feed').appendChild(el);
  const pack = { el, dream, slots: [], story: p.story || null };
  if (dream) packs.set(dream, pack);
  return pack;
}
function render(pages) {
  const fresh = pages.slice().reverse().filter(p => !rooms.has(p.room));
  const touched = new Set();
  for (const p of fresh) {
    const dream = p.story && p.story.dream || null;
    if (!lastPack || !dream || lastPack.dream !== dream) lastPack = newPack(p);
    const r = buildRow(p);
    r.room = p.room; r.pack = lastPack;
    rooms.set(p.room, r);
    lastPack.el.appendChild(r.row);
    setPortrait(r, p.portrait);
    lastPack.slots.push({ turn: verseTurn(p.verse) || lastPack.slots.length + 1, el: r.trickle, row: r.row });
    if (p.story) lastPack.story = p.story;
    touched.add(lastPack);
    lastRowEl = r.row;
  }
  // a new scene means the whole telling was rewritten: every part of that pack is redrawn
  for (const pack of touched) drawPack(pack, pack.story);
  return fresh.length;
}

// update what already exists: late paintings, late readings, the telling rewritten. the story
// is rewritten WHOLE every time a scene lands — part 1 can change when scene 3 arrives — so a
// pack is always redrawn entire, never appended to.
function sync(pages) {
  const seen = new Set();
  for (const p of pages) {
    const r = rooms.get(p.room);
    if (r) { if (p.plate) setPlate(r, p.plate); setReading(r, p.reading); setPortrait(r, p.portrait); }
    const dream = p.story && p.story.dream;
    if (dream && !seen.has(dream) && packs.has(dream)) {
      const pack = packs.get(dream);
      pack.story = p.story;
      drawPack(pack, p.story);
      seen.add(dream);
    }
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
  // [data-look] only: the font and ink buttons live in the same bar and wear `on` for their own
  // reasons (the ink panel being down), which a bare `#flip button` would wipe on every look change
  for (const b of document.querySelectorAll('#flip button[data-look]')) b.classList.toggle('on', b.dataset.look === name);
  try { localStorage.setItem('look', name); } catch {}
  tell(`look: ${name}   [1-${LOOK_NAMES.length}]` + (/--gb/.test(look.css || '') ? `   blur ${GB}px  [ ]` : ''));
}
addEventListener('keydown', e => {
  const i = +e.key - 1; if (LOOK_NAMES[i]) return setLook(LOOK_NAMES[i]);
  if (e.key === '[' || e.key === ']') { GB = Math.max(0, Math.min(20, GB + (e.key === ']' ? 1 : -1))); setLook(LOOK); }
});
addEventListener('resize', () => {
  for (const r of rooms.values()) { r.dither = null; paint(r); }
  // a resize can also cross the phone breakpoint, which decides whether stretch applies at all
  for (const pack of packs.values()) drawPack(pack, pack.story);
  refit();
});

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

// ---- live: pushed, not polled --------------------------------------------------------------
// eva holds a connection open at /api/stream/events and names the rooms that changed, within a
// couple of seconds of a passage, a note, a story, a plate or a name landing on its shelf
// (loom.py's stream_prints). It used to be a 60s poll, which meant a passage could sit written
// and unseen for a minute, and the mac's push to the mini for another one.
//
// What the front does with an event is one refetch of the window it already holds: the pages are
// a contiguous newest-first run, so n=<held> covers anything that changed inside it and anything
// newer than it, and a room older than the window is one we are not showing.
let fetching = false, again = false;
function refetch() {
  if (fetching) { again = true; return; }   // an event mid-flight: the answer may predate it
  fetching = true;
  api('n=' + Math.max(FIRST_LOAD, rooms.size)).then(d => {
    drawStatus(d.status);
    sync(d.pages || []);
    const wasAtNewest = focused && focused.row === lastRow();
    const n = render(d.pages || []);
    console.debug('stream · refetched', (d.pages || []).length, 'pages ·', n, 'new');
    if (!n) return;
    if (wasAtNewest) return toNewest(true);
    waiting += n;
    const f = $('#fresh'); f.textContent = waiting === 1 ? 'new' : waiting + ' new'; f.hidden = false;
  }).catch(() => trouble("can't reach eva")).then(() => {
    fetching = false;
    if (again) { again = false; refetch(); }
  });
}

function onChange(e) {
  let d; try { d = JSON.parse(e.data); } catch { return; }
  drawStatus(d.status);
  // room names are timestamps (stream/<date>/<HHMM>), so a plain string compare is chronological
  const held = [...rooms.keys()];
  const oldest = held.length ? held.reduce((a, b) => b < a ? b : a) : '';
  const inside = (d.rooms || []).filter(r => !oldest || r >= oldest);
  console.debug('stream · change ·', (d.rooms || []).length, 'rooms,', inside.length, 'in the window ·', d.status && d.status.state);
  if (inside.length) refetch();
}

// exactly one connection and at most one retry pending: `live` is the current EventSource and
// every handler ignores an older one, so a retry that fires late can never leave two open.
let everOpened = false, slow = 0, live = null, retry = 0;
function listen() {
  clearTimeout(retry); retry = 0;
  if (live) live.close();
  const es = live = new EventSource('/api/stream/events');
  es.addEventListener('open', () => {
    if (es !== live) return;
    console.debug('stream · events open');
    // a reconnect (a tunnel hiccup, the mirror restarting) means whatever landed while we were
    // away is still missed — so fetch once. the first open follows the initial load, which is
    // that fetch already.
    if (everOpened) refetch();
    everOpened = true;
    clearInterval(slow);            // it has connected: nothing on this page is on a timer now
  });
  es.addEventListener('change', e => { if (es === live) onChange(e); });
  // a dropped connection the browser reconnects by itself (readyState 0). a CLOSED one (2) it
  // never retries — and that is not only "a loom too old to know this route": while the mirror
  // restarts, the proxy in front of it answers 502, and one 502 would otherwise end the live
  // page for good. so we open it again ourselves, and keep doing it until it takes.
  es.addEventListener('error', () => {
    if (es !== live) return;
    const dead = es.readyState === 2;
    console.debug('stream · events ' + (dead ? 'closed, opening again in ' + RETRY_MS / 1000 + 's' : 'dropped, retrying'));
    if (dead && !retry) retry = setTimeout(listen, RETRY_MS);
  });
  return es;
}
$('#fresh').onclick = () => toNewest(true);
for (const b of document.querySelectorAll('#flip button[data-look]')) b.onclick = () => setLook(b.dataset.look);

// the painting full screen: `pic` only — the double-click on a dream was let go (bekh, 2026-09-22)
function openPlate(r) { if (!r.img || !r.img.src) return; $('#lightbox img').src = r.img.src; $('#lightbox').hidden = false; }
const closeBox = () => { $('#lightbox').hidden = true; };
function closeSeeds() { for (const b of document.querySelectorAll('.seedbox')) b.hidden = true; }
addEventListener('click', closeSeeds);
$('#lightbox').addEventListener('click', closeBox);
addEventListener('keydown', e => { if (e.key === 'Escape') { closeBox(); closeSeeds(); inkPanel(false); } });

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
    // the one hand call the observer didn't make redundant after all: without it the telling
    // stopped a scene short again in bekh's browser (2026-09-23), though never in headless. The
    // face is only declared once this sheet is parsed, so load it by hand then, and refit.
    l.onload = () => document.fonts.load(`${f.size}px ${f.family}`).then(refit, refit);
    l.href = `https://fonts.googleapis.com/css2?family=${f.google}&display=swap`; document.head.appendChild(l);
  }
  // , and . nudge the size live, t and T the weight — both remembered per font, found by eye,
  // then baked into fonts.js. weight only moves on a variable face (newsreader); a fixed face
  // snaps to whatever it has
  const size = +(store('fsize:' + name) || f.size);
  const weight = +(store('fw:' + name) || f.weight || 400);
  st.setProperty('--tf', f.family); st.setProperty('--ts', size + 'px'); st.setProperty('--tlead', f.lead);
  st.setProperty('--ttrack', f.track); st.setProperty('--tw', weight);
  document.body.classList.toggle('rough', !!f.rough);
  $('#fontbtn').textContent = 'font: ' + name + (weight !== (f.weight || 400) ? ' ' + weight : '');
  store('font', name);
  tell(`font: ${name}   ${size}px   ${weight}   [f / shift-f · shortlist · , smaller · . bigger · t thinner · T thicker]`);
}
// ?fw=300 sets the weight for the font the page opens with, then it's remembered like the rest
if (params.has('fw')) store('fw:' + FONT, params.get('fw'));
$('#fontbtn').onclick = e => step(e.shiftKey ? -1 : 1);
// the button and f / F walk the shortlist only; a font outside it (via ?font=) steps onto the list
function step(d) { const L = SHORTLIST, i = L.indexOf(FONT); setFont(L[i < 0 ? 0 : (i + d + L.length) % L.length]); }

// ---- the passage's ink --------------------------------------------------------------------
// bekh, 2026-09-22: a palette and a real colour picker for the main font. The presets are in
// fonts.js (INKS); the picker is the browser's own `<input type=color>`, which on a mac is the
// system colour panel — wheel, sliders, eyedropper — so there is no hand-built wheel here.
// ONLY the passage takes the colour (--ink-text, style.css): the labels, names, trickle, reading
// and seed keep the house palette. The reader's two marks blend out of --ink-text as well, so a
// marked run keeps its 30% step away from whatever the words around it are wearing.
// Remembered as an explicit choice only, like the trickle's dials: a default written on every
// load would freeze each browser on whatever the default was the day it first opened the page.
const inkHex = v => {
  if (v === null || v === undefined) return null;
  let s = String(v).trim().toLowerCase();
  if (INKS[s]) return INKS[s];                        // ?ink=pink — a preset by its name
  s = s.replace(/^#/, '');
  if (/^[0-9a-f]{3}$/.test(s)) s = s.replace(/./g, c => c + c);
  return /^[0-9a-f]{6}$/.test(s) ? '#' + s : null;
};
// ?ink=f5c8fe (no #) wins over what's remembered and is then remembered itself; ?ink= empty is
// the reset — it wipes the memory rather than writing the default into it.
let INK = DEFAULT_INK;
if (params.has('ink')) {
  const h = inkHex(params.get('ink'));
  INK = h || DEFAULT_INK;
  store('ink', h && h !== DEFAULT_INK ? h : '');
} else INK = inkHex(store('ink')) || DEFAULT_INK;
const inkName = hex => Object.keys(INKS).find(n => INKS[n] === hex) || hex;
function setInk(hex, quiet) {
  INK = hex;
  document.body.style.setProperty('--ink-text', hex);
  $('#inkpick').value = hex;
  $('#inkbtn .sw').style.background = hex;
  for (const s of document.querySelectorAll('#inkpanel .sw')) s.classList.toggle('on', s.dataset.ink === hex);
  store('ink', hex === DEFAULT_INK ? '' : hex);
  if (!quiet) tell(`ink: ${inkName(hex)}   ${hex}   [c]`);
}
for (const [name, hex] of Object.entries(INKS)) {
  const b = document.createElement('button');
  b.className = 'sw'; b.dataset.ink = hex; b.style.background = hex; b.title = name;
  b.onmouseenter = () => tell(`ink: ${name}   ${hex}`);
  b.onclick = () => setInk(hex);
  $('#inkpanel .swatches').appendChild(b);
}
// live: the passage recolours as the colour panel is dragged, not only when it is let go
$('#inkpick').oninput = e => setInk(e.target.value, true);
$('#inkpick').onchange = e => setInk(e.target.value);
$('#inkreset').onclick = () => setInk(DEFAULT_INK);
// the button opens it and the button closes it (esc too) — bekh's shape. A click anywhere else
// deliberately does NOT close it: reaching for the picker or a swatch is a click on the page.
function inkPanel(on) {
  const p = $('#inkpanel');
  p.hidden = on === undefined ? !p.hidden : !on;
  $('#inkbtn').classList.toggle('on', !p.hidden);
}
$('#inkbtn').onclick = e => { e.stopPropagation(); inkPanel(); };

// ---- the ribbon's tuner ---------------------------------------------------------------------
// bekh, 2026-09-23: "smaller — give me two sliders, the height of his band and the height of the
// space between his band and the dreams; i'll fiddle and give you the numbers." Opened by
// ?tune=ribbon and nothing else (no key, no button: it is a tuning bench, not a dial of the
// page). What he sets is remembered per browser and applies without the param too, like the
// wash; `reset` forgets both and the stylesheet's --rh / --rgap are back. Once he reads the
// numbers out they get baked into style.css's :root and this memory is moot.
// face: where the crop sits down the portrait (object-position y, 0 = his hat, 100 = his chin)
const RT = { h: ['ribbon-h', '--rh', 40, 200, 'px'], gap: ['ribbon-gap', '--rgap', 0, 48, 'px'],
             pos: ['ribbon-pos', '--rpos', 0, 100, '%'] };
const rtDefault = v => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(v)) || 0;
function rtApply(which, v, save) {
  const [key, css, lo, hi, unit] = RT[which];
  if (v === null) { document.body.style.removeProperty(css); try { localStorage.removeItem(key); } catch {} }
  else {
    v = Math.max(lo, Math.min(hi, Math.round(v)));
    document.body.style.setProperty(css, v + unit);
    if (save) store(key, v);
  }
  const now = v === null ? rtDefault(css) : v;
  $('#rt-' + which).value = now;
  $('#rt-' + which).nextElementSibling.textContent = now + unit;
  $('#ribbontune .read').textContent = `height ${$('#rt-h').value} · gap ${$('#rt-gap').value} · face ${$('#rt-pos').value}`;
}
// ?rh=60&rgap=0 is the same as dragging there (and remembered, as a drag is) — how a headless
// shot proves a setting, since it can't move a slider; ?rh= empty resets that one, like ?ink=
const RT_URL = { h: 'rh', gap: 'rgap', pos: 'rpos' };
for (const w of Object.keys(RT)) {
  $('#rt-' + w).oninput = e => rtApply(w, +e.target.value, true);
  const u = params.get(RT_URL[w]);
  if (u === '') rtApply(w, null);
  else if (u !== null && !isNaN(+u)) { rtApply(w, +u, true); continue; }
  const saved = store(RT[w][0]);
  rtApply(w, saved === null || saved === '' || isNaN(+saved) ? null : +saved, false);
}
$('#rt-reset').onclick = () => { for (const w of Object.keys(RT)) rtApply(w, null); };
if (params.get('tune') === 'ribbon') $('#ribbontune').hidden = false;

// how the telling stands beside its dream. **stretch is what the site does** (bekh's verdict,
// 2026-09-22: "unfortunately actually the best stylistically") — one thread paced down the whole
// dream; `parts` (cut at the sleeper's seams, part n beside passage n) stays as a dev option.
// Only an explicit choice is remembered, url or `g`: a default written into localStorage on every
// load freezes each browser on whatever the default was the day it first opened the page, which
// is exactly what happened to `parts` in the hour it was the default — hence the key's new name.
const TRICKLE_MODES = ['parts', 'stretch'];
let TRICKLE = TRICKLE_MODES.includes(params.get('trickle')) ? params.get('trickle')
  : TRICKLE_MODES.includes(store('drip')) ? store('drip') : 'stretch';
if (params.has('trickle')) store('drip', TRICKLE);
// stretch's own sub-knob: does the drip run evenly down the whole dream, or does each part of
// the telling line up with the scene it belongs to? No key — it is an experiment, not a dial —
// and NOT REMEMBERED: url only, gone on the next plain load. It used to be stored like the
// dials, and one `?align=dreams` opened in Helium for a comparison (2026-09-22) left that
// browser on the dreams drip for a day, which showed as the thread stopping a scene short of
// its dream in that one browser and nowhere else (docs/front.md, the precedent).
const ALIGNS = ['even', 'dreams', 'band'];
const ALIGN = ALIGNS.includes(params.get('align')) ? params.get('align') : 'even';
// how far from the even drip's pace a part may go in align=band. 0 would be the even pace held
// everywhere (and most parts ending early); 1 lets a part run at twice or at nothing.
// (0 is a real setting — the even pace held everywhere — so a MISSING value has to be told from
// a zero one, which `+null` is not: it is 0, and the band silently collapsed to nothing.)
const BAND = (() => {
  const raw = params.get('band');
  const v = raw === null || raw === '' ? NaN : +raw;
  return v >= 0 && v <= 5 ? v : .4;
})();
// the stale memory itself, wiped once in every browser that carries it
try { localStorage.removeItem('align'); localStorage.removeItem('band'); } catch {}
// the size of the two SIDE VOICES, found by eye like the passage's: `;` smaller, `'` bigger.
// One dial moves both (bekh, 2026-09-22): the trickle sits at --tsize, the reading one pixel
// above it (style.css), because moving one alone throws the pair off balance. The headers keep
// the size css gives them. Every step re-measures — the thread's column is as wide as its widest
// word, so the type decides both the width and how many lines there are to pace.
let TSIZE = (() => {
  const raw = params.has('tsize') ? params.get('tsize') : store('tsize');
  const v = raw === null || raw === '' ? NaN : +raw;
  return v >= 10 && v <= 20 ? v : 12;
})();
if (params.has('tsize')) store('tsize', TSIZE);
function setSides(v) {
  TSIZE = Math.max(10, Math.min(20, v));
  document.body.style.setProperty('--tsize', TSIZE + 'px');
  refit();   // the thread's own size; the reading growing with it is the observer's
  tell(`sides ${TSIZE}px   [; smaller · ' bigger]`);
}
function setTrickleMode(m) {
  TRICKLE = m; store('drip', m);
  for (const pack of packs.values()) drawPack(pack, pack.story);
  tell(`trickle: ${m}   [g]`);
}

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
  else if (e.key === ',' || e.key === '.') {
    const cur = +(store('fsize:' + FONT) || FONTS[FONT].size);
    store('fsize:' + FONT, Math.max(12, Math.min(30, cur + (e.key === '.' ? .5 : -.5))));
    setFont(FONT);
  }
  else if (e.key === 't' || e.key === 'T') {
    const cur = +(store('fw:' + FONT) || FONTS[FONT].weight || 400);
    store('fw:' + FONT, Math.max(200, Math.min(800, cur + (e.key === 'T' ? 50 : -50))));
    setFont(FONT);
  }
  else if (e.key === ';' || e.key === "'") { setSides(TSIZE + (e.key === "'" ? .5 : -.5)); store('tsize', TSIZE); }
  else if (e.key === 'g') setTrickleMode(TRICKLE === 'stretch' ? 'parts' : 'stretch');
  else if (e.key === 'c') inkPanel();
  else if ('wW-='.includes(e.key)) { WA = Math.max(0, Math.min(.95, WA + (e.key === 'W' || e.key === '=' ? .04 : -.04))); setWash(); }
});


setLook(LOOK);
setSides(TSIZE);         // before the others, so the label the page opens with is the wash's
setInk(INK, true);       // quiet: the page opening is not a choice made, and it says so in the bar
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
// ?tail / ?only are the screenshot modes: one shot of a fixed set of passages, nothing live.
if (!TAIL && !ONLY) {
  // insurance, and only until the events connect: an old loom or a proxy that eats the stream
  // would otherwise leave the page frozen on what it loaded. the first open clears this.
  slow = setInterval(refetch, SLOW_MS);
  listen();
}
// the age in `dreaming · 4 min ago` is drawn here, off the status the events carry; no network
setInterval(() => drawStatus(), 30000);
requestAnimationFrame(loop);
