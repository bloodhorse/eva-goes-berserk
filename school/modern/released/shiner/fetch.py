import json
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
BASE = "https://fictionliberationfront.net/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
DELAY = 10.5
SECTIONS = {"Novels": "novel", "Short Fiction": "story", "Non-fiction": "nonfiction", "Screenplays": "screenplay",
            "Audio": "audio", "Video": "video", "Translations": "translation", "Interviews": "interview"}


class Index(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section = None
        self.in_h2 = False
        self.h2 = []
        self.rows = []
        self.cell = None
        self.cells = []
        self.in_tr = False
        self.href = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "br":
            self.handle_data(" ")
        elif tag == "h2":
            self.in_h2 = True
            self.h2 = []
        elif tag == "tr":
            self.in_tr = True
            self.cells = []
        elif tag == "td" and self.in_tr:
            self.cell = {"text": [], "links": []}
        elif tag == "a" and self.cell is not None and a.get("href"):
            self.href = a["href"]
            self.cell["links"].append([a["href"], ""])

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_h2 = False
            name = re.sub(r"\s+", " ", "".join(self.h2)).strip()
            self.section = SECTIONS.get(name, name)
        elif tag == "td" and self.cell is not None:
            self.cells.append(self.cell)
            self.cell = None
        elif tag == "a":
            self.href = None
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            if self.cells and self.section:
                self.rows.append((self.section, self.cells))

    def handle_data(self, data):
        if self.in_h2:
            self.h2.append(data)
        if self.cell is not None:
            self.cell["text"].append(data)
            if self.href and self.cell["links"]:
                self.cell["links"][-1][1] += data


def ws(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def catalogue():
    p = Index()
    p.feed((RAW / "index.html").read_text(encoding="utf-8", errors="replace"))
    works = []
    for section, cells in p.rows:
        links = [(h, ws(t)) for c in cells for h, t in c["links"]]
        formats = {t.upper(): h for h, t in links if t.upper() in ("HTML", "PDF")}
        if not formats:
            continue
        texts = [ws("".join(c["text"])) for c in cells]
        texts = [t for t in texts if t and t.upper() not in ("HTML", "PDF", "INFO", "•")]
        title = re.sub(r"\s*\*+$", "", texts[0]).strip() if texts else ""
        title = re.sub(r"^•\s*", "", title)
        blurb = texts[-1] if len(texts) > 1 else ""
        works.append({"section": section, "title": title, "blurb": blurb,
                      "html": formats.get("HTML"), "pdf": formats.get("PDF")})
    return works


def get(url, out):
    if out.exists() and out.stat().st_size > 0:
        return "have"
    wait = 30
    for attempt in range(5):
        time.sleep(DELAY)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            tmp = out.with_suffix(out.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.rename(out)
            return f"{len(data)} bytes"
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 451):
                print(f"STOPPED: HTTP {e.code} for {url}", flush=True)
                sys.exit(2)
            if e.code == 404:
                return "404"
            print(f"  HTTP {e.code}, sleeping {wait}s", flush=True)
        except Exception as e:
            print(f"  {e!r}, sleeping {wait}s", flush=True)
        time.sleep(wait)
        wait *= 2
    return "failed"


def main():
    RAW.mkdir(exist_ok=True)
    if not (RAW / "index.html").exists():
        get(BASE, RAW / "index.html")
    get(BASE + "manifesto.html", RAW / "manifesto.html")
    works = catalogue()
    (ROOT / "catalogue.json").write_text(json.dumps(works, ensure_ascii=False, indent=1), encoding="utf-8")
    for w in works:
        if w["section"] not in ("novel", "story"):
            continue
        want = []
        if w["section"] == "novel":
            want = [w["pdf"]]
        elif w["html"] and not w["html"].startswith("http"):
            want = [w["html"]]
        elif w["pdf"] and not w["pdf"].startswith("http"):
            want = [w["pdf"]]
        for name in want:
            if not name or name.startswith("http"):
                continue
            print(f"{w['title']}: {name}: {get(BASE + name, RAW / name)}", flush=True)
        (RAW / "heartbeat").write_text(str(time.time()))
    print("done", flush=True)


if __name__ == "__main__":
    main()
