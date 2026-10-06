import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Shelf, get, paragraphs, join, norm
from bs4 import BeautifulSoup

AUTHOR = "Scott Alexander"
HOME = "http://unsongbook.com/"
sh = Shelf("alexander")
NAV = re.compile(r"^(next|previous|prev|«|»|←|→|share this|like this|related)\b", re.I)
PART = re.compile(r"^(prologue|chapter|interlude|epilogue|book)", re.I)


def content(s):
    c = s.select_one(".pjgm-postcontent") or s.select_one(".entry-content") or s.select_one("article")
    for sel in ("script", "style", ".sharedaddy", "#jp-post-flair", ".jp-relatedposts", ".wp-block-buttons", "nav"):
        for x in c.select(sel):
            x.decompose()
    return c


def main(limit=None):
    home = get(HOME)
    sh.raw_html("index", home)
    hs = BeautifulSoup(home, "lxml")
    order = []
    for a in hs.find_all("a", href=True):
        h = a["href"].replace("https://", "http://")
        if h.lower().startswith(HOME):
            tail = h[len(HOME):]
            if PART.match(tail) and tail not in order:
                order.append(tail)
    parts = []
    for i, tail in enumerate(order[:limit]):
        html = get(HOME + tail)
        name = re.sub(r"[^A-Za-z0-9-]", "", tail.strip("/"))[:60] or f"p{i}"
        sh.raw_html(f"{i:03d}-{name}", html)
        s = BeautifulSoup(html, "lxml")
        h = s.select_one(".pjgm-posttitle") or s.select_one("h1.entry-title") or s.find("h1")
        title = norm(h.get_text(" ")) if h else tail
        parts.append(title)
        parts += [p for p in paragraphs(content(s)) if not NAV.match(p) and not re.fullmatch(r"\[.*author.?s note.*\]", p, re.I)]
        sh.beat()
    sh.write("unsong", join(parts), url=HOME, title="Unsong", author=AUTHOR, year=2017, kind="novel",
             licence_or_basis="served free in full by the author on the book's own site: " + HOME)


def ssc(limit=None):
    from common import words
    tag, posts, n = "https://slatestarcodex.com/tag/fiction/", [], 1
    while True:
        html = get(tag if n == 1 else f"{tag}page/{n}/")
        s = BeautifulSoup(html, "lxml")
        new = [a["href"] for h in s.select(".pjgm-posttitle") for a in h.find_all("a", href=True)]
        posts += [u for u in new if u not in posts]
        if not s.find("a", href=f"{tag}page/{n + 1}/"):
            break
        n += 1
    for u in posts[:limit]:
        slug = "ssc-" + u.rstrip("/").split("/")[-1][:60]
        if slug in sh.done:
            continue
        html = get(u)
        sh.raw_html(slug, html)
        s = BeautifulSoup(html, "lxml")
        h = s.select_one(".pjgm-posttitle")
        title = norm(h.get_text(" ")) if h else slug
        y = re.search(r"/(\d{4})/\d\d/", u)
        ps = [p for p in paragraphs(content(s)) if not NAV.match(p) and not re.match(r"^\[?(epistemic status|content warning|\[?this is fiction)", p, re.I)]
        while ps and ps[0].startswith("[") and ps[0].endswith("]"):
            ps = ps[1:]
        text = join(ps)
        meta = dict(url=u, slug=slug, title=title, author=AUTHOR, year=int(y.group(1)) if y else None, kind="story",
                    licence_or_basis="served free by the author on his own blog, fiction tag: " + tag)
        if words(text) < 300:
            sh.log(status="declined:under 300 words", words=words(text), **meta)
        else:
            sh.write(text=text, **{k: v for k, v in meta.items()})
        sh.beat()


if __name__ == "__main__":
    if sys.argv[1:2] == ["ssc"]:
        ssc(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
