"""One reading page for the sheets site, with stars.

    python3 sheet_build.py entries.json out.html

entries.json: {slug, title, intro, preface: [{heading, items: [{id, why}]}], seed,
entries: [{id, vector, dose, about, quote, text, words}]}. The output is one self-contained html
file: every verbatim text is inside it (folded, not fetched), so it reads the same from the mini
or from disk. Stars go to the sheets server (/api/stars, /api/star, keyed by slug) so the phone
and the desk see the same marks; opened from disk the fetch fails and they fall back to
localStorage — change the slug and a page loses its stars, since the slug is the key."""
import html, json, sys

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--dim:#6b6860;--line:#e2ded5;--card:#fff;--acc:#8a3fa0;--star:#c98a00}
@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#e8e6e1;--dim:#9a968d;--line:#2c2a27;--card:#1a1918;--acc:#f5c8fe;--star:#ffd35c}}
body{background:var(--bg);color:var(--fg);font:18px/1.55 Georgia,'Iowan Old Style',serif;margin:0 auto;max-width:720px;padding:16px 16px 72px}
h1{font-size:1.6em;line-height:1.2;margin:.4em 0}h2{font-size:1.2em;color:var(--acc);margin:2em 0 .6em;border-bottom:1px solid var(--line);padding-bottom:.2em}
h3{font-size:1em;margin:1.4em 0 .4em;font-family:system-ui,sans-serif;text-transform:lowercase;color:var(--dim)}
a{color:var(--acc)}blockquote{margin:.8em 0;padding:.1em 0 .1em 14px;border-left:3px solid var(--line);font-style:italic}
.seed{font-style:normal;white-space:pre-wrap}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:12px 0}
.meta{font:14px system-ui,sans-serif;color:var(--dim);display:flex;align-items:center;gap:10px}
.meta .sp{flex:1}button{font:inherit;background:none;border:0;color:inherit;cursor:pointer;padding:2px 6px}
.star{font-size:22px;line-height:1;color:var(--star)}summary{cursor:pointer;list-style:none;font:14px system-ui,sans-serif;color:var(--dim)}
summary::-webkit-details-marker{display:none}summary:before{content:'▸ '}details[open] summary:before{content:'▾ '}
.text{white-space:pre-wrap;margin-top:.6em}.pref li{margin:.4em 0}.top{font:12px system-ui,sans-serif;color:var(--dim);display:flex;gap:8px;align-items:center;justify-content:flex-end;opacity:.7}
.top button{border:1px solid var(--line);border-radius:5px;padding:1px 6px}
"""

JS = """
const SLUG=%s, KEY='sheet-stars:'+SLUG;let stars=new Set(),remote=true;
function paint(){document.querySelectorAll('.star').forEach(b=>{const on=stars.has(b.dataset.id);b.textContent=on?'★':'☆';b.setAttribute('aria-pressed',on)});
 document.getElementById('n').textContent=stars.size?stars.size+' starred':''}
function local(){try{stars=new Set(JSON.parse(localStorage.getItem(KEY)||'[]'))}catch(e){}}
function keep(){try{localStorage.setItem(KEY,JSON.stringify([...stars]))}catch(e){}}
fetch('/api/stars?page='+encodeURIComponent(SLUG)).then(r=>{if(!r.ok)throw 0;return r.json()})
 .then(j=>{stars=new Set(j.stars)}).catch(()=>{remote=false;local()}).finally(paint);
document.addEventListener('click',e=>{const b=e.target.closest('.star');if(!b)return;const id=b.dataset.id,on=!stars.has(id);
 on?stars.add(id):stars.delete(id);paint();keep();if(!remote)return;
 fetch('/api/star',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({page:SLUG,id,on})})
  .then(r=>r.json()).then(j=>{stars=new Set(j.stars);paint()}).catch(()=>{remote=false})});
document.getElementById('copy').onclick=()=>{const t=[...stars].join('\\n');
 (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).catch(()=>prompt('starred',t))
 .then(()=>{const b=document.getElementById('copy');b.textContent='copied';setTimeout(()=>b.textContent='copy starred',1200)})};
"""

E = html.escape


def para(s):
    """Plain text with blank-line paragraphs; enough for an intro, not a markdown engine."""
    return "".join(f"<p>{E(p).replace(chr(10), '<br>')}</p>" for p in (s or "").split("\n\n") if p.strip())


def build(d):
    slug = d["slug"]
    groups = {}
    for e in d.get("entries", []):
        groups.setdefault(e["vector"], []).append(e)
    anchor = {v: "v-" + "".join(c if c.isalnum() else "-" for c in v) for v in groups}
    out = [f"<!doctype html><html lang=en><head><meta charset=utf-8>"
           f"<meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>{E(d['title'])}</title><style>{CSS}</style></head><body>",
           f"<h1>{E(d['title'])}</h1>",
           "<div class=top><button id=copy>copy starred</button><span id=n></span></div>",
           para(d.get("intro"))]
    for sec in d.get("preface", []):
        out.append(f"<h3>{E(sec['heading'])}</h3><ul class=pref>")
        for it in sec.get("items", []):
            v = it["id"]
            link = f"<a href='#{anchor[v]}'>{E(v)}</a>" if v in anchor else E(v)
            out.append(f"<li>{link} — {E(it.get('why', ''))}</li>")
        out.append("</ul>")
    if d.get("seed"):
        out.append(f"<h3>the seed</h3><blockquote class=seed>{E(d['seed'])}</blockquote>")
    for v, es in groups.items():
        out.append(f"<h2 id='{anchor[v]}'>{E(v)}</h2>")
        for e in es:
            out.append(
                f"<div class=card><div class=meta><span>dose {E(str(e.get('dose', '')))} · "
                f"{E(str(e.get('words', '')))} words</span><span class=sp></span>"
                f"<button class=star data-id='{E(e['id'])}' title='star'>☆</button></div>"
                + para(e.get("about"))
                + (f"<blockquote>{E(e['quote'])}</blockquote>" if e.get("quote") else "")
                + f"<details><summary>the page</summary><div class=text>{E(e.get('text', ''))}</div></details></div>")
    out.append(f"<script>{JS % json.dumps(slug)}</script></body></html>")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python3 sheet_build.py entries.json out.html")
    with open(sys.argv[1]) as f:
        page = build(json.load(f))
    with open(sys.argv[2], "w") as f:
        f.write(page)
