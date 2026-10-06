import gzip, json, os, re, time
import requests

ROOT = "/Users/bekh/tower/forge/eva-goes-berserk/school/modern/released"
UA = "eva-shelf/1.0 (private corpus; one request at a time)"
_last = {}
_session = requests.Session()
_session.headers["User-Agent"] = UA


def get(url, delay=1.0):
    host = url.split("/")[2]
    wait = _last.get(host, 0) + delay - time.time()
    if wait > 0:
        time.sleep(wait)
    r = _session.get(url, timeout=60)
    _last[host] = time.time()
    r.raise_for_status()
    return r.content


def fetch_raw(slug, url, name, delay=1.0):
    d = os.path.join(ROOT, slug, "raw")
    os.makedirs(d, exist_ok=True)
    gz = name.endswith((".html", ".htm"))
    p = os.path.join(d, name + (".gz" if gz else ""))
    if os.path.exists(p):
        data = open(p, "rb").read()
        return gzip.decompress(data) if gz else data
    data = get(url, delay)
    with open(p, "wb") as f:
        f.write(gzip.compress(data) if gz else data)
    return data


def words(text):
    return len(re.findall(r"[A-Za-z']+", text))


def norm_paras(paras):
    out = []
    for p in paras:
        p = " ".join(p.replace("­", "").split())
        if p:
            out.append(p)
    return "\n\n".join(out) + "\n"


def write_text(slug, name, text):
    d = os.path.join(ROOT, slug, "text")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name + ".txt")
    open(p, "w", encoding="utf-8").write(text)
    return os.path.relpath(p, os.path.join(ROOT, slug))


def write_ledger(slug, rows):
    p = os.path.join(ROOT, slug, "ledger.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def row(url, slug, title, author, year, kind, text, file, basis, status="ok"):
    return {"url": url, "slug": slug, "title": title, "author": author, "year": year,
            "kind": kind, "words": words(text) if text else 0, "file": file,
            "licence_or_basis": basis, "status": status}
