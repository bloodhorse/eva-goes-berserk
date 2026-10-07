import gzip
import html
import json
import re
import unicodedata
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
TEXT = ROOT / "text"
HR = "\x00HR"
BREAK = "* * *"
L, R = "\x01", "\x02"

DROP_TAGS = {"script", "style", "object", "embed", "iframe", "audio", "video", "img", "figure", "figcaption",
             "noscript", "button", "form", "input", "svg", "source"}
BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "blockquote", "pre", "center",
              "table", "tr", "td", "th", "section", "article", "dl", "dt", "dd"}
SENT = re.compile(r"(?<=[.!?…\"”’])\s+(?=[\"“‘A-Z\[(\x01])")
CYR = re.compile(r"[Ѐ-ӿ]")
LAT = re.compile(r"[A-Za-z]")
BREAKISH = re.compile(r"^[\s*#~§•·⁂◊○●oO×xX+=_\-–—.:|/\\♦❖∞]{1,40}$")
COPYRIGHT = re.compile(r"^\s*(?:copyright|©|\(c\))\s*(?:©|\(c\))?\s*(\d{4})?,?\s*(?:by\s+)?(.{2,80}?)\s*\.?\s*$", re.I)
TAIL_JUNK = re.compile(
    r"^(about the author|author'?s?’?s? note|editor'?s?’?s? note|acknowledge?ments?|originally (published|appeared)|"
    r"first (published|appeared)|this story (first|originally|was first)|reprinted|the end\.?$|end\.?$|fin\.?$|"
    r"check out this|translated (from|by)|translation (copyright|©)|art(work)? by|illustration)", re.I)
HEAD_JUNK = re.compile(
    r"^(by\s+[A-Z]|editor'?s?’?s? note|content (warning|note)|cw:|tw:|trigger warning|author'?s?’?s? note|"
    r"originally (published|appeared)|first (published|appeared)|translated (from|by)|\[?this story)", re.I)
BIO = re.compile(
    r"\blives (in|with|on|near)\b|\bis an? (\w+ ){0,3}(writer|poet|author|novelist|editor|artist)\b|\bis the author\b|"
    r"\b(work|works|stories|poems|poetry|fiction|writing) (has|have) (also )?(appeared|been published)\b|"
    r"\bcan be (reached|found)\b|\bwebsite\b|\btwitter\b|\bblog\b|\bgraduate of\b|\bclarion\b|\bauthor of\b|"
    r"\bforthcoming\b|\banthologies\b|\bmfa\b|\bnominated\b|\bfind (him|her|them)\b|@|\.com\b", re.I)
STOP = set("the of and to a in is was that it he she i you his her for on with as but not at my me we they".split())

