import gzip, json, os, re, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Shelf, get, paragraphs, join, norm, words
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")
AUTHOR = "Rudy Rucker"
FREE = "https://www.rudyrucker.com/blog/rudy-rucker-free-books/"
QUOTE = 'rudyrucker.com/blog/rudy-rucker-free-books/: "I want people to read these, and I want AIs and bots to read them, and to train on them" (no republishing or selling)'
CC = "CC BY-NC-ND (stated in the book's own pages); "
sh = Shelf("rucker")

SRC = {
    "wares": "https://www.rudyrucker.com/wares/cc_downloads/html/",
    "juicyghosts": "https://www.rudyrucker.com/juicyghosts/HTML",
    "spaceland": "https://www.rudyrucker.com/spaceland/html_edition/index.html",
    "whitelight": "https://www.rudyrucker.com/whitelight/sample/whitelight.xhtml",
    "jimandtheflims": "https://www.rudyrucker.com/jimandtheflims/HTML/",
    "allthevisions": "https://www.rudyrucker.com/allthevisions/sample/allthevisions.xhtml",
}
JUNK = re.compile(r"Copyright ©|Creative Commons|can be purchas|Back to Table of Contents|Buy a paperback|free online browsing|browsing edition", re.I)
BREAK = re.compile(r"[\s*#§~•·.\-—_=]*")


def leaves(name):
    p = os.path.join(sh.dir, "raw", name + ".html.gz")
    if os.path.exists(p):
        html = gzip.open(p, "rt", encoding="utf-8").read()
    else:
        html = get(SRC[name])
        sh.raw_html(name, html)
    s = BeautifulSoup(html, "lxml")
    out = []
    for e in s.body.find_all(["p", "h1", "h2", "h3", "h4", "div"]):
        if e.find(["p", "div", "h1", "h2", "h3", "h4"]):
            continue
        k = e.name + "." + " ".join(e.get("class") or [])
        t = norm(" ".join(paragraphs(e)) if e.find("br") is None else "\n".join(paragraphs(e)))
        out.append((k, t, e))
    return out


def text_of(e):
    return [norm(x) for x in paragraphs(e) if norm(x)]


def clean(lines):
    out = []
    for t in lines:
        t = norm(t)
        if not t or BREAK.fullmatch(t) or JUNK.search(t):
            continue
        t = re.sub(r"^([B-HJ-Z]) ([a-z])", r"\1\2", t)
        out.append(t)
    return out


def wares():
    els = leaves("wares")
    books, cur = {}, None
    for k, t, e in els:
        if k == "h1." :
            u = t.upper()
            cur = u if u in ("SOFTWARE", "WETWARE", "FREEWARE", "REALWARE") else None
            if cur:
                books[cur] = []
            continue
        if cur is None:
            continue
        if k == "h3.":
            books[cur].append(t)
        elif books[cur]:
            books[cur].extend(text_of(e))
    years = {"SOFTWARE": 1982, "WETWARE": 1988, "FREEWARE": 1997, "REALWARE": 2000}
    for b, lines in books.items():
        emit(b.lower(), b.title(), years[b], clean(lines), SRC["wares"], CC + QUOTE)


def juicyghosts():
    out, on = [], False
    for k, t, e in leaves("juicyghosts"):
        if k == "p.h1":
            if t.lower().startswith("afterword"):
                break
            on = True
            out.append(t)
        elif on and k == "p.epubtext":
            out.extend(text_of(e))
    emit("juicy-ghosts", "Juicy Ghosts", 2021, clean(out), SRC["juicyghosts"], QUOTE)


def spaceland():
    out, on, num = [], False, None
    for k, t, e in leaves("spaceland"):
        if k == "div.title-chapter":
            on, num = True, t
            continue
        if not on:
            continue
        if k == "div.title-toc":
            break
        if k in ("div.subtitle-chapter", "p.b1") and num:
            out.append(f"{num}: {t}")
            num = None
        elif k in ("div.p", "div.p-indent"):
            out.extend(text_of(e))
    emit("spaceland", "Spaceland", 2002, clean(out), SRC["spaceland"], QUOTE)


def whitelight():
    out, on, part = [], False, False
    for k, t, e in leaves("whitelight"):
        if k == "p.h2" and t == "Part I":
            on = True
        if not on:
            continue
        if k == "p.h2":
            part = t.startswith("Part")
            out.append(re.sub(r"^6: Inflatable", "16: Inflatable", re.sub(r"^9 Hilbert", "9: Hilbert", t)))
        elif part:
            continue
        elif k.startswith("p.epubtext") and k != "p.epubtext-centered":
            out.extend(text_of(e))
    emit("white-light", "White Light", 1980, clean(out), SRC["whitelight"], QUOTE)


def jim():
    out, on = [], False
    for k, t, e in leaves("jimandtheflims"):
        if k == "p.h" and re.match(r"1:", t):
            on = True
        if not on:
            continue
        if k.startswith("p.epub-title"):
            break
        if k == "p.h":
            out.append(t)
        elif k == "p.epubtext":
            out.extend(text_of(e))
    emit("jim-and-the-flims", "Jim and the Flims", 2011, clean(out), SRC["jimandtheflims"], QUOTE)


def visions():
    out, on = [], False
    for k, t, e in leaves("allthevisions"):
        if k == "p.h1" and t.startswith("Take 1"):
            on = True
        if not on:
            continue
        if k.startswith("p.TOC"):
            break
        if k == "p.h1":
            out.append(t)
        elif k.startswith("p.epubtext") and k not in ("p.epubtext-centered", "p.epubtext-flushright"):
            out.extend(text_of(e))
    emit("all-the-visions", "All the Visions", 1991, clean(out), SRC["allthevisions"], QUOTE)


def emit(slug, title, year, lines, url, basis):
    sh.write(slug, join(lines), url=url, title=title, author=AUTHOR, year=year, kind="novel", licence_or_basis=basis)
    sh.beat()
    t = open(os.path.join(sh.dir, "text", slug + ".txt")).read()
    print(f"{slug}\t{words(t)}")


def relicense():
    rows = [json.loads(l) for l in open(sh.ledger)]
    for o in rows:
        if o["slug"] == "saucer-wisdom":
            continue
        if o["slug"] == "postsingular":
            o["licence_or_basis"] = "CC BY-NC-ND, author's own free edition: https://www.rudyrucker.com/postsingular/cc_downloads; " + QUOTE
        elif o["slug"] in ("software", "wetware", "freeware", "realware"):
            o["licence_or_basis"] = CC + QUOTE
        else:
            o["licence_or_basis"] = QUOTE
    with open(sh.ledger + ".tmp", "w") as f:
        for o in rows:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    os.replace(sh.ledger + ".tmp", sh.ledger)


if __name__ == "__main__":
    which = sys.argv[1:] or ["wares", "juicyghosts", "spaceland", "whitelight", "jim", "visions"]
    for w in which:
        globals()[w]()
