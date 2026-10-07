import difflib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import prose

RAW = HERE / "raw"
TEXT = HERE / "text"
STORY = re.compile(r"/scifiction/(originals|classics)/(?:originals|classics)_archive/([^/]+)/([^/?#]*)$", re.I)
ELEMENT = re.compile(r"/scifiction/elements/([a-z]+)\.html$", re.I)
TAIL = re.compile(r"©|\bcopyright\b|first appeared|first published|originally (appeared|published)|reprinted (by|with) permission|"
                  r"used by permission|all rights reserved|^the end\.?$|^end$|scifi\.com|^\(?(to be )?continued|"
                  r"^(back|next|previous) ?(to|page)?\b.{0,30}$|^page \d|^\d( \| \d)+$", re.I)
NOTE = re.compile(r"^\W*(author'?s?'? ?note|editor'?s? note|note:|acknowledge?ments?|with thanks|thanks to|is cited as follows|for more information)", re.I)
YEAR = re.compile(r"\b(1[89]\d\d|20[01]\d)\b")
FIRST = re.compile(r"(first appeared|first published|originally (?:appeared|published))(.{0,200})", re.I | re.S)
YEARS = {}
OVERRIDE = HERE / "years.json"
EXCERPT = re.compile(r"\bexcerpt(ed)?\b|\bfrom the (forthcoming )?novel\b", re.I)


def load_index():
    idx = {}
    files = sorted((HERE / "index").glob("*scifiction_archive.html.html"))
    if not files:
        return idx
    soup = prose.soup_of(prose.decode(files[-1].read_bytes()))
    flat = prose.fix(prose.norm_ws(soup.get_text(" ")))
    anchors = []
    for a in soup.find_all("a"):
        h = a.get("href") or ""
        m = re.search(r"/scifiction/(originals|classics)/(?:originals|classics)_archive/([^/]+)/", h)
        if m:
            anchors.append(((m.group(1).lower(), m.group(2).lower()), prose.fix(prose.norm_ws(a.get_text(" "))), h))
    pos = 0
    for k, title, h in anchors:
        info = {"title": title, "author": "", "posted": "", "index_url": "http://www.scifi.com" + h}
        m = re.compile(re.escape(title) + r"\s+(?:by\s+)?(.+?)(?=\s+\d{1,2}\.\d{1,2}\.\d\d\s|\s*$)").search(flat, pos)
        if m:
            info["author"] = m.group(1).strip()
            dates = re.findall(r"(\d{1,2})\.(\d{1,2})\.(\d\d)\s", flat[max(0, m.start() - 400):m.start()])
            if dates:
                mm, dd, yy = dates[-1]
                info["posted"] = f"20{yy}-{int(mm):02d}-{int(dd):02d}"
            pos = m.start() + len(title)
        idx.setdefault(k, info)
    return idx


def same_title(a, b):
    a, b = prose.key(a), prose.key(b)
    if not a or not b:
        return True
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.8


def page_no(d, name):
    name = name.lower().split("#")[0]
    if not re.search(r"\.html?$", name) or re.search(r"_(bio|biblio)", name):
        return None
    stem = re.sub(r"\.html?$", "", name)
    rest = stem[len(d):] if stem.startswith(d) else re.sub(r"^[a-z_]+", "", stem)
    m = re.fullmatch(r"[._-]?0*(\d{1,2})", rest)
    return int(m.group(1)) if m and int(m.group(1)) > 0 else None


