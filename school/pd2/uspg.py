import csv, re, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    s = re.split(r"[:;]| -- | — |--", s)[0]
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"^(the|a|an) ", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()

def surname(a):
    a = unicodedata.normalize("NFKD", a).encode("ascii", "ignore").decode()
    if "," in a:
        return a.split(",")[0].strip().lower()
    parts = re.sub(r"\(.*?\)", "", a).split()
    return parts[-1].lower() if parts else ""

def load(path):
    idx = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Type"] != "Text" or r["Language"] != "en":
                continue
            t = norm(r["Title"].split("\n")[0])
            for a in r["Authors"].split(";"):
                sn = surname(a)
                if sn:
                    idx.setdefault(sn, []).append((t, r["Text#"]))
    return idx

def lookup(idx, author, title):
    sn = surname(author)
    t = norm(title)
    if not t:
        return None
    for ut, num in idx.get(sn, []):
        if ut == t or (len(t) > 12 and (ut.startswith(t) or t.startswith(ut) and len(ut) > 12)):
            return num
    return None

if __name__ == "__main__":
    idx = load(sys.argv[1])
    ac, tc = int(sys.argv[2]), int(sys.argv[3])
    for line in sys.stdin:
        f = line.rstrip("\n").split("\t")
        print(line.rstrip("\n") + "\t" + (lookup(idx, f[ac], f[tc]) or ""))
