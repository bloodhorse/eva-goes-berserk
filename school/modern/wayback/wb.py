import fcntl
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = "private-reading-shelf/1.0 (personal offline archive, not redistributed; python-urllib)"
DELAY = 4.0
BACKOFF = 60
GATE = HERE / ".gate"
CDX = "https://web.archive.org/cdx/search/cdx"
OFFLINE = b"Internet Archive: Temporarily Offline"


class Gone(Exception):
    pass


def _serial(fn):
    GATE.touch(exist_ok=True)
    with open(GATE, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            raw = f.read().strip()
            last = float(raw) if raw else 0.0
            now = time.time()
            if now - last < DELAY:
                time.sleep(DELAY - (now - last))
            try:
                return fn()
            finally:
                f.seek(0)
                f.truncate()
                f.write(str(time.time()))
                f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _once(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read(), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, b"", url
    except Exception as e:
        return -1, repr(e).encode(), url


def get(url, tries=8, log=print):
    for attempt in range(tries):
        status, body, final = _serial(lambda: _once(url))
        if status == 200 and OFFLINE in body[:400]:
            log(f"  offline notice for {url}, sleeping {BACKOFF}s")
        elif status == -1:
            log(f"  network error {body[:200]!r} for {url}, sleeping {BACKOFF}s")
        elif status == 429 or status >= 500:
            log(f"  HTTP {status} for {url}, sleeping {BACKOFF}s")
        else:
            return status, body, final
        time.sleep(BACKOFF)
    raise Gone(f"gave up after {tries} tries: {url}")


def cdx(url, html_only=True, ok_only=True, collapse="urlkey", extra=None, log=print):
    q = [("url", url), ("output", "json")]
    if ok_only:
        q.append(("filter", "statuscode:200"))
    if html_only:
        q.append(("filter", "mimetype:text/html"))
    if collapse:
        q.append(("collapse", collapse))
    for k, v in (extra or []):
        q.append((k, v))
    status, body, _ = get(CDX + "?" + urllib.parse.urlencode(q), log=log)
    if status != 200 or not body.strip():
        return []
    rows = json.loads(body)
    if not rows:
        return []
    head = rows[0]
    return [dict(zip(head, r)) for r in rows[1:]]


def snap_url(ts, url):
    return f"https://web.archive.org/web/{ts}id_/{url}"


def safe_name(ts, url):
    u = re.sub(r"^https?://", "", url)
    u = re.sub(r"[^A-Za-z0-9._-]+", "_", u).strip("_")
    return f"{ts}_{u[:150]}"


def heartbeat(folder, count, total=None, note=""):
    d = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "epoch": int(time.time()), "count": count}
    if total is not None:
        d["total"] = total
    if note:
        d["note"] = note
    (Path(folder) / "heartbeat").write_text(json.dumps(d) + "\n")


def decode(b):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", errors="replace")


def fetch_all(folder, rows, log=print):
    folder = Path(folder)
    raw = folder / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest = folder / "raw.jsonl"
    done = {}
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            d = json.loads(line)
            done[d["urlkey"]] = d
    total = len(rows)
    n = 0
    with open(manifest, "a") as mf:
        for r in rows:
            n += 1
            key = r["urlkey"]
            if key in done and (done[key]["status"] != 200 or (raw / done[key]["file"]).exists()):
                continue
            name = safe_name(r["timestamp"], r["original"]) + ".html"
            status, body, final = get(snap_url(r["timestamp"], r["original"]), log=log)
            m = re.search(r"/web/(\d{14})", final)
            rec = {"urlkey": key, "original": r["original"], "timestamp": r["timestamp"],
                   "served_timestamp": m.group(1) if m else r["timestamp"], "status": status,
                   "bytes": len(body), "file": name if status == 200 else ""}
            if status == 200:
                tmp = raw / (name + ".tmp")
                tmp.write_bytes(body)
                tmp.rename(raw / name)
            mf.write(json.dumps(rec) + "\n")
            mf.flush()
            done[key] = rec
            heartbeat(folder, n, total, r["original"])
            if n % 25 == 0:
                log(f"{folder.name}: {n}/{total}")
    heartbeat(folder, n, total, "done")
    log(f"{folder.name}: done, {total} rows")
