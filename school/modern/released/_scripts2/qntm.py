import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Shelf, get, paragraphs, join, words
from bs4 import BeautifulSoup

BASE = "https://qntm.org/"
AUTHOR = "qntm (Sam Hughes)"
BASIS = "served in full, free, by the author on his own site (https://qntm.org/fiction)"
sh = Shelf("qntm")
cache = {}
NAV = re.compile(r"^(next|previous|prev|back|up|first|last|index|contents)\b\s*:?", re.I)


def page(slug):
    if slug not in cache:
        html = get(BASE + slug)
        sh.raw_html(slug, html)
        cache[slug] = html
    return BeautifulSoup(cache[slug], "lxml")


def meta(s):
    h = s.select_one(".page__h2")
    d = s.select_one(".page__dateline")
    y = re.search(r"(\d{4})-\d\d-\d\d", d.get_text()) if d else None
    return (h.get_text(" ", strip=True) if h else ""), (int(y.group(1)) if y else None)


def children(s, stop_heads=("Everything2", "Extras", "Aftermath", "Appendices")):
    c = s.select_one(".page__content")
    out = []
    for el in c.find_all(["h2", "h3", "h4", "li"]):
        if el.name != "li":
            if any(el.get_text(strip=True).startswith(h) for h in stop_heads):
                break
            continue
        a = el.find("a")
        if a and a.get("href", "").startswith("/") and "/" not in a["href"][1:] and "?" not in a["href"]:
            out.append((a["href"][1:], "(subdirectory)" in el.get_text()))
    return out


def body(s):
    c = s.select_one(".page__content")
    for sel in (".hatnote", ".page__ancestors", "script", "style", ".page__comments"):
        for x in c.select(sel):
            x.decompose()
    for h in c.find_all(["h3", "h4", "h5", "p"]):
        if NAV.match(h.get_text(" ", strip=True)) and h.find("a"):
            h.decompose()
    return [p for p in paragraphs(c) if not NAV.match(p) or len(p) > 80]


def leaves(slug, sub, depth=0):
    s = page(slug)
    if sub and depth < 3:
        out = []
        for k, ksub in children(s):
            out += leaves(k, ksub, depth + 1)
        return out
    return [(slug, s)]


def serial(book, slug, title):
    if book in sh.done:
        return
    s = page(slug)
    parts, years = [], []
    for k, sub in children(s):
        for leaf, ls in leaves(k, sub):
            t, y = meta(ls)
            years.append(y)
            parts.append(t)
            parts += body(ls)
            sh.beat()
    sh.write(book, join(parts), url=BASE + slug, title=title, author=AUTHOR,
             year=min(y for y in years if y), kind="novel", licence_or_basis=BASIS)


def stories(indexes, skip):
    seen = set(skip)
    for idx in indexes:
        for k, sub in children(page(idx), stop_heads=("Aftermath", "A deeper", "Edit", "Follow", "Publication", "Precursor", "First drafts")) if idx != "vhitaos" else [(x, False) for x in ("reading", "difference", "gorge", "person", "responsibility", "transit")]:
            for leaf, ls in leaves(k, sub):
                if leaf in seen or leaf in sh.done:
                    continue
                seen.add(leaf)
                t, y = meta(ls)
                b = body(ls)
                n = words(join(b))
                if n < 300:
                    sh.log(url=BASE + leaf, slug=leaf, title=t, author=AUTHOR, year=y, kind="story", words=n, licence_or_basis=BASIS, status="declined:stub or excerpt under 300 words")
                else:
                    sh.write(leaf, join(b), url=BASE + leaf, title=t, author=AUTHOR, year=y, kind="story", licence_or_basis=BASIS)
                sh.beat()


if __name__ == "__main__":
    which = sys.argv[1:] or ["ra", "structure", "ed", "stories"]
    if "ra" in which:
        serial("ra", "ra", "Ra")
    if "structure" in which:
        serial("fine-structure", "structure", "Fine Structure")
    if "ed" in which:
        serial("ed", "ed", "Ed (The Ed Stories)")
    if "stories" in which:
        stories(["vhitaos", "more", "nanowrimo", "older"], skip=set())
    if "antimemetics" in which:
        sh.log(url=BASE + "antimemetics", slug="antimemetics", title="There Is No Antimemetics Division", author=AUTHOR, year=2025, kind="novel", licence_or_basis=BASIS, status="declined:pulled for print publication; the page is a sales page")
