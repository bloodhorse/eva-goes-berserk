# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Opens the key on an instructed reader's picks.

    uv run --python 3.12 eva/scorer/score_picks.py eva/scorer/picks-A.json

The picks file is `{"<room>": ["<display id>", ...]}` as printed by `blind_view.py`.
This resolves the display ids, compares against bekh's marks, and prints precision,
recall and star catch per room and over the split. Run it only after the picks are
written down — it is the moment the blind comes off.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blind_view as BV  # noqa: E402
import features as F  # noqa: E402


def score(path: Path) -> None:
    picks = json.loads(path.read_text())
    split = picks.pop("_split", path.stem.rsplit("-", 1)[-1])
    rooms = BV.SPLITS[split]["test"]
    tot = {"picks": 0, "marks": 0, "hits": 0, "stars": 0, "star_hits": 0}
    print(f"# split {split} — instructed reader against bekh\n")
    print("| room | picks | his marks | hits | precision | recall | ★ caught |")
    print("|---|---|---|---|---|---|---|")
    for room in rooms:
        cs = BV.cards_of(room)
        chosen = set(picks.get(room, []))
        by_disp = {BV.display_id(split, c.room, c.node): c for c in cs}
        unknown = chosen - set(by_disp)
        if unknown:
            print(f"  !! unknown display ids in {room}: {sorted(unknown)}", file=sys.stderr)
        got = [by_disp[d] for d in chosen if d in by_disp]
        marks = [c for c in cs if c.marked]
        stars = [c for c in cs if c.true_star]
        hits = [c for c in got if c.marked]
        star_hits = [c for c in got if c.true_star]
        star_cell = (f"{len(star_hits)}/{len(stars)}"
                     if cs and cs[0].star_room and stars else "—")
        print(f"| `{room}` | {len(got)} | {len(marks)} | {len(hits)} | "
              f"{len(hits)/len(got):.0%} | {len(hits)/len(marks):.0%} | {star_cell} |"
              if got and marks else f"| `{room}` | {len(got)} | {len(marks)} | — | — | — | — |")
        tot["picks"] += len(got); tot["marks"] += len(marks); tot["hits"] += len(hits)
        if cs and cs[0].star_room:
            tot["stars"] += len(stars); tot["star_hits"] += len(star_hits)
    p = tot["hits"] / tot["picks"] if tot["picks"] else 0
    r = tot["hits"] / tot["marks"] if tot["marks"] else 0
    sr = f"{tot['star_hits']}/{tot['stars']} ({tot['star_hits']/tot['stars']:.0%})" if tot["stars"] else "—"
    base = tot["marks"] / sum(len(BV.cards_of(x)) for x in rooms)
    print(f"| **split {split}** | {tot['picks']} | {tot['marks']} | {tot['hits']} | "
          f"**{p:.0%}** | **{r:.0%}** | {sr} |")
    print(f"\nChance for this split (its base rate): {base:.0%}.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("picks", nargs="+", type=Path)
    a = ap.parse_args()
    for p in a.picks:
        score(p)
        print()


if __name__ == "__main__":
    main()
