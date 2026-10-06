import gzip
import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://strangehorizons.com/wordpress/wp-json/wp/v2/posts"
FIELDS = "id,date,slug,link,title,content,categories,tags,author,excerpt"
KINDS = {"fiction": 1, "poetry": 2}
UA = "private-reading-shelf/1.0 (personal offline archive, not redistributed; python-requests)"
RAW = Path(__file__).resolve().parent / "raw"
DELAY = 1.1


class Refused(Exception):
    pass


def get(session, params):
    wait = 5
    for attempt in range(8):
        time.sleep(DELAY)
        try:
            r = session.get(BASE, params=params, timeout=90)
        except requests.RequestException as e:
            print(f"  network error {e!r}, sleeping {wait}s", flush=True)
            time.sleep(wait)
            wait = min(wait * 2, 300)
            continue
        if r.status_code == 200:
            return r
        if r.status_code == 400:
            return r
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("Retry-After")
            s = int(ra) if ra and ra.isdigit() else wait
            print(f"  HTTP {r.status_code}, sleeping {s}s", flush=True)
            time.sleep(s)
            wait = min(wait * 2, 300)
            continue
        raise Refused(f"HTTP {r.status_code} for {r.url}: {r.text[:200]}")
    raise Refused(f"gave up after retries: {params}")


def fetch_kind(session, kind, max_pages):
    cat = KINDS[kind]
    page = 1
    fetched = 0
    while True:
        out = RAW / f"{kind}-{page}.json.gz"
        if out.exists():
            page += 1
            continue
        if max_pages is not None and fetched >= max_pages:
            return
        params = {"categories": cat, "per_page": 100, "page": page, "_fields": FIELDS, "orderby": "id", "order": "asc"}
        r = get(session, params)
        if r.status_code == 400:
            print(f"{kind}: page {page} past the end, done", flush=True)
            return
        data = r.json()
        if not data:
            print(f"{kind}: page {page} empty, done", flush=True)
            return
        tmp = out.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        tmp.rename(out)
        total = r.headers.get("X-WP-TotalPages")
        print(f"{kind}: page {page}/{total} saved, {len(data)} posts", flush=True)
        fetched += 1
        if total and total.isdigit() and page >= int(total):
            return
        page += 1


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    kinds = [a for a in sys.argv[1:] if a in KINDS] or list(KINDS)
    max_pages = None
    for a in sys.argv[1:]:
        if a.startswith("--max="):
            max_pages = int(a.split("=", 1)[1])
    s = requests.Session()
    s.headers["User-Agent"] = UA
    try:
        for k in kinds:
            fetch_kind(s, k, max_pages)
    except Refused as e:
        print(f"STOPPED: {e}", flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