UNWRAP = {"business", "commercial solar"}
SPLICES = [
    (460, r", or visiting sites online of porn which we can find at \x01[^\x02]*\x02 online", ""),
    (730, r", about which you can \x01find more\x02", ""),
    (730, r" that \x01you can find out more\x02 about there", ""),
    (812, r", we found \x01[^\x02]*\x02 at cvlinens\.com perfect for the decoration", ""),
    (812, r" with help of \x01[^\x02]*\x02", ""),
    (970, r" and she recommends the \x01[^\x02]*\x02 games to the parents", ""),
    (1007, r"\s*visit \x01Fashion Mag\x02\s*\.", ""),
    (1139, r" either here or at an online casino like \x01[^\x02]*\x02", ""),
    (1334, r"You like stories must check our site \x01[^\x02]*\x02\s*\.\s*", ""),
    (1424, r" to \x01get a better night’s sleep\x02", ""),
    (1424, r"a \x01Northside Locksmith\x02", "a locksmith"),
    (1444, r", she buys her supplements by \x01Amazon\x02", ""),
    (1628, r" by \x01roofers\x02", ""),
    (1646, r"If you want more amazing stories like this \x01[^\x02]*\x02\s*\.?", ""),
    (1646, r"\x01Hospice Cleveland\x02", "hospice"),
    (1686, r"Click here to know \x01[^\x02]*\x02", ""),
    (1697, r"\x01commercial solar\x02", "solar"),
    (1728, r", you can take care of your skin in a healthy way just use \x01[^\x02]*\x02", ""),
    (1730, r" or long before he knew he’d be using \x01[^\x02]*\x02 to run his metier", ""),
    (1730, r", \x01here are the best instagram growth services\x02 which helps you in the marketing your\s+product", ""),
    (1855, r" going around with \x01[^\x02]*\x02", ""),
    (1870, r" or you can check at \x01[^\x02]*\x02", ""),
    (1906, r" as you can even find content as \x01[^\x02]*\x02 online", ""),
    (112, r"Ever thought of changing the color of your eyes temporarily\?\s*\x01[^\x02]*\x02 can help you with that\.", ""),
]
UNLINKED = {
    319: r"^(Telling sexy stories|Using dirty talk|Many people get into a routine|Toys not only keep|"
         r"The first thing that you want to do is to find out what fantasies|Do not be afraid to try this new technique|"
         r"Women like it when you talk softly)",
    766: r"^It will helps you in how to use tax form",
    1054: r"^(If you are facing bankruptcy|You may be thinking that you would not even need a bankrupcy)",
    1728: r"\b(hemp|marijuana|cannabi\w*|CBD|kratom|THC|opioids?)\b|^(It is one of the world’s oldest domesticated crops|"
          r"American industrialist William Randolph Hearst|More and more universities and hospitals|"
          r"It can be ordered online|Its experience extends)",
    1870: r"^Else, it would have been a long evening",
}
SKIP_IDS = {}


