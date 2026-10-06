import gzip, json, os, re, time, urllib.parse, urllib.robotparser
import requests
from bs4 import BeautifulSoup, NavigableString

ROOT = "/Users/bekh/tower/forge/eva-goes-berserk/school/modern/released"
UA = "eva-shelf/1.0 (private corpus; one request at a time)"
S = requests.Session()
S.headers["User-Agent"] = UA
_last = {}
_robots = {}


def allowed(url):
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = S.get(base + "/robots.txt", timeout=30)
            _last[p.netloc] = time.time()
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except Exception:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def get(url, binary=False):
    host = urllib.parse.urlsplit(url).netloc
    if not allowed(url):
        raise PermissionError("robots.txt disallows " + url)
    wait = 1.1 - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    r = S.get(url, timeout=60)
    _last[host] = time.time()
    r.raise_for_status()
    if binary:
        return r.content
    try:
        return r.content.decode("utf-8")
    except UnicodeDecodeError:
        return r.content.decode(r.apparent_encoding or "cp1252", errors="replace")


class Shelf:
    def __init__(self, slug):
        self.dir = os.path.join(ROOT, slug)
        for d in ("raw", "text"):
            os.makedirs(os.path.join(self.dir, d), exist_ok=True)
        self.ledger = os.path.join(self.dir, "ledger.jsonl")
        self.hb = os.path.join(self.dir, "heartbeat")
        self.count = 0
        self.done = set()
        if os.path.exists(self.ledger):
            for line in open(self.ledger):
                o = json.loads(line)
                if o["status"] == "ok":
                    self.done.add(o["slug"])

    def raw_html(self, name, html):
        p = os.path.join(self.dir, "raw", name + ".html.gz")
        with gzip.open(p, "wt", encoding="utf-8") as f:
            f.write(html)

    def raw_bytes(self, name, data):
        with open(os.path.join(self.dir, "raw", name), "wb") as f:
            f.write(data)

    def beat(self):
        self.count += 1
        with open(self.hb, "w") as f:
            f.write(f"{int(time.time())} {self.count}\n")

    def write(self, slug, text, **meta):
        rel = f"text/{slug}.txt"
        with open(os.path.join(self.dir, rel), "w") as f:
            f.write(text.strip() + "\n")
        self.log(slug=slug, file=rel, words=words(text), status="ok", **meta)

    def log(self, **o):
        o.setdefault("words", 0)
        o.setdefault("file", None)
        keys = ["url", "slug", "title", "author", "year", "kind", "words", "file", "licence_or_basis", "status"]
        rec = {k: o.get(k) for k in keys}
        with open(self.ledger, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def words(t):
    return len(re.findall(r"[A-Za-z']+", t))


def norm(s):
    s = s.replace(" ", " ").replace("\r", "")
    s = re.sub(r"[ \t\n]+", " ", s)
    return s.strip()


BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "pre", "blockquote", "div", "dd", "dt", "tr", "table", "ul", "ol", "dl", "center", "section", "article", "hr"}


def paragraphs(node):
    out, cur = [], []

    def flush():
        t = norm("".join(cur))
        if t:
            out.append(t)
        cur.clear()

    def walk(n):
        for c in n.children:
            if isinstance(c, NavigableString):
                if type(c).__name__ in ("Comment", "Doctype", "Declaration", "ProcessingInstruction"):
                    continue
                cur.append(str(c))
            elif c.name in ("script", "style", "noscript"):
                continue
            elif c.name == "br":
                flush()
            elif c.name == "pre":
                flush()
                for line in c.get_text().split("\n"):
                    if line.strip():
                        out.append(norm(line))
            elif c.name in BLOCKS:
                flush()
                walk(c)
                flush()
            else:
                walk(c)

    walk(node)
    flush()
    return out


def join(paras):
    return "\n\n".join(p for p in paras if p) + "\n"
