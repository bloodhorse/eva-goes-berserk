import html
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
TEXT = ROOT / "text"
BASE = "https://fictionliberationfront.net/"
AUTHOR = "Lewis Shiner"
BREAK = "* * *"
MANIFESTO = ("fictionliberationfront.net/manifesto.html: \"Everything on the FLF website, regardless of original "
             "copyright, carries a Creative Commons license.\"")
ORNAMENT = re.compile(r"^[\s*#~•·⁂◊○●]+$")
BREAKISH = re.compile(r"^[\s*#~§•·⁂◊○●×+=_\-–—.:|/\\]{1,40}$")
C1 = {i: bytes([i]).decode("cp1252", "replace") for i in range(0x80, 0xA0)}
END_PAGE = re.compile(r"^(author[’']?snote|glossary|acknowledge?ments?|abouttheauthor|afterword)")
DUP_OF = {"americans": "cities", "rebels": "cities", "cabracan": "cities", "dcities": "cities",
          "stoked": "slam", "sailor": "frontera"}


WORDS = set(w.strip() for w in open("/usr/share/dict/words", encoding="utf-8", errors="ignore") if w[:1].islower())
NAMES = set(w.strip().lower() for w in open("/usr/share/dict/words", encoding="utf-8", errors="ignore") if w[:1].isupper())
SMALLCAP_WORDS = {"aids"}