def ws(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def external(a):
    h = (a.get("href") or "").strip()
    return h.startswith("http") and "giganotosaurus.org" not in h


def blocks_of(content):
    soup = BeautifulSoup(content, "lxml")
    for t in soup.find_all(DROP_TAGS):
        t.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for s in soup.find_all("sup"):
        if re.fullmatch(r"[\s\[\]\d*†‡ivxlc]*", s.get_text()):
            s.decompose()
    for a in soup.find_all("a"):
        if external(a):
            a.insert_before(L)
            a.insert_after(R)
    blocks, buf = [], []

    def flush():
        t = ws("".join(buf))
        buf.clear()
        if t:
            blocks.append(t)

    def walk(node):
        for ch in list(node.children):
            if isinstance(ch, NavigableString):
                buf.append(str(ch))
            elif isinstance(ch, Tag):
                n = ch.name
                if n == "br":
                    flush()
                elif n == "hr":
                    flush()
                    blocks.append(HR)
                elif n in BLOCK_TAGS:
                    flush()
                    walk(ch)
                    flush()
                else:
                    walk(ch)

    walk(soup.body or soup)
    flush()
    return blocks


def homoglyph(s):
    for w in re.findall(r"[^\W\d_]+", s):
        if CYR.search(w) and LAT.search(w):
            return True
    cyr = len(CYR.findall(s))
    lat = len(LAT.findall(s))
    return cyr > 0 and lat > 3 * cyr and len(re.findall(r"\b[іѕаоеурсх]{1,3}\b|\b[TtYy]?[А-яіѕ]{1,4}\b", s)) >= 1 and \
        bool(re.search(r"\b(іѕ|оf|tо|аnd|thе|уоu|уоur|bе|іn|fоr|саn|аrе|іt|оr|bу|аѕ|а)\b", s))


def despam(pid, para, log):
    if L not in para and not CYR.search(para) and pid not in UNLINKED:
        return para
    orig = para
    for sid, pat, rep in SPLICES:
        if sid == pid:
            para = re.sub(pat, rep, para)
    for w in UNWRAP:
        para = para.replace(L + w + R, w)
    unl = re.compile(UNLINKED[pid], re.I) if pid in UNLINKED else None
    kept, dropped = [], []
    for s in SENT.split(para):
        if L in s or R in s or homoglyph(s) or (unl and unl.search(s)):
            dropped.append(s.replace(L, "[[").replace(R, "]]"))
            if s.rstrip().endswith("”") and kept and kept[-1].count("“") > kept[-1].count("”"):
                kept[-1] = kept[-1] + "”"
            continue
        kept.append(s)
    out = ws(" ".join(kept))
    out = re.sub(r"\s+([.,;:!?”])", r"\1", out) if out != orig else out
    if out != orig:
        log.append({"id": pid, "before": orig.replace(L, "[[").replace(R, "]]"), "after": out, "dropped": dropped})
    return out


def demojibake(text):
    text = text.replace("?™", "’")
    if len(re.findall(r"[A-Za-z]\?[a-z]", text)) < 20:
        return text
    text = re.sub(r"(?<=[A-Za-z])\?(?=[a-z])", "’", text)
    if text.count("“") < 10:
        text = re.sub(r"(?<![\w?])\?(?=[A-Za-z])", "“", text)
        text = re.sub(r"(?<=[.,!?…])\?(?=\s|$)", "”", text)
    return text


def is_bio(t):
    if len(t.split()) > 200:
        return False
    hits = len(set(m.group(0).lower() for m in BIO.finditer(t)))
    return hits >= 2


def strip_tail(blocks, meta):
    changed = True
    while changed and blocks:
        changed = False
        t = blocks[-1]
        if t == HR or BREAKISH.match(t):
            blocks.pop()
            changed = True
            continue
        m = COPYRIGHT.match(t)
        if m and len(t.split()) < 16:
            if m.group(2) and not meta.get("author"):
                meta["author"] = ws(re.sub(r"\b(19|20)\d\d\b|^by\s+", "", m.group(2))).strip(" ,.")
            blocks.pop()
            meta["tail"].append(t)
            changed = True
            continue
        if (len(t.split()) < 120 and TAIL_JUNK.match(t)) or is_bio(t):
            meta["tail"].append(blocks.pop())
            changed = True
            continue
    for i in range(len(blocks) - 1, max(len(blocks) - 12, 0), -1):
        t = blocks[i]
        if t != HR and re.match(r"^(about the author|author'?s?’?s? note)s?:?\b", t, re.I) and \
                sum(len(b.split()) for b in blocks[i:] if b != HR) < 500:
            meta["tail"].extend(b for b in blocks[i:] if b != HR)
            del blocks[i:]
            return strip_tail(blocks, meta)
        m = COPYRIGHT.match(t) if t != HR else None
        if m and len(t.split()) < 16 and re.match(r"(?i)\s*(copyright|©)", t) and \
                sum(len(b.split()) for b in blocks[i:] if b != HR) < 500:
            if m.group(2) and not meta.get("author"):
                meta["author"] = ws(re.sub(r"\b(19|20)\d\d\b|^by\s+", "", m.group(2))).strip(" ,.")
            meta["tail"].extend(b for b in blocks[i:] if b != HR)
            del blocks[i:]
            return strip_tail(blocks, meta)
    return blocks


def strip_head(blocks, meta, title):
    key = re.sub(r"[^a-z0-9]", "", title.lower())
    while blocks:
        t = blocks[0]
        if t == HR or BREAKISH.match(t):
            blocks.pop(0)
            continue
        if re.sub(r"[^a-z0-9]", "", t.lower()) == key and key:
            blocks.pop(0)
            continue
        if len(t.split()) < 90 and HEAD_JUNK.match(t):
            meta["head"].append(blocks.pop(0))
            continue
        break
    return blocks


def english(text):
    w = re.findall(r"[a-zA-Z’']+", text.lower())
    if len(w) < 30:
        return True
    return sum(1 for x in w if x in STOP) / len(w) >= 0.06


def slugify(slug, pid):
    s = urllib.parse.unquote(slug)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or f"post-{pid}"


def byline(pid):
    f = RAW / "pages" / f"{pid}.html"
    if not f.exists():
        return ""
    m = re.search(r'<a[^>]*/people/[^>]*>([^<]+)</a>', f.read_text(encoding="utf-8", errors="replace"))
    return ws(html.unescape(m.group(1))) if m else ""


def load():
    posts, seen = [], set()
    files = sorted(RAW.glob("fiction-*.json.gz"), key=lambda p: int(p.name.split("-")[1].split(".")[0]))
    for f in files:
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for p in json.load(fh):
                if p["id"] not in seen:
                    seen.add(p["id"])
                    posts.append(p)
    return posts


def main():
    TEXT.mkdir(exist_ok=True)
    for old in TEXT.glob("*.txt"):
        old.unlink()
    log, recs, used = [], [], set()
    for p in sorted(load(), key=lambda p: p["date"]):
        pid = p["id"]
        title = ws(BeautifulSoup(html.unescape(p["title"]["rendered"]), "lxml").get_text())
        meta = {"tail": [], "head": [], "author": ""}
        blocks = blocks_of(p["content"]["rendered"])
        n0 = len(log)
        cleaned = []
        for b in blocks:
            if b == HR:
                cleaned.append(b)
                continue
            b = despam(pid, b, log)
            if b:
                cleaned.append(b)
        blocks = strip_head(strip_tail(strip_head(cleaned, meta, title), meta), meta, title)
        paras = []
        for b in blocks:
            if b == HR or BREAKISH.match(b):
                if paras and paras[-1] != BREAK:
                    paras.append(BREAK)
                continue
            b = re.sub(r"https?://\S+|www\.\S+", "", b).strip()
            if b:
                paras.append(b)
        while paras and paras[-1] == BREAK:
            paras.pop()
        text = demojibake("\n\n".join(paras))
        slug = slugify(p["slug"], pid)
        meta["author"] = byline(pid) or meta["author"]
        rec = {"id": pid, "url": p["link"], "slug": slug, "title": title, "author": meta["author"],
               "date": p["date"], "year": int(p["date"][:4]), "kind": "story", "words": len(text.split()),
               "file": "", "spam_edits": len(log) - n0, "status": "ok"}
        if pid in SKIP_IDS:
            rec["status"] = SKIP_IDS[pid]
        elif re.search(r"removed by the publisher", " ".join(meta["head"] + blocks[:2]), re.I):
            rec["status"] = "skipped: removed by the publisher"
        elif not title:
            rec["status"] = "skipped: untitled spam post filed under Fiction"
        elif rec["words"] < 1500:
            rec["status"] = "skipped: announcement filed under Fiction"
        elif not english(text):
            rec["status"] = "skipped: not English"
        if rec["status"] == "ok":
            name = slug if slug not in used else f"{slug}-{pid}"
            used.add(name)
            rec["file"] = f"text/{name}.txt"
            (ROOT / rec["file"]).write_text(text + "\n", encoding="utf-8")
        rec["_cut"] = {"head": meta["head"], "tail": meta["tail"]}
        recs.append(rec)
    with open(ROOT / "ledger.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
    with open(ROOT / "spam_removed.jsonl", "w", encoding="utf-8") as f:
        for e in log:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(ROOT / "cut_edges.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps({"id": r["id"], "slug": r["slug"], **r["_cut"]}, ensure_ascii=False) + "\n")
    ok = [r for r in recs if r["status"] == "ok"]
    print(len(ok), "stories,", sum(r["words"] for r in ok), "words;", len(recs) - len(ok), "skipped;",
          len(log), "paragraphs with spam edits;", sum(1 for r in ok if not r["author"]), "without author")
    for r in recs:
        if r["status"] != "ok":
            print("  ", r["id"], r["title"], r["words"], r["status"])


if __name__ == "__main__":
    main()
