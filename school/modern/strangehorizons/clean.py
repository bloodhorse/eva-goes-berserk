import gzip
import html
import json
import re
import shutil
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Comment, Tag

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
HR = "\x00HR"
EMPTY = "\x00EMPTY"
BREAK = "* * *"

DROP_TAGS = {"script", "style", "object", "embed", "iframe", "audio", "video", "img", "figure",
             "figcaption", "noscript", "button", "form", "input", "svg", "source", "param", "map"}
BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "blockquote", "pre",
              "center", "table", "tr", "td", "th", "section", "article", "dl", "dt", "dd", "address"}
DROP_CLASS = re.compile(r"content-warning|wp-caption|image-right|image-left|image-center|sharedaddy|jp-relatedposts|audioplayer|clear_both")

HEAD_JUNK = re.compile(
    r"^part \w+ of \w+\.?$|^read (the )?part \w+|fund ?drive|^this (week'?s )?(story|poem|piece)|^reprinted|"
    r"^originally (published|appeared)|^first published|^click here|podcast|^tales of the chinese zodiac|"
    r"^content warning|^editor'?s? note|^\(?see also|^our process with art|^listen to|"
    r"also be read in|can also be read|^\(?read (this|the) (story|poem)|translation\.?\)?$|^by [A-Z]",
    re.I)
ANY_JUNK = re.compile(
    r"©|\bcopyright\b|^click here|\bpodcast\b|^read part \w+|read part \w+ here|^\[?\s*editor'?s? note|"
    r"^illustrations? (by|©)|^art by|this (story|poem|piece) (is|was) (no longer|part of|one of|made possible|first|originally)|"
    r"publication of this (poem|story) was made possible|^part \w+ of \w+\.?$|^(read|listen)\b.{0,60}\bhere\b|"
    r"^\s*\(?\s*(previous|next):|^return to the|^reader comments$|creative commons|if you redistribute this|comments on this story|fiction forum|^play .{1,120} by .{1,80}$|has provided (detailed )?content warnings",
    re.I)
CREDIT = re.compile(r"^([\w-]+ ){0,2}(editors?|first readers?|copy ?editors?|copy editing|accessibility|art|artist|illustrations?|"
                    r"illustrator|podcast|audio|narrat\w+|translat\w+ by|proofread\w*|cover art)\s*:", re.I)
BIO = re.compile(
    r"\blives (in|with|on|near)\b|\bis an? (\w+ ){0,3}(writer|poet|author|novelist|editor|artist)\b|\bis the author\b|"
    r"\b(work|works|stories|poems|poetry|fiction|writing) (has|have) (also )?(appeared|been published)\b|\bhas (been )?published\b|"
    r"\bcan be (reached|found)\b|\bsend (him|her|them) (an )?e-?mail\b|\be-?mail\b|\bwebsite\b|\btwitter\b|\bblog\b|"
    r"\bgraduate of\b|\bclarion\b|\bour archive|\bstrange horizons\b|\bhis first\b|\bher first\b|\bher debut\b|\bhis debut\b|"
    r"\bauthor of\b|\bweb ?site\b|\bhas been (publishing|writing)\b|\bsplits (his|her|their) time\b|\bcurrently (lives|resides|teaches|works)\b|\bpreviously appeared\b|\bforthcoming\b|\banthologies\b|\bmfa\b|\bnominated\b|\bnominee\b|\bfind (him|her|them)\b|@|\.com\b",
    re.I)