def ws(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fix_chars(s):
    s = s.translate(C1).replace("­", "")
    for a, b in (("ﬁ", "fi"), ("ﬂ", "fl"), ("ﬀ", "ff"), ("ﬃ", "ffi"), ("ﬄ", "ffl")):
        s = s.replace(a, b)
    return s


def story(path):
    soup = BeautifulSoup(path.read_bytes().decode("cp1252", "replace"), "lxml")
    lic = ""
    for a in soup.find_all("a", rel=True):
        if "license" in a.get("rel", []) and "creativecommons.org" in (a.get("href") or ""):
            lic = a["href"]
            break
    box = soup.find(id="libcontent") or soup.body
    for t in box.find_all(["script", "style", "img", "table"]):
        t.decompose()
    h1 = box.find("h1")
    title = ws(fix_chars(h1.get_text(" "))) if h1 else ""
    credit = ""
    paras = []

    def lines_of(node):
        out, buf = [], []
        for d in node.descendants:
            if isinstance(d, NavigableString):
                buf.append(str(d))
            elif isinstance(d, Tag) and d.name == "br":
                out.append(ws(fix_chars("".join(buf))))
                buf = []
        out.append(ws(fix_chars("".join(buf))))
        return [x for x in out if x]

    for el in box.find_all(["p", "h2", "h3", "h5", "h6", "blockquote", "pre", "li"]):
        if el.name != "blockquote" and el.find_parent("blockquote") is not None and el.name != "p":
            continue
        if el.name == "blockquote" and el.find("p") is not None:
            continue
        cls = el.get("class") or []
        text = ws(fix_chars(el.get_text(" ")))
        if "bodysm" in cls:
            credit = text
            continue
        if el.get("align") == "center" and re.search(r"\bTop\b.*\bHome\b", text):
            continue
        if not text:
            continue
        if el.name in ("h2", "h3", "h5", "h6"):
            paras.append(BREAK if BREAKISH.match(text) else text)
            continue
        cap = el.find("span", class_="dropcap")
        if cap is not None:
            c = ws(cap.get_text())
            if re.fullmatch(r"[\divxIVX]{1,4}\.?", c) and not re.fullmatch(r"[IVX]", c):
                cap.extract()
                paras.append(c)
            elif c == "I" and str(cap.next_sibling or "").startswith((" ", "\n", "\t")):
                pass
            else:
                nxt = cap.next_sibling
                if isinstance(nxt, NavigableString):
                    nxt.replace_with(str(nxt).lstrip())
                cap.unwrap()
                el.smooth()
        for ln in lines_of(el):
            ln = re.sub(r"\s+([,.;:!?])", r"\1", ln)
            paras.append(BREAK if BREAKISH.match(ln) else ln)
    out = []
    for p in paras:
        if p == BREAK and (not out or out[-1] == BREAK):
            continue
        out.append(p)
    while out and out[-1] == BREAK:
        out.pop()
    m = re.search(r"(?:©|\(c\))\s*(\d{4})", credit)
    return {"title": title, "text": "\n\n".join(out), "licence": lic, "credit": credit,
            "year": int(m.group(1)) if m else None}


TWO = set("of to in it is be as at so we he by or on do if me my up an go no us am".split())


def known(w, vocab):
    w = re.sub(r"^[^\w]+|[^\w]+$", "", w).lower().replace("’", "'")
    if not w:
        return True
    if len(w) <= 2:
        return w in TWO or w in ("a", "i")
    return w in vocab or w in WORDS or (w.endswith("'s") and (w[:-2] in vocab or w[:-2] in WORDS))


def regroup(frags, vocab, prefix="", acronyms=False):
    n = len(frags)
    best = [(0.0, [])] + [None] * n
    for j in range(1, n + 1):
        for i in range(j):
            piece = "".join(frags[i:j])
            whole = (prefix if i == 0 else "") + piece
            core = re.sub(r"[^\w]", "", piece)
            if j - i == 1:
                cost, tag = (1.0 if known(whole, vocab) else 2.0), 1
            elif known(whole, vocab):
                cost, tag = 1.0, 2
            elif acronyms and len(core) <= 6 and core.isalpha() and not any(
                    (len(f) >= 3 and known(f, vocab)) or re.sub(r"[^\w]", "", f).lower() in TWO for f in frags[i:j]):
                cost, tag = 1.5, 3
            else:
                continue
            cand = (best[i][0] + cost, best[i][1] + [(piece, tag)])
            if best[j] is None or cand[0] < best[j][0]:
                best[j] = cand
    return best[n][1]


def segment(text, vocab):
    letters = "".join(text.split())
    n = len(letters)
    best = [(0.0, [])] + [None] * n
    for j in range(1, n + 1):
        for i in range(max(0, j - 20), j):
            if best[i] is None:
                continue
            w = letters[i:j]
            core = re.sub(r"[^\w]", "", w).lower()
            if core in ("a", "i", "the", "and") or core in TWO:
                cost = 0.9
            elif len(core) > 2 and core in WORDS:
                cost = 1.0
            elif len(core) > 2 and core in vocab:
                cost = 1.2
            elif len(core) > 2 and core in NAMES:
                cost = 1.4
            else:
                cost = 3.0 + len(core)
            cand = (best[i][0] + cost, best[i][1] + [w])
            if best[j] is None or cand[0] < best[j][0]:
                best[j] = cand
    return " ".join(best[n][1])


def pdf_lines(path):
    xml = subprocess.run(["pdftotext", "-bbox-layout", str(path), "-"], capture_output=True, check=True).stdout
    xml = xml.decode("utf-8", "replace")
    raw_pages = []
    vocab = Counter()
    for pg in re.findall(r"<page [^>]*>(.*?)</page>", xml, re.S):
        lines = []
        for ln in re.findall(r'<line xMin="(.*?)" yMin="(.*?)" xMax="(.*?)" yMax="(.*?)">(.*?)</line>', pg, re.S):
            words = [(float(a), float(b), fix_chars(html.unescape(w))) for a, b, w in
                     re.findall(r'<word xMin="(.*?)" yMin="[^"]*" xMax="(.*?)" yMax="[^"]*">(.*?)</word>', ln[4])]
            runs = []
            for i, (x0, x1, w) in enumerate(words):
                if runs and x0 - words[i - 1][1] < 2.0 and re.search(r"[A-Za-z’']$", runs[-1][-1]) and re.match(r"[a-z’']", w):
                    runs[-1].append(w)
                else:
                    runs.append([w])
            for r in runs:
                if len(r) == 1:
                    vocab[re.sub(r"^[^\w]+|[^\w]+$", "", r[0]).lower().replace("’", "'")] += 1
            if runs:
                lines.append({"x0": float(ln[0]), "y0": float(ln[1]), "x1": float(ln[2]), "y1": float(ln[3]), "runs": runs})
        raw_pages.append(lines)
    vocab = {w for w, c in vocab.items() if c >= 2 and len(w) >= 3}
    for lines in raw_pages:
        prefix = ""
        for l in lines:
            toks, frag = [], []
            for k, r in enumerate(l["runs"]):
                if len(r) == 1:
                    toks.append(r[0])
                    frag.append(1)
                    continue
                for piece, tag in regroup(r, vocab, prefix if k == 0 else "", True):
                    toks.append(piece)
                    frag.append(tag)
            l["toks"], l["frag"] = toks, frag
            l["caps_open"] = sum(1 for r in l["runs"][:5] if len(r) > 1) >= 2
            text = "".join(toks)
            prefix = text if (l["y1"] - l["y0"] > 25 and len(text) <= 3) else ""
    return raw_pages


def novel(path, report):
    pages = pdf_lines(path)
    start = None
    seen_c = False
    for i, lines in enumerate(pages):
        if any(l["toks"][0].startswith("©") for l in lines):
            seen_c = True
            continue
        if seen_c and len(lines) >= 20 and any(l["y1"] - l["y0"] > 25 for l in lines):
            start = i
            break
    def norm(l):
        return re.sub(r"[^a-z0-9]", "", "".join(l["toks"]).lower())

    tops = Counter()
    for lines in pages[start:]:
        if lines:
            y = min(l["y0"] for l in lines)
            for l in lines:
                if l["y0"] < y + 4:
                    tops[re.sub(r"\d+", "#", norm(l))] += 1
    heads = {k for k, c in tops.items() if c >= 8}
    end = len(pages)
    for i in range(start + 1, len(pages)):
        lines = pages[i]
        if not lines:
            continue
        y = min(l["y0"] for l in lines)
        body = [l for l in lines if not (l["y0"] < y + 4 and re.sub(r"\d+", "#", norm(l)) in heads)]
        if any(END_PAGE.match(re.sub(r"[^a-z]", "", norm(l))) for l in body[:3]):
            end = i
            break
    report["pages"] = f"{start + 1}-{end} of {len(pages)}"
    report["heads"] = sorted(heads)
    stream = []
    for i in range(start, end):
        lines = pages[i]
        if not lines:
            continue
        y = min(l["y0"] for l in lines)
        body = []
        for l in lines:
            if l["y0"] < y + 4 and re.sub(r"\d+", "#", norm(l)) in heads:
                continue
            if l["y0"] > 585 and re.fullmatch(r"\d{1,4}", "".join(l["toks"])):
                continue
            body.append(l)
        if not body:
            continue
        xs = Counter(round(l["x0"], 0) for l in body)
        cands = [x for x, c in xs.most_common(3)]
        pl = min(cands, key=lambda x: (-(xs[x] + xs.get(x + 11, 0)), x)) if len(body) >= 6 else None
        for l in body:
            l["page"] = i
            l["pl"] = pl
        stream.extend(body)
    by_parity = {}
    for l in stream:
        if l["pl"] is not None:
            by_parity.setdefault(l["page"] % 2, Counter())[l["pl"]] += 1
    for l in stream:
        if l["pl"] is None:
            c = by_parity.get(l["page"] % 2)
            l["pl"] = c.most_common(1)[0][0] if c else min(x["x0"] for x in stream)
        l["x0"] -= l["pl"]
        l["x1"] -= l["pl"]
    left = 0
    ind = Counter(round(l["x0"]) for l in stream if 5 <= round(l["x0"]) <= 20)
    indent = ind.most_common(1)[0][0] if ind else 11
    right = max(l["x1"] for l in stream)
    vocab = Counter()
    for l in stream:
        for t in l["toks"][:-1]:
            vocab[re.sub(r"^[^\w]+|[^\w]+$", "", t).lower()] += 1
    paras, cur, kind = [], [], None
    heading_vocab = {w for w, c in vocab.items() if c >= 2 and len(w) >= 3}
    acr = Counter()
    evidence = set(SMALLCAP_WORDS)
    seen = Counter()
    prev_cap = False
    for l in stream:
        is_cap = l["y1"] - l["y0"] > 25
        skip = l["caps_open"] or prev_cap or is_cap
        prev_cap = is_cap
        if skip:
            continue
        for t, f in zip(l["toks"], l["frag"]):
            core = re.sub(r"^[^\w]+|[^\w]+$", "", t)
            if f < 2 or not core.isalpha() or not core.islower() or not 2 <= len(core) <= 6:
                continue
            forms = {core, core[:-1] if core.endswith("s") else core, re.sub(r"(ed|d|ing|es)$", "", core),
                     re.sub(r"(ed|ing)$", "e", core)}
            if not (forms & WORDS) and core not in TWO and core not in NAMES:
                seen[core] += 1
    for core, c in seen.items():
        if len(core) <= 4 or c >= 2:
            plural = core.endswith("s") and core[:-1] in seen
            evidence.add(core[:-1] if plural else core)
    report["evidence"] = sorted(evidence)

    def close():
        nonlocal cur, kind
        if cur:
            t = re.sub(r"(?<=[\w”’]) ([.,;:!?])", r"\1", " ".join(cur))
            t = ws(re.sub(r"(https?://|www\.)\s?[\w ]{0,30}\.(com|org|net)\b\S*", "", t))
            paras.append(t)
        cur, kind = [], None

    def add(toks):
        if cur and cur[-1].endswith("-") and len(cur[-1]) > 1 and not cur[-1].endswith(("--", "—-")) and \
                toks and re.match(r"[a-z]", toks[0]):
            a, b = cur[-1][:-1], toks[0]
            joined = re.sub(r"^[^\w]+|[^\w]+$", "", a + b).lower()
            hyph = re.sub(r"^[^\w]+|[^\w]+$", "", a + "-" + b).lower()
            ka = re.sub(r"^[^\w]+|[^\w]+$", "", a).lower()
            kb = re.sub(r"^[^\w]+|[^\w]+$", "", b).lower()
            whole = vocab[joined] or joined in WORDS or re.sub(r"(s|ed|d|ing|ly|es)$", "", joined) in WORDS
            base = lambda w: w in WORDS or vocab[w] or re.sub(r"(s|ed|d|ing|es)$", "", w) in WORDS
            parts = len(ka) > 2 and len(kb) > 2 and base(ka) and base(kb)
            if whole or not (vocab[hyph] or parts):
                cur[-1] = a + b
            else:
                cur[-1] = a + "-" + b
            cur.extend(toks[1:])
        else:
            cur.extend(toks)

    cap = None
    opening = True
    prev = None
    for l in stream:
        h = l["y1"] - l["y0"]
        text = " ".join(l["toks"])
        same_page = prev is not None and prev["page"] == l["page"]
        gap = (l["y0"] - prev["y0"]) if same_page else 0
        if h > 25 and len(text) <= 3:
            close()
            cap = l
            cur = [text]
            kind = "cap"
            prev = l
            continue
        toks = list(l["toks"])
        in_cap = kind == "cap" and cap is not None and l["y0"] < cap["y1"] - 2
        flush = abs(l["x0"] - left) <= 1.5
        fresh = flush and (kind == "other" or not cur or (same_page and gap > 2.2 * 14))
        top_open = flush and not fresh and not in_cap and not same_page and l["caps_open"] and cur \
            and re.search(r"[.!?”’\"']$", cur[-1])
        if top_open:
            close()
            if paras and paras[-1] != BREAK:
                paras.append(BREAK)
            fresh = True
        if not in_cap and not fresh and not l["caps_open"]:
            for i, t in enumerate(toks):
                if re.fullmatch(r"[“‘(]?tvs?[.,;:!?”’)]*", t):
                    toks[i] = t.replace("tv", "TV")
                    continue
                for core in re.findall(r"[a-z]+", t):
                    stem = core[:-1] if core.endswith("s") and len(core) > 2 else core
                    if core in evidence or (stem in evidence and core not in WORDS and len(stem) > 1):
                        up = core.upper() if core in evidence else stem.upper() + "s"
                        toks[i] = toks[i].replace(core, up, 1)
                        acr[up] += 1
        if kind == "cap" and cap is not None and l["y0"] < cap["y1"] - 2:
            if len(cur) == 1 and cap is prev:
                cur[0] = cur[0] + toks[0]
                cur.extend(toks[1:])
            else:
                add(toks)
            prev = l
            continue
        if kind == "cap":
            kind = "body"
            cap = None
        x = l["x0"]
        if re.fullmatch(r"[.,;:!?”’\"')]+", text) and cur:
            cur[-1] += text
            continue
        if ORNAMENT.match(text):
            close()
            if paras and paras[-1] != BREAK:
                paras.append(BREAK)
            opening = True
            prev = l
            continue
        if abs(x - left) <= 1.5:
            if kind == "other" or (same_page and gap > 2.2 * 14 and kind == "body"):
                was_body = kind == "body"
                close()
                if was_body and paras and paras[-1] != BREAK:
                    paras.append(BREAK)
            if not cur:
                kind = "body"
            add(toks)
            opening = False
        elif abs(x - indent) <= 1.5 and kind != "other-run":
            close()
            kind = "body"
            add(toks)
            opening = False
        else:
            if kind == "other" and prev is not None and abs(prev["x0"] - x) <= 1 and prev["x1"] > right - 25 \
                    and same_page and gap < 20:
                add(toks)
            else:
                close()
                kind = "other"
                add(toks)
            opening = True
        prev = l
    close()
    out = []
    merged = 0
    for p in paras:
        if p == BREAK:
            if out and out[-1] != BREAK:
                out.append(p)
            continue
        if out and out[-1] != BREAK and re.match(r"[a-z]", p) and len(out[-1]) > 40 and \
                not re.search(r"[.!?”’»:…\"')—]$", out[-1]):
            if re.search(r"[A-Za-z]-$", out[-1]):
                out[-1] = out[-1][:-1] + p
            else:
                out[-1] = out[-1] + " " + p
            merged += 1
            continue
        if p == p.lower() and len(p.replace(" ", "")) <= 40 and re.search(r"[a-z]", p) and \
                not re.search(r"[.!?,;:”»]$", p) and not re.search(r"\d", p):
            p = segment(p, heading_vocab).title().replace("’S", "’s")
        elif (not out or out[-1] == BREAK) and re.match(r"[a-z]", p):
            p = p[0].upper() + p[1:]
        out.append(p)
    while out and out[-1] == BREAK:
        out.pop()
    report["merged_continuations"] = merged
    report["smallcaps_uppercased"] = sum(acr.values())
    return "\n\n".join(out)


def shingles(text, n=8):
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(0, max(len(w) - n + 1, 0))}


