import glob, json, os, re, sys
from multiprocessing import Pool

import pyarrow.parquet as pq

SRC, OUT = sys.argv[1], sys.argv[2]
S2 = re.compile(r"science fiction", re.I)
S1 = re.compile(r"fantasy|horror|gothic|ghost|supernatural|occult fiction|weird|mytholog|legends|sagas|epic poetry|arthur|knights|chivalry|romances", re.I)
A1 = re.compile(r"Dunsany|Morris, William, 1834|Eddison|Malory|Hodgson, William Hope|Machen|Blackwood, Algernon|Cabell|Smith, Clark Ashton|Howard, Robert E|Lovecraft|Beckford|Macpherson|Dasent|Magnússon|Schreiber, Charlotte|Spenser, Edmund", re.I)
DRY = re.compile(r"juvenile|children|history and criticism|study and teaching|bibliograph|dictionar|periodicals|indexes|textbooks|concordances|handbooks|encyclopedias", re.I)
NOTE = re.compile(r"^\s*(\[\d+\]|Produced by .*|Transcriber'?s? [Nn]ote.*|E-text prepared by .*)\s*$")
ILLUS = re.compile(r"\[Illustration[^\]]*\]", re.S)


def clean(text):
    lines = ILLUS.sub("", text.replace("\r\n", "\n").replace("\r", "\n")).split("\n")
    runs, blank, seen = [], 0, False
    for line in lines:
        if line.strip():
            if seen:
                runs.append(blank)
            blank, seen = 0, True
        else:
            blank += 1
    doubled = runs and sum(1 for r in runs if r == 1) > 0.6 * len(runs)
    gap = 2 if doubled else 1
    paras, cur, blank = [], [], 0
    for line in lines:
        s = line.strip()
        if not s:
            blank += 1
            continue
        if NOTE.match(line):
            continue
        if cur and blank >= gap:
            paras.append(" ".join(cur))
            cur = []
        blank = 0
        cur.append(re.sub(r"\s+", " ", s))
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras)


def shard(path):
    t = pq.read_table(path, columns=["TEXT", "METADATA"]).to_pydict()
    n = [0, 0, 0]
    b = [0, 0, 0]
    for text, meta in zip(t["TEXT"], t["METADATA"]):
        m = json.loads(meta)
        s = m.get("subjects") or ""
        a = m.get("authors") or ""
        if S2.search(s):
            k = 2
        elif (S1.search(s) or A1.search(a)) and not DRY.search(s):
            k = 1
        else:
            continue
        body = clean(text)
        if len(body) < 5000:
            continue
        with open(f"{OUT}/shelf{k}/{m.get('text_id')}.txt", "w") as f:
            f.write(body)
        n[k] += 1
        b[k] += len(body)
    return n, b


if __name__ == "__main__":
    for k in (1, 2):
        os.makedirs(f"{OUT}/shelf{k}", exist_ok=True)
    files = sorted(glob.glob(f"{SRC}/data/*.parquet"))
    tot_n, tot_b = [0, 0, 0], [0, 0, 0]
    with Pool(12) as p:
        for n, b in p.imap_unordered(shard, files):
            for k in (1, 2):
                tot_n[k] += n[k]
                tot_b[k] += b[k]
    for k in (1, 2):
        print(f"shelf{k}: {tot_n[k]} books, {tot_b[k] / 1e6:.0f} MB", flush=True)
    print("CUT-DONE", flush=True)
