#!/usr/bin/env python3
"""cut.py — the first-person seeds, cut by anchor from fetched sources. Provenance, not an
instrument: it says exactly which slice of which page each seed is, so nobody retyped anything.

Every seed is an `i` already inside a situation, mid-thought, with nothing asked of it: a diary
page, a ship's journal, a deposition, a letter, a dream written down on waking. Third-person
documents get reported on; an author talking about a text gets an author's note; a slot gets a
category. So the last words of a cut are never a question and never a slot — the sentence is
underway, and the next words are the `i` continuing.

Sources (fetched 2026-09-17 into a scratch dir, plain-text Gutenberg mirrors):
    gutenberg.org/cache/epub/<id>/pg<id>.txt

      1952 The Yellow Wall Paper            ·  2147 Works of Poe, vol 1
     68553 The festival (Lovecraft)         ·   345 Dracula
     10007 Carmilla                         · 11438 The Willows
     25016 The House of Souls (Machen)      ·  8492 The King in Yellow
      2040 Confessions of an Opium-Eater    · 36238 The Mantle, and Other Stories (Gogol)
     11579 Scott's Last Expedition, vol 1   · 17845 Salem Witchcraft (Upham)

Normalization, applied to the whole source before slicing so that anchors never straddle a line
break: CRLF to LF; editorial page markers ([ii.231]) and single-letter footnote marks ([B])
dropped; asterisk dividers dropped; hard-wrapped lines joined into paragraphs with a blank line
between them; _underscore italics_ flattened to plain text. The author's capitals, spelling and
punctuation are left exactly as they are — including the 1692 spelling in seed 12.

    python3 cut.py <source-dir>     # writes NN-name.txt beside this file, prints each tail
"""
import os
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "."
HERE = os.path.dirname(os.path.abspath(__file__))

DIVIDER = re.compile(r"(?m)^[ \t]*(?:\*[ \t]+)+\*[ \t]*$")
PAGEMARK = re.compile(r"\[[ivxlc]+\.\d+\]")
FOOTMARK = re.compile(r"\[[A-Z0-9]\]")
ITALIC = re.compile(r"_([^_\n]+)_")


def read(stem):
    """The source, normalized: paragraphs on one line each, blank line between."""
    with open(os.path.join(SRC, stem + ".txt"), encoding="utf-8", newline="") as f:
        t = f.read()
    t = t.replace("\r\n", "\n")
    t = PAGEMARK.sub("", t)
    t = FOOTMARK.sub("", t)
    t = DIVIDER.sub("", t)
    paras, cur = [], []
    for line in t.split("\n"):
        line = line.strip()
        if line:
            cur.append(line)
        elif cur:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return ITALIC.sub(r"\1", "\n\n".join(paras))


def cut(text, start, end):
    """From `start` up to (not including) `end`, trimmed to the last whole word. `end` is the
    text that follows the seam, so the seam itself is never typed here — only located."""
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j].rstrip().rstrip('"')


seeds = []

# 01 — Charlotte Perkins Gilman, "The Yellow Wall Paper", 1892. The narrator alone in the
# nursery, cataloguing the smell of the paper and the woman she has begun to see outdoors.
seeds.append(("yellow-wallpaper", cut(
    read("g1952"),
    "But there is something else about that paper—the smell!",
    "suspect something at once.")))

# 02 — Edgar Allan Poe, "MS. Found in a Bottle", 1833. Stowed away in the hold of a ship whose
# crew cannot see him, keeping the journal he means to throw into the sea.
seeds.append(("ms-found-in-a-bottle", cut(
    read("g2147"),
    "I had scarcely completed my work, when a footstep in the hold",
    "stood in the very midst of them all")))

# 03 — H. P. Lovecraft, "The Festival", 1925. Walking down into Kingsport at dusk, on the
# night his family's legend told him to come back.
seeds.append(("the-festival", cut(
    read("g68553"),
    "Then beyond the hill’s crest I saw Kingsport outspread frostily",
    "windows without drawn curtains.")))

# 04 — Bram Stoker, "Dracula", 1897. Jonathan Harker's shorthand journal, the night he watches
# the Count go down the castle wall and then goes looking for a way out.
seeds.append(("harkers-journal", cut(
    read("g345"),
    "What I saw was the Count’s head coming out from the window.",
    "enter. I was now in a wing of the castle")))

# 05 — Sheridan Le Fanu, "Carmilla", 1872. Laura's account of the night the black animal came
# round the foot of her locked bed.
seeds.append(("carmilla", cut(
    read("g10007"),
    "The precautions of nervous people are infectious,",
    "horrified. I sprang into my bed")))

# 06 — Algernon Blackwood, "The Willows", 1907. Awake past midnight on a sand island in the
# Danube, crawling out of the tent to look at the shapes rising out of the bushes.
seeds.append(("the-willows", cut(
    read("g11438"),
    "Suddenly I found myself lying awake, peering from my sandy mattress",
    "stood upright. I felt the ground still warm")))

# 07 — Arthur Machen, "The White People" (in The House of Souls), 1906. The Green Book: a girl
# writing down, in her own secret book, the walk she took on the White Day.
seeds.append(("the-green-book", cut(
    read("g25016"),
    "I was thirteen, nearly fourteen, when I had a very singular adventure,",
    "killed. But I wanted to get up to the very top")))

# 08 — Robert W. Chambers, "The Repairer of Reputations" (in The King in Yellow), 1895. Hildred
# Castaigne comes home, opens the time lock, takes out the diadem, and looks at the square.
seeds.append(("the-diadem", cut(
    read("g8492"),
    "Passing Hawberk’s door again I saw him still at work on the armour,",
    "dinner. As I crossed the central driveway")))

# 09 — Thomas De Quincey, "Confessions of an English Opium-Eater", 1821. The water dreams, and
# the night the faces begin to come up out of the sea.
seeds.append(("opium-dreams", cut(
    read("g2040"),
    "To my architecture succeeded dreams of lakes and silvery expanses",
    "mad. The causes of my horror lie deep")))

# 10 — Nikolai Gogol, "Memoirs of a Madman", 1835 (Claud Field's 1916 translation). The clerk's
# diary after the dates come apart: he is the King of Spain and the moon is in danger.
seeds.append(("madmans-diary", cut(
    read("g36238"),
    "No date. The day had no date.--I went for a walk incognito",
    "prevent the earth sitting on the moon.")))

# 11 — Robert Falcon Scott, sledging diary, March 1912 (Scott's Last Expedition, vol 1). Eleven
# miles a day from One Ton Depot, writing at lunch because the cold allows nothing else.
seeds.append(("scotts-diary", cut(
    read("g11579"),
    "Wednesday, March 14.--No doubt about the going downhill",
    "know it. A very small measure of neglect")))

# 12 — Salem, 9 September 1692: three depositions against Mary Bradbury, printed verbatim in
# Charles Upham's "Salem Witchcraft" (1867). Two boys on a horse saw a blue boar; James Carr
# was held down in his bed. Spelling as sworn.
upham = read("g17845")
seeds.append(("blue-boar", "\n\n".join([
    cut(upham, "The Deposition of Richard Carr, who testifieth and saith,", "\n\n"),
    cut(upham, "Zerubabel Endicott testifieth and saith,", "\n\n"),
    cut(upham, "The Deposistion of James Carr.", "mis Bradbery the prisoner att the barr"),
])))


for n, (name, text) in enumerate(seeds, 1):
    path = os.path.join(HERE, f"{n:02d}-{name}.txt")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    words = len(text.split())
    print(f"{n:02d} {name:<21} {words:>4}w  …{text[-58:]!r}")
