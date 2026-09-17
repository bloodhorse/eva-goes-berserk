# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""The instructed reader's only window onto the cards.

Prints one split: the five training rooms with every card and bekh's marks on it,
then the five test rooms with every card **shuffled, unmarked, and with the model
names stripped**. A reader doing that part of the experiment reads this output and
nothing else — opening the test rooms' json is the whole cheat.

Cards in the test half carry an opaque display id, not their node id, so a pick
cannot be resolved back to a card by hand; `score_picks.py` holds the key.

    uv run --python 3.12 eva/scorer/blind_view.py --split A
    uv run --python 3.12 eva/scorer/blind_view.py --split A --half test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402

BASE = "experiments/three-models"

# Two splits, swapped. Each half mixes found documents (green book, madman, Scott,
# blue boar) with rooms seeded by nemo's own lines, so neither half is all of one
# kind — the models behave differently on the two, and a portrait written on found
# documents alone would be a portrait of Gogol.
SPLITS = {
    "A": {
        "train": ["07-the-green-book", "10-madmans-diary", "07-all-ive-got-are-names",
                  "18-what-is-that-hum", "22-you-it-said"],
        "test": ["11-scotts-diary", "12-blue-boar", "13-a-dreamer-to-a-reader",
                 "15-it-keeps-talking-back", "24-what-has-this-to-do-with-you"],
    },
}
SPLITS["B"] = {"train": SPLITS["A"]["test"], "test": SPLITS["A"]["train"]}


def display_id(split: str, room: str, node: str) -> str:
    return hashlib.sha1(f"{split}|{room}|{node}".encode()).hexdigest()[:6]


def cards_of(room: str) -> list[F.Card]:
    return F.load_rooms([f"{BASE}/{room}"])


def show(split: str, half: str) -> None:
    rooms = SPLITS[split][half]
    print(f"# split {split} — {half} rooms\n")
    if half == "train":
        print("Every card, with bekh's marks. `★` = it made him feel something; "
              "`●` = he liked it.\n")
    else:
        print("Every card, shuffled, unmarked, model names stripped. Pick about 8 of "
              "the 30 in each room.\n")
    for room in rooms:
        cs = cards_of(room)
        seed = cs[0].seed if cs else ""
        print(f"\n{'=' * 78}\n## {room}   ({len(cs)} cards)\n{'=' * 78}\n")
        print("SEED (the document every card continues):")
        print("\n".join("    " + l for l in seed.strip().splitlines()))
        print()
        if half == "train":
            n_star = sum(c.true_star for c in cs)
            n_mark = sum(c.marked for c in cs)
            era = "" if cs[0].star_room else "   [★ here means 'marked' — ● did not exist yet]"
            print(f"-- {n_mark} marked, {n_star} true ★{era}\n")
            for c in cs:
                mark = "★" if c.true_star else ("●" if c.marked else " ")
                print(f"[{mark}] {c.node}  ({c.model}, t={c.temperature})")
                print(f"     {c.text.strip()!r}\n")
        else:
            order = list(cs)
            random.Random(f"{split}|{room}").shuffle(order)
            for c in order:
                print(f"[{display_id(split, c.room, c.node)}]")
                print(f"     {c.text.strip()!r}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=sorted(SPLITS), default="A")
    ap.add_argument("--half", choices=("train", "test", "both"), default="both")
    ap.add_argument("--rooms", action="store_true", help="just list the split")
    a = ap.parse_args()
    if a.rooms:
        print(json.dumps(SPLITS[a.split], indent=1))
        return
    for half in (("train", "test") if a.half == "both" else (a.half,)):
        show(a.split, half)


if __name__ == "__main__":
    main()