def page_parts(htmltext):
    soup = prose.soup_of(htmltext)
    title = soup.find(class_="storytitle")
    bio = soup.find(class_="storybio")
    t = prose.fix(prose.norm_ws(title.get_text(" "))) if title else ""
    a = prose.fix(prose.norm_ws(bio.get_text(" "))) if bio else ""
    a = re.sub(r"^by\s+", "", a, flags=re.I)
    links = set()
    for x in soup.find_all(["a", "area"]):
        links.add((x.get("href") or "").split("/")[-1].lower())
    whole = prose.norm_ws(soup.get_text(" "))
    bodies = soup.find_all(class_="bodytext")
    paras = []
    for b in bodies:
        if b.find_parent(class_="bodytext"):
            continue
        paras += prose.paragraphs(b, drop_class=re.compile(r"pullquote|arrows|archivebio|storybio|storytitle|announcement"))
    return t, a, links, whole, paras


NOTES_HEAD = re.compile(r"^(annotations?|notes?|footnotes?|endnotes?|glossary)\W*$", re.I)
NUMBERED = re.compile(r"^\[?(\d{1,3})[.\])]\s+\S")
SERIAL = re.compile(r"^\W*(to be )?(continued|concluded)( next week| from last week| in part \w+)?\W*$|^\W*(part \w+ )?(continues|concludes) next week\W*$", re.I)


def drop_annotations(paras):
    n = len(paras)
    i = n
    while i > 0 and (paras[i - 1] == prose.BREAK or NUMBERED.match(paras[i - 1])):
        i -= 1
    run = [p for p in paras[i:] if p != prose.BREAK]
    if len(run) >= 4 and NUMBERED.match(run[0]).group(1) in ("1", "0"):
        if i > 0 and NOTES_HEAD.match(paras[i - 1]):
            i -= 1
        return paras[:i]
    for j in range(n - 1, max(n - 400, -1), -1):
        if NOTES_HEAD.match(paras[j]) and j < n - 1:
            rest = [p for p in paras[j + 1:] if p != prose.BREAK]
            if rest and sum(1 for p in rest if NUMBERED.match(p)) >= 0.8 * len(rest):
                return paras[:j]
    return paras


def strip_tail(paras):
    removed = []
    for i in range(len(paras) - 1, max(len(paras) - 12, 0), -1):
        if prose.END.match(paras[i]) and sum(len(p.split()) for p in paras[i + 1:]) < 250:
            removed = list(reversed(paras[i:]))
            paras = paras[:i]
            break
    while paras:
        p = paras[-1]
        if p == prose.BREAK or (len(p.split()) < 90 and (TAIL.search(p) or prose.LINK in p or NOTE.search(p))):
            removed.append(paras.pop())
            continue
        break
    return paras, removed


def first_year(whole, removed):
    tail = " ".join(reversed(removed)) + " " + whole[-1500:]
    m = FIRST.search(tail)
    if m:
        ys = [int(y) for y in YEAR.findall(m.group(2))]
        if ys:
            return min(ys), "page: first appeared"
    cs = [int(y) for y in YEAR.findall(" ".join(re.findall(r"(?:©|copyright)[^.]{0,80}", tail, re.I)))]
    if cs:
        return min(cs), "page: copyright line"
    return None, ""