def main():
    TEXT.mkdir(exist_ok=True)
    for old in TEXT.glob("*.txt"):
        old.unlink()
    works = fetch.catalogue()
    recs, novels, reports = [], {}, {}
    for w in works:
        if w["section"] != "novel":
            continue
        m = re.match(r"(.*?)\s*\((\d{4})\)$", w["title"])
        title = ws(m.group(1)).title().replace(" Of ", " of ").replace(" The ", " the ") if m else w["title"]
        stem = w["pdf"][:-4]
        rep = {}
        text = novel(RAW / w["pdf"], rep)
        reports[stem] = rep
        novels[stem] = text
        slug = slugify(title)
        (TEXT / f"{slug}.txt").write_text(text + "\n", encoding="utf-8")
        recs.append({"url": BASE + w["pdf"], "slug": slug, "title": title, "author": AUTHOR,
                     "year": int(m.group(2)) if m else None, "kind": "novel", "words": len(text.split()),
                     "file": f"text/{slug}.txt", "format": "pdf", "pdf_pages_kept": rep["pages"],
                     "licence_or_basis": MANIFESTO + " (the PDF itself names no licence; every HTML page on the site "
                                         "links creativecommons.org/licenses/by-nc-nd/3.0/us/)", "status": "ok"})
    grams = {k: shingles(v) for k, v in novels.items()}
    used = {r["slug"] for r in recs}
    for w in works:
        if w["section"] == "novel":
            continue
        src = w["html"] or w["pdf"] or ""
        base = {"url": src if src.startswith("http") else BASE + src, "slug": slugify(w["title"]), "title": w["title"],
                "author": AUTHOR, "year": None, "kind": w["section"], "words": 0, "file": ""}
        if w["section"] != "story":
            base["status"] = f"skipped: {w['section']}, not fiction prose in English (not fetched)"
            recs.append(base)
            continue
        if src.startswith("http"):
            base["status"] = "skipped: hosted on another site (not fetched)"
            recs.append(base)
            continue
        s = story(RAW / src)
        stem = src.rsplit(".", 1)[0]
        base.update({"title": s["title"] or w["title"], "year": s["year"], "words": len(s["text"].split()),
                     "format": "html", "first_published": s["credit"],
                     "licence_or_basis": (s["licence"] or "none stated on the page") + "; " + MANIFESTO})
        base["slug"] = slugify(base["title"])
        if stem in DUP_OF:
            sh = shingles(s["text"])
            ov = len(sh & grams[DUP_OF[stem]]) / max(len(sh), 1)
            base["overlap_with_novel"] = round(ov, 3)
            if ov >= 0.5:
                base["status"] = f"skipped: duplicate ({ov:.0%} of its 8-word runs are in the novel {DUP_OF[stem]}.pdf; {w['blurb']})"
                recs.append(base)
                continue
        name = base["slug"]
        if name in used:
            name = f"{name}-story"
        used.add(name)
        base["slug"] = name
        base["file"] = f"text/{name}.txt"
        base["status"] = "ok"
        (TEXT / f"{name}.txt").write_text(s["text"] + "\n", encoding="utf-8")
        recs.append(base)
    with open(ROOT / "ledger.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = [r for r in recs if r["status"] == "ok"]
    print(len(ok), "works,", sum(r["words"] for r in ok), "words")
    for k, v in reports.items():
        print(k, v)
    for r in recs:
        if "overlap_with_novel" in r:
            print(r["title"], r["overlap_with_novel"], r["status"][:40])
    print(Counter(r["status"].split(" (")[0][:60] for r in recs if r["status"] != "ok"))


if __name__ == "__main__":
    main()
