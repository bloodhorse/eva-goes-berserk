import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Shelf, get, paragraphs, join, norm, words
from bs4 import BeautifulSoup

AUTHOR = "Rudy Rucker"
sh = Shelf("rucker")
CS = "https://www.rudyrucker.com/completestories/completestories.html"
PS = "https://www.rudyrucker.com/postsingular/cc_downloads/postsingular_rudy_rucker.htm"
SW = "https://www.rudyrucker.com/saucerwisdom/html"
KEEP = {"epubtext", "epubtext-noindent", "epubtext-centered", "epubtext-quote", "epubtext-poem"}
END = re.compile(r"^(Volume 2: Hylozoic|Acknowledg|About the Author|Afterword|Writing notes|Creative Commons|This work is licensed)", re.I)


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower().replace("’", "").replace("'", "")).strip("-")[:60]


def stories():
    html = get(CS)
    sh.raw_html("completestories", html)
    s = BeautifulSoup(html, "lxml")
    cur, text, year, notes = None, [], None, False
    out = []
    for p in s.find_all("p"):
        c = (p.get("class") or [""])[0]
        t = norm(p.get_text(" "))
        if c in ("h1-tight", "h2") and t and t != "Introduction":
            if cur:
                out.append((cur, text, year))
            cur, text, year, notes = t, [], None, False
        elif cur is None:
            continue
        elif c == "h3" and t.startswith("Note on"):
            notes = True
        elif c.startswith("epubtext-note") or notes:
            m = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", t)
            if m and year is None:
                year = int(m.group(1))
        elif c in KEEP and not notes and t and t != "§":
            text.append(t)
    if cur:
        out.append((cur, text, year))
    seen = set()
    for title, text, year in out:
        slug = slugify(title)
        while slug in seen:
            slug += "-2"
        seen.add(slug)
        if words(join(text)) < 150:
            sh.log(url=CS, slug=slug, title=title, author=AUTHOR, year=year, kind="story", licence_or_basis="free online browsing edition", status="declined:pointer stub, text lives elsewhere in the book")
            continue
        sh.write(slug, join(text), url=CS, title=title, author=AUTHOR, year=year, kind="story",
                 licence_or_basis="free online browsing edition served by the author on his own site (all rights reserved; private use only): " + CS)
        sh.beat()


def postsingular():
    html = get(PS)
    sh.raw_html("postsingular", html)
    s = BeautifulSoup(html, "lxml")
    started, out = False, []
    for el in s.find_all(["h1", "h2", "h3", "p"]):
        t = norm(el.get_text(" "))
        if not started:
            if el.name in ("h1", "h2") and t.upper() == "PART I" :
                started = True
                out.append(t)
            continue
        if END.match(t):
            break
        if t and t not in ("*", "* * *", "§"):
            out.append(t)
    idx = [i for i, t in enumerate(out) if t.upper() == "PART I"]
    out = [t for t in out[idx[-1]:] if not re.fullmatch(r"[=\-—_* ]+|—\s*The End\s*—", t)]
    out = [re.sub(r"^([B-HJ-Z]) ([a-z])", r"\1\2", t) for t in out]
    sh.write("postsingular", join(out), url=PS, title="Postsingular", author=AUTHOR, year=2007, kind="novel",
             licence_or_basis="CC BY-NC-ND, author's own free edition: https://www.rudyrucker.com/postsingular/cc_downloads")
    sh.beat()


if __name__ == "__main__":
    which = sys.argv[1:] or ["stories", "postsingular"]
    if "stories" in which:
        stories()
    if "postsingular" in which:
        postsingular()
    if "decline" in which:
        sh.log(url=SW, slug="saucer-wisdom", title="Saucer Wisdom", author=AUTHOR, year=1999, kind="novel",
               licence_or_basis="free browsing edition on author's site", status="declined:page is marked 'Free Browsing Edition, Not To Be Recopied'")
