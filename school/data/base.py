import glob, json, os, random, re, sys
from multiprocessing import Pool

import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cut

SRC, OUT, CAP = sys.argv[1], sys.argv[2], float(sys.argv[3]) * 1e6
FIC = re.compile(r"fiction|stories|tales|novel", re.I)
NOT = re.compile(r"juvenile|children|history and criticism|study and teaching|bibliograph|dictionar|periodicals|textbooks|readers|essays|poetry|drama|plays", re.I)


def shard(path):
    t = pq.read_table(path, columns=["TEXT", "METADATA"]).to_pydict()
    rng = random.Random(path)
    kept = []
    for text, meta in zip(t["TEXT"], t["METADATA"]):
        m = json.loads(meta)
        s = m.get("subjects") or ""
        if not FIC.search(s) or NOT.search(s) or cut.S2.search(s) or cut.S1.search(s) or cut.A1.search(m.get("authors") or ""):
            continue
        if rng.random() > 0.35:
            continue
        body = cut.clean(text)
        if len(body) < 20000:
            continue
        kept.append((m.get("text_id"), body))
    return kept


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    total = 0
    with Pool(12) as p:
        for kept in p.imap_unordered(shard, sorted(glob.glob(f"{SRC}/data/*.parquet"))):
            for tid, body in kept:
                if total >= CAP:
                    break
                open(f"{OUT}/{tid}.txt", "w").write(body)
                total += len(body)
    print(f"base: {len(os.listdir(OUT))} books, {total / 1e6:.0f} MB", flush=True)
    print("BASE-DONE", flush=True)
