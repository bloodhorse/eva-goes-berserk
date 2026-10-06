import json
import sys

from common import ROOT
from merge import OUT, merge
from minors import MINOR_CAST


def main():
    for shelf in sys.argv[1:] or ["souls", "wired", "anime"]:
        src = ROOT / f"{shelf}.jsonl"
        (OUT / shelf).mkdir(parents=True, exist_ok=True)
        dropped = 0
        with open(src, encoding="utf-8") as fh, open(OUT / shelf / "00000.jsonl", "w", encoding="utf-8") as out:
            for line in fh:
                r = json.loads(line)
                if r["explicit"] and MINOR_CAST.search(r["fandom"]):
                    dropped += 1
                    continue
                out.write(line)
        print(shelf, "dropped minor-cast explicit", dropped, flush=True)
        merge(shelf)


if __name__ == "__main__":
    main()
