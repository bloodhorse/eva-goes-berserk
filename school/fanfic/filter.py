import collections
import hashlib
import json
import sys
import time

import pyarrow.parquet as pq

from aggregate import split_category
from clean import WORD, clean, quality, rating_of
from common import ROOT, cleanup, download, key
from minors import sexual, verdict

OUT = ROOT / "out"
STATS = ROOT / "stats"
CAP = 3 * 1024**3
MAPPING = json.loads((ROOT / "mapping.json").read_text())
FRACTIONS = json.loads((ROOT / "fractions.json").read_text())


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def shelf_bytes(shelf):
    d = OUT / shelf
    return sum(f.stat().st_size for f in d.glob("*.jsonl")) if d.exists() else 0


def sample_keep(text, frac):
    if frac >= 1:
        return True
    h = int(hashlib.sha1(text[:4000].encode("utf-8", "ignore")).hexdigest()[:8], 16)
    return h / 0xFFFFFFFF < frac


def process(name):
    k = key(name)
    done = STATS / f"{k}.json"
    if done.exists():
        return
    full = {s: shelf_bytes(s) >= CAP for s in ("souls", "wired", "anime")}
    d, p = download(name, log)
    t = pq.read_table(p, columns=["TEXT", "CATEGORY", "language"])
    st = collections.defaultdict(collections.Counter)
    writers = {}
    try:
        for raw, cat, lang in zip(*(t.column(c).to_pylist() for c in t.column_names)):
            st["all"]["rows"] += 1
            if lang != "en":
                st["all"]["not_en"] += 1
                continue
            fandom, genres = split_category(cat)
            m = MAPPING.get(fandom)
            if not m:
                st["all"]["unmapped"] += 1
                continue
            shelf, label = m["shelf"], m["label"]
            sk = f"{shelf}|{label}"
            c = st[sk]
            c["seen"] += 1
            if full[shelf]:
                c["shelf_full"] += 1
                continue
            if not raw:
                c["empty"] += 1
                continue
            if not sample_keep(raw, FRACTIONS.get(sk, 1.0)):
                c["sampled_out"] += 1
                continue
            v = verdict(raw, label, m.get("minor", False))
            if v:
                c["minors_" + v] += 1
                c["minors_words"] += len(raw.split())
                continue
            text, paras, cs = clean(raw)
            words = len(WORD.findall(text))
            q = quality(paras, words)
            if q:
                for r in q:
                    c["q_" + r] += 1
                continue
            row = {
                "fandom": label,
                "category": cat,
                "rating": rating_of(raw),
                "explicit": sexual(raw),
                "words": words,
                "tier": m.get("tier", 1),
                "text": text,
            }
            if shelf not in writers:
                (OUT / shelf).mkdir(parents=True, exist_ok=True)
                writers[shelf] = open(OUT / shelf / f"{k}.part", "w", encoding="utf-8")
            writers[shelf].write(json.dumps(row, ensure_ascii=False) + "\n")
            c["kept"] += 1
            c["words"] += words
            c["an_paras"] += cs["an"]
            c["rating_" + row["rating"]] += 1
            if row["explicit"]:
                c["explicit"] += 1
    finally:
        for w in writers.values():
            w.close()
    for shelf in writers:
        (OUT / shelf / f"{k}.part").rename(OUT / shelf / f"{k}.jsonl")
    STATS.mkdir(exist_ok=True)
    tmp = done.with_suffix(".part")
    tmp.write_text(json.dumps(st))
    tmp.rename(done)
    cleanup(d)
    kept = sum(v["kept"] for v in st.values())
    log(f"done {k} rows {t.num_rows} kept {kept}")


def main():
    for name in sys.argv[1:]:
        try:
            process(name)
        except Exception as e:
            log(f"FAILED {name}: {e!r}")


if __name__ == "__main__":
    main()
