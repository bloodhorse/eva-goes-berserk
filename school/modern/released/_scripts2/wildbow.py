import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Shelf, get, paragraphs, join, norm
from bs4 import BeautifulSoup

AUTHOR = "Wildbow (John C. McCrae)"
BOOKS = {"pact": ("https://pactwebserial.wordpress.com/table-of-contents/", "Pact", 2013)}
NAV = re.compile(r"^(last chapter|next chapter|previous chapter|share this|like this|related|loading)\b", re.I)
sh = Shelf("wildbow")


def chapter(url):
    html = get(url)
    sh.raw_html(re.sub(r"[^A-Za-z0-9-]", "", url.rstrip("/").split("/")[-1]), html)
    s = BeautifulSoup(html, "lxml")
    h = s.select_one("h1.entry-title") or s.find("h1")
    c = s.select_one(".entry-content")
    for sel in ("script", "style", ".sharedaddy", "#jp-post-flair", ".jp-relatedposts", ".wpcnt", ".wp-block-buttons"):
        for x in c.select(sel):
            x.decompose()
    for a in c.find_all("a"):
        if NAV.match(a.get_text(" ", strip=True)):
            a.decompose()
    ps = [p for p in paragraphs(c) if not NAV.match(p) and not re.fullmatch(r"[\s|/]*|About|Table of Contents", p)]
    return norm(h.get_text(" ")) if h else url, ps


def book(slug, limit=None):
    toc, title, year = BOOKS[slug]
    th = get(toc)
    sh.raw_html(slug + "-toc", th)
    c = BeautifulSoup(th, "lxml").select_one(".entry-content")
    links = []
    for a in c.find_all("a", href=True):
        u = a["href"].split("#")[0]
        if not u.startswith("http"):
            u = "https://" + u.lstrip("/")
        if "?" in u or "table-of-contents" in u or u in links or not re.search(r"/\d{4}/\d\d/\d\d/", u):
            continue
        links.append(u)
    parts = []
    for u in links[:limit]:
        try:
            t, ps = chapter(u)
        except Exception as e:
            print("failed", u, e, flush=True)
            continue
        parts.append(t)
        parts += ps
        sh.beat()
    sh.write(slug, join(parts), url=toc, title=title, author=AUTHOR, year=year, kind="novel",
             licence_or_basis="web serial served free in full by the author on his own blog: " + toc)


if __name__ == "__main__":
    for b in sys.argv[1].split(","):
        if b not in sh.done:
            book(b, int(sys.argv[2]) if len(sys.argv) > 2 else None)
