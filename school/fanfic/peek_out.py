import json
import random
import sys
from pathlib import Path

ROOT = Path.home() / "eva-olmo" / "school" / "fanfic"
shelf = sys.argv[1]
n = int(sys.argv[2])
random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 0)
src = ROOT / f"{shelf}.jsonl" if (ROOT / f"{shelf}.jsonl").exists() else None
files = [src] if src else sorted((ROOT / "out" / shelf).glob("*.jsonl"))
rows = []
for f in files:
    with open(f, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if random.random() < 0.02 or len(rows) < n:
                rows.append(line)
for line in random.sample(rows, min(n, len(rows))):
    r = json.loads(line)
    t = r["text"]
    a = random.randint(0, max(0, len(t) - 1500))
    print("=" * 60, r["fandom"], "|", r["category"], "|", r["rating"], r["explicit"], r["words"], "tier", r["tier"])
    print(t[:700])
    print("[...]")
    print(t[a:a + 600])
    print("[... END]")
    print(t[-400:])