def main():
    idx = load_index()
    overrides = json.loads(OVERRIDE.read_text()) if OVERRIDE.exists() else {}
    man = [json.loads(l) for l in open(HERE / "raw.jsonl")]
    groups = defaultdict(dict)
    elements = {}
    for m in man:
        if m["status"] != 200 or not m["file"]:
            continue
        u = m["original"].split("?")[0]
        s = STORY.search(u)
        if s:
            groups[(s.group(1).lower(), s.group(2).lower())][s.group(3).lower()] = m
            continue
        e = ELEMENT.search(u)
        if e:
            elements[e.group(1).lower()] = m
    if TEXT.exists():
        shutil.rmtree(TEXT)
    TEXT.mkdir()
    recs = []
    keys = sorted(set(idx) | set(groups))
    for k in keys:
        kind, d = k
        info = idx.get(k, {})
        rec = {"source": "SCI FICTION (scifi.com)", "kind": "original" if kind == "originals" else "classic",
               "dir": d, "title": info.get("title", ""), "author": info.get("author", ""),
               "posted": info.get("posted", ""), "url": info.get("index_url", ""), "wayback": [],
               "year": None, "year_source": "", "pages": 0, "pages_expected": 0, "words": 0, "file": "",
               "in_index": k in idx, "status": "ok"}
        files = groups.get(k, {})
        numbered = {}
        for name, m in files.items():
            n = page_no(d, name)
            if n:
                numbered[n] = m
        roots = [files[n] for n in ("index.html", "", "index.htm") if n in files]
        chosen = []
        expected = 0
        parsed = {}
        for n, m in sorted(numbered.items()):
            parsed[n] = page_parts(prose.decode((RAW / m["file"]).read_bytes()))
            for l in parsed[n][2]:
                x = page_no(d, l)
                if x:
                    expected = max(expected, x)
        expected = max(expected, max(numbered) if numbered else 0)
        want = info.get("title", "")
        foreign = []
        for n in list(numbered):
            if not same_title(parsed[n][0], want):
                foreign.append(f"{numbered[n]['original']} carries the title {parsed[n][0]!r}")
                del numbered[n]
        good_roots = []
        for m in roots:
            pp = page_parts(prose.decode((RAW / m["file"]).read_bytes()))
            if same_title(pp[0], want):
                good_roots.append(m)
            else:
                foreign.append(f"{m['original']} carries the title {pp[0]!r}")
        roots = good_roots
        rec["foreign_pages"] = foreign
        if numbered and 1 not in numbered:
            for m in roots:
                pp = page_parts(prose.decode((RAW / m["file"]).read_bytes()))
                if pp[4] and sum(len(x.split()) for x in pp[4]) > 300:
                    numbered[1] = m
                    parsed[1] = pp
                    break
        body_pages = [(n, numbered[n], parsed[n]) for n in sorted(numbered) if parsed[n][4]]
        if body_pages:
            chosen = body_pages
        else:
            for m in roots:
                pp = page_parts(prose.decode((RAW / m["file"]).read_bytes()))
                if pp[4] and sum(len(p.split()) for p in pp[4]) > 300:
                    chosen = [(1, m, pp)]
                    expected = 1
                    break
        rec["pages_expected"] = expected
        if not chosen:
            rec["status"] = "missing: no story page captured" if not files else "missing: only the teaser front page was captured"
            if not rec["url"] and files:
                rec["url"] = next(iter(files.values()))["original"]
            recs.append(rec)
            continue
        rec["pages"] = len(chosen)
        rec["wayback"] = [f"{m['served_timestamp']} {m['original']}" for _, m, _ in chosen]
        if not rec["url"]:
            rec["url"] = chosen[0][1]["original"]
        if not rec["title"]:
            rec["title"] = chosen[0][2][0]
        if not rec["author"]:
            rec["author"] = chosen[0][2][1]
        got = {n for n, _, _ in chosen}
        if expected and got != set(range(1, expected + 1)):
            rec["status"] = f"incomplete: pages {sorted(got)} of {expected} captured"
        paras = []
        for _, _, pp in chosen:
            page = drop_annotations([x for x in pp[4] if not SERIAL.match(x)])
            page, _ = strip_tail(page)
            paras += page
        removed = []
        for _, _, pp in chosen[-1:]:
            _, removed = strip_tail(drop_annotations(list(pp[4])))
        while paras and (prose.key(paras[0]) == prose.key(rec["title"]) or re.match(r"^by\s+\S", paras[0]) and len(paras[0].split()) < 8):
            paras.pop(0)
        text = prose.join(paras)
        rec["words"] = len(text.split())
        y, src = first_year(chosen[-1][2][3], removed)
        if f"{kind}/{d}" in overrides:
            y, src = overrides[f"{kind}/{d}"], "set by hand (years.json)"
        if kind == "originals":
            rec["year"] = int(rec["posted"][:4]) if rec["posted"] else int(chosen[0][1]["served_timestamp"][:4])
            rec["year_source"] = "posted on the site"
        else:
            rec["year"], rec["year_source"] = y, src
        head = " ".join(paras[:3]) + " " + " ".join(removed)
        if rec["status"] == "ok":
            if rec["words"] < 150:
                rec["status"] = "missing: page captured but no story text in it"
            elif kind == "classics" and rec["year"] is None:
                rec["status"] = "held: classic with no first-publication year on the page"
            elif kind == "classics" and rec["year"] < 1970:
                rec["status"] = "skipped: pre-1970"
            elif EXCERPT.search(rec["title"]) or EXCERPT.search(" ".join(removed)):
                rec["status"] = "skipped: excerpt"
            elif not prose.english(text):
                rec["status"] = "skipped: not English"
        rec["_text"] = text
        recs.append(rec)

    order = []
    pt = sorted((HERE / "index").glob("*periodictable*")) + [RAW / m["file"] for m in man if m["status"] == 200 and "periodictable.html" in m["original"]]
    for f in pt:
        soup = prose.soup_of(prose.decode(Path(f).read_bytes()))
        for a in soup.find_all(["a", "area"]):
            e = re.search(r"elements/([a-z]+)\.html", a.get("href") or "", re.I)
            if e and e.group(1).lower() not in order:
                order.append(e.group(1).lower())
    for name in order + sorted(set(elements) - set(order)):
        rec = {"source": "SCI FICTION (scifi.com)", "kind": "original", "dir": f"elements/{name}",
               "title": f"Periodic Table of Science Fiction: {name.capitalize()}", "author": "Michael Swanwick",
               "posted": "", "url": f"http://www.scifi.com/scifiction/elements/{name}.html", "wayback": [],
               "year": None, "year_source": "", "pages": 0, "pages_expected": 1, "words": 0, "file": "",
               "in_index": name in order, "status": "ok"}
        m = elements.get(name)
        if not m:
            rec["status"] = "missing: no story page captured"
            recs.append(rec)
            continue
        soup = prose.soup_of(prose.decode((RAW / m["file"]).read_bytes()))
        body = soup.find(class_="bodytext") or soup.find(class_=re.compile("text", re.I)) or soup.body
        paras = prose.paragraphs(body, drop_class=re.compile(r"pullquote|arrows|archivebio|storybio|storytitle|announcement")) if body else []
        paras, removed = strip_tail(paras)
        while paras and len(paras[0].split()) <= 3 and (re.fullmatch(r"[\d.()\[\]]+", paras[0]) or len(paras[0]) <= 3 or prose.key(paras[0]) == name):
            paras.pop(0)
        if paras and len(paras[0].split()) <= 12 and not re.search(r"[.!?,;:\"”]$", paras[0]):
            rec["title"] += " — " + paras.pop(0)
        text = prose.join(paras)
        rec.update(pages=1, wayback=[f"{m['served_timestamp']} {m['original']}"], words=len(text.split()),
                   year=int(m["served_timestamp"][:4]), year_source="first capture")
        if rec["words"] < 40:
            rec["status"] = "missing: page captured but no story text in it"
        rec["_text"] = text
        recs.append(rec)

    used = set()
    for r in recs:
        if r["status"] != "ok":
            continue
        base = prose.slug(r["title"]) if r["title"] else r["dir"].replace("/", "-")
        name = base
        if name in used:
            name = f"{base}-{prose.slug(r['dir'])}"
        used.add(name)
        r["file"] = f"text/{name}.txt"
        (HERE / r["file"]).write_text(r["_text"], encoding="utf-8")
    with open(HERE / "ledger.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
    c = Counter((r["kind"], r["status"].split(":")[0]) for r in recs)
    for k, v in sorted(c.items()):
        print(v, *k)
    print("words ok", sum(r["words"] for r in recs if r["status"] == "ok"))


if __name__ == "__main__":
    main()
