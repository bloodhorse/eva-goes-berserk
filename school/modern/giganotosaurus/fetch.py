import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
API = "https://giganotosaurus.org/wp-json/wp/v2/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
DELAY = 5.5
FICTION = 3
PER_PAGE = 20


def get(path, params):
    url = API + path + "?" + urllib.parse.urlencode(params)
    wait = 30
    for attempt in range(6):
        time.sleep(DELAY)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8")), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                return None, {}
            if e.code in (401, 403, 451):
                print(f"STOPPED: HTTP {e.code} for {url}", flush=True)
                sys.exit(2)
            print(f"  HTTP {e.code}, sleeping {wait}s", flush=True)
        except Exception as e:
            print(f"  {e!r}, sleeping {wait}s", flush=True)
        time.sleep(wait)
        wait = min(wait * 2, 300)
    print(f"STOPPED: gave up on {url}", flush=True)
    sys.exit(2)


def pages(path, name, params):
    page = 1
    while True:
        out = RAW / f"{name}-{page}.json.gz"
        if out.exists():
            page += 1
            continue
        data, headers = get(path, dict(params, per_page=PER_PAGE, page=page, orderby="id", order="asc"))
        if not data:
            print(f"{name}: page {page} past the end, done", flush=True)
            return
        tmp = out.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        tmp.rename(out)
        total = headers.get("x-wp-totalpages") or headers.get("X-WP-TotalPages")
        print(f"{name}: page {page}/{total} saved, {len(data)} items", flush=True)
        (RAW / "heartbeat").write_text(str(time.time()))
        if total and str(total).isdigit() and page >= int(total):
            return
        page += 1


def bylines():
    out = RAW / "pages"
    out.mkdir(exist_ok=True)
    for f in sorted(RAW.glob("fiction-*.json.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            posts = json.load(fh)
        for p in posts:
            tail = re.sub(r"<[^>]+>", " ", p["content"]["rendered"])[-400:]
            dest = out / f"{p['id']}.html"
            if re.search(r"(?i)copyright|©", tail) or dest.exists():
                continue
            time.sleep(DELAY)
            req = urllib.request.Request(p["link"], headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    dest.write_bytes(r.read())
                print(f"byline page {p['id']} {p['slug']}", flush=True)
            except Exception as e:
                print(f"byline page {p['id']} failed: {e!r}", flush=True)


def main():
    RAW.mkdir(exist_ok=True)
    pages("posts", "fiction", {"categories": FICTION})
    bylines()
    types, _ = get("taxonomies", {})
    (RAW / "taxonomies.json").write_text(json.dumps(types, ensure_ascii=False, indent=1), encoding="utf-8")
    for slug, t in (types or {}).items():
        if slug in ("category", "post_tag", "nav_menu", "wp_pattern_category"):
            continue
        base = t.get("rest_base") or slug
        pages(base, f"tax-{slug}", {"_fields": "id,name,slug,count,description"})
    print("done", flush=True)


if __name__ == "__main__":
    main()