NAME_START = re.compile(r"^[A-Z][\w.'’-]*\.?( [A-Z][\w.'’-]*\.?){1,3}('s|’s| is| lives| has| was| writes| grew| works| teaches| began| studied|,)")
LOOSE_NAME = re.compile(r"^[A-Z][\w.'’-]+( [A-Z][\w.'’-]+){1,3} [a-z]")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
INTRO = re.compile(r"^(introduction( to\b|:)|poem analysis\b)", re.I)
LIVES = re.compile(r"^[A-Z][\w.'’-]*\.?( [A-Z][\w.'’-]*\.?){1,3} lives (in|near|with)\b")
SKIP_IDS = {53464: "skipped: column (recap of a radio serial), not a work", 58172: "skipped: poem analysis, not a work", 58185: "skipped: poem analysis, not a work", 40063: "skipped: editorial introduction to a special issue", 44080: "skipped: editorial", 57253: "skipped: editorial retrospective, not a work", 812: "skipped: editor's introduction, not the work", 1184: "skipped: introduction to a withdrawn story"}
BREAKISH = re.compile(r"^[\s*#~§•·⁂◊○●oO0×xX+=_\-–—.:|/\\]{1,20}$")
URL = re.compile(r"https?://\S+|www\.\S+")
TITLE_PART = re.compile(r"\s*[\(\[]?\s*[-–—:,]?\s*\bpart\s+(\d+|[ivx]+)(\s+of\s+(\d+|[ivx]+))?\s*[\)\]]?\s*$", re.I)
TITLE_SKIP = re.compile(r"\b(fund ?drive|announc\w*|table of contents|short fiction treasures|submissions? (are )?(open|closed)|contest winners?|call for)\b", re.I)
STOP = set("the of and to a in is was that it he she i you his her for on with as but not at my me we they".split())
ES = set("de la el que y en los las por con una del se no su para es un al lo como".split())
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}


def norm_ws(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def blocks_of(htmltext, poetry):
    soup = BeautifulSoup(htmltext, "lxml")
    for t in soup.find_all(DROP_TAGS):
        t.decompose()
    for t in soup.find_all(class_=DROP_CLASS):
        t.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    if poetry:
        for st in soup.find_all("div", class_="stanza"):
            for p in st.find_all("p"):
                p.append(soup.new_tag("br"))
                p.unwrap()
    blocks = []
    cur = []
    buf = []

    def end_line():
        line = norm_ws("".join(buf))
        buf.clear()
        cur.append(line)

    def flush():
        if buf:
            end_line()
        lines = [l for l in cur]
        cur.clear()
        while lines and not lines[-1]:
            lines.pop()
        while lines and not lines[0]:
            lines.pop(0)
        blocks.append(lines if lines else EMPTY)

    def walk(node):
        for ch in list(node.children):
            if isinstance(ch, NavigableString):
                buf.append(str(ch))
            elif isinstance(ch, Tag):
                n = ch.name
                if n == "br":
                    end_line()
                elif n == "hr":
                    flush()
                    blocks.append(HR)
                elif n in BLOCK_TAGS:
                    flush()
                    walk(ch)
                    flush()
                else:
                    walk(ch)

    body = soup.body or soup
    walk(body)
    flush()
    out = []
    for b in blocks:
        if b == EMPTY and out and out[-1] == EMPTY:
            continue
        out.append(b)
    return out


def text_of(b):
    return " ".join(b) if isinstance(b, list) else ""


def is_bio_para(t):
    if CREDIT.match(t):
        return True
    if len(t.split()) > 220:
        return False
    hits = len(set(m.group(0).lower() for m in BIO.finditer(t)))
    return hits >= 2 or (hits >= 1 and bool(NAME_START.match(t) or LOOSE_NAME.match(t)))


def strict_bio(t):
    if len(t.split()) > 150 or not NAME_START.match(t):
        return False
    hits = len(set(m.group(0).lower() for m in BIO.finditer(t)))
    return hits >= 2 or (len(t.split()) < 80 and bool(LIVES.match(t)))


def strip_tail(blocks, removed):
    changed = True
    while changed:
        changed = False
        while blocks and (blocks[-1] in (HR, EMPTY) or (isinstance(blocks[-1], list) and BREAKISH.match(text_of(blocks[-1]) or "x"))):
            blocks.pop()
            changed = True
        while blocks and isinstance(blocks[-1], list) and (is_bio_para(text_of(blocks[-1])) or ANY_JUNK.search(text_of(blocks[-1]))):
            removed.append(text_of(blocks.pop()))
            changed = True
        if HR in blocks:
            i = len(blocks) - 1 - blocks[::-1].index(HR)
            seg = [text_of(b) for b in blocks[i + 1:] if isinstance(b, list)]
            words = sum(len(s.split()) for s in seg)
            dirt = sum(len(s.split()) for s in seg if is_bio_para(s) or ANY_JUNK.search(s))
            if seg and words < 300 and dirt >= 0.6 * words:
                removed.extend(seg)
                del blocks[i:]
                changed = True
    return blocks


def strip_head(blocks):
    while blocks:
        b = blocks[0]
        if b in (HR, EMPTY):
            blocks.pop(0)
            continue
        t = text_of(b)
        if BREAKISH.match(t) or (len(t.split()) < 80 and HEAD_JUNK.search(t)):
            blocks.pop(0)
            continue
        break
    return blocks


def clean_line(s):
    s = URL.sub("", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def render(blocks, poetry):
    paras = []
    multi = sum(1 for b in blocks if isinstance(b, list) and len(b) > 1)
    single = [b for b in blocks if isinstance(b, list) and len(b) == 1]
    lens = sorted(len(b[0].split()) for b in single) or [0]
    line_per_p = poetry and multi == 0 and lens[len(lens) // 2] <= 14
    stanza = []
    for b in blocks:
        if b == HR:
            if stanza:
                paras.append("\n".join(stanza))
                stanza = []
            paras.append(BREAK)
            continue
        if b == EMPTY:
            if line_per_p and stanza:
                paras.append("\n".join(stanza))
                stanza = []
            continue
        t = text_of(b)
        if len(t.split()) < 60 and ANY_JUNK.search(t) or len(t.split()) < 15 and CREDIT.match(t) or strict_bio(t):
            continue
        lines = [clean_line(l) for l in b]
        if BREAKISH.match(" ".join(lines)):
            if stanza:
                paras.append("\n".join(stanza))
                stanza = []
            paras.append(BREAK)
            continue
        if poetry:
            lines = [l for l in lines]
            while lines and not lines[0]:
                lines.pop(0)
            while lines and not lines[-1]:
                lines.pop()
            if not lines:
                continue
            if line_per_p:
                stanza.append(lines[0] if len(lines) == 1 else " ".join(lines))
            else:
                chunk, out = [], []
                for l in lines:
                    if l:
                        chunk.append(l)
                    elif chunk:
                        out.append("\n".join(chunk))
                        chunk = []
                if chunk:
                    out.append("\n".join(chunk))
                paras.extend(out)
        else:
            for l in lines:
                if l:
                    paras.append(l)
    if stanza:
        paras.append("\n".join(stanza))
    res = []
    for p in paras:
        if p == BREAK and (not res or res[-1] == BREAK):
            continue
        res.append(p)
    while res and res[-1] == BREAK:
        res.pop()
    return "\n\n".join(res)


def author_from(raw_text, removed):
    m = re.search(r"Copyright\s*©\s*\d{4},?\s*(?:by\s+)?([A-Z][^\n©]{2,60}?)(?=\s+(?:Illustration|Art|Image|Photo)|\s*$|\s*\n|\.\s)", raw_text)
    if m:
        return norm_ws(m.group(1)).rstrip(".")
    for r in removed:
        m = re.match(r"^((?:[A-Z][\w.'’-]*\.? ?){2,4}?)(?:'s|’s| is| lives| has| was| writes| grew| works| teaches| began| studied)\b", r)
        if m:
            return m.group(1).strip()
    return ""


def english(text, poetry):
    chars = re.sub(r"\s", "", text)
    if chars and len(CJK.findall(chars)) / len(chars) > 0.2:
        return False
    w = re.findall(r"[a-zA-Z’']+", text.lower())
    if len(w) < 30:
        return True
    en = sum(1 for x in w if x in STOP) / len(w)
    es = sum(1 for x in w if x in ES) / len(w)
    if es > en:
        return False
    return len(w) < 150 or en >= 0.06


def load():
    posts = []
    seen = set()
    for kind in ("fiction", "poetry"):
        files = sorted(RAW.glob(f"{kind}-*.json.gz"), key=lambda p: int(p.name.split("-")[1].split(".")[0]))
        for f in files:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for p in json.load(fh):
                    if p["id"] in seen:
                        continue
                    seen.add(p["id"])
                    p["_kind"] = kind
                    posts.append(p)
    return posts


def title_key(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def main():
    posts = load()
    for d in ("text", "poetry"):
        if (ROOT / d).exists():
            shutil.rmtree(ROOT / d)
        (ROOT / d).mkdir()
    recs = []
    for p in posts:
        poetry = p["_kind"] == "poetry"
        title = norm_ws(BeautifulSoup(html.unescape(p["title"]["rendered"]), "lxml").get_text())
        kind = "poem" if poetry else ("reprint" if 598 in p["categories"] else "story")
        rawhtml = p["content"]["rendered"]
        raw_text = BeautifulSoup(rawhtml, "lxml").get_text("\n")
        blocks = blocks_of(rawhtml, poetry)
        removed = []
        blocks = strip_head(strip_tail(strip_head(blocks), removed))
        text = render(blocks, poetry)
        rec = {"id": p["id"], "url": p["link"], "slug": p["slug"], "title": title,
               "author": author_from(raw_text, removed), "date": p["date"], "kind": kind,
               "words": len(text.split()), "file": "", "status": "ok", "_text": text, "_poetry": poetry}
        m = TITLE_PART.search(title)
        hm = re.match(r"\s*part (\d+|[ivx]+) of (\d+)", raw_text.strip()[:40], re.I)
        rec["_part"] = None
        if m and m.start() > 0:
            n = m.group(1).lower()
            rec["_part"] = int(n) if n.isdigit() else ROMAN.get(n)
            rec["_base"] = title_key(title[:m.start()])
        elif hm:
            n = hm.group(1).lower()
            rec["_part"] = int(n) if n.isdigit() else ROMAN.get(n)
            rec["_base"] = title_key(title)
        if p["id"] in SKIP_IDS:
            rec["status"] = SKIP_IDS[p["id"]]
        elif INTRO.match(title):
            rec["status"] = "skipped: editorial introduction or analysis, not the work"
        elif TITLE_SKIP.search(title) and rec["words"] < 1500:
            rec["status"] = "skipped: announcement"
        elif rec["words"] < 40 and re.search(r"no longer available", raw_text, re.I):
            rec["status"] = "skipped: withdrawn from the site"
        elif rec["words"] < (8 if poetry else 40):
            rec["status"] = "skipped: no text (podcast/art/notice only)"
        elif not english(text, poetry):
            rec["status"] = "skipped: not English"
        recs.append(rec)

    groups = {}
    for r in recs:
        if r["_part"] and r["status"] == "ok":
            groups.setdefault((r["_poetry"], r["_base"]), []).append(r)
    for g in groups.values():
        if len(g) < 2:
            continue
        g.sort(key=lambda r: (r["_part"], r["date"]))
        head = g[0]
        head["_text"] = "\n\n".join(r["_text"] for r in g)
        head["words"] = len(head["_text"].split())
        head["title"] = TITLE_PART.sub("", head["title"]).strip()
        for r in g[1:]:
            r["status"] = f"merged-into:{head['slug']}"
            r["_merged_to"] = head

    used = {"text": set(), "poetry": set()}
    for r in sorted(recs, key=lambda r: r["date"]):
        if r["status"] != "ok":
            continue
        d = "poetry" if r["_poetry"] else "text"
        name = r["slug"]
        if name in used[d]:
            name = f"{r['slug']}-{r['id']}"
        used[d].add(name)
        r["file"] = f"{d}/{name}.txt"
        (ROOT / r["file"]).write_text(r["_text"] + "\n", encoding="utf-8")
    for r in recs:
        if "_merged_to" in r:
            r["file"] = r["_merged_to"]["file"]
    with open(ROOT / "ledger.jsonl", "w", encoding="utf-8") as f:
        for r in sorted(recs, key=lambda r: r["date"]):
            f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
    from collections import Counter
    c = Counter((r["kind"], r["status"].split(":")[0] if not r["status"].startswith("skipped") else r["status"]) for r in recs)
    for k, v in sorted(c.items()):
        print(v, *k)


if __name__ == "__main__":
    main()
