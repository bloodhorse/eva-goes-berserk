#!/usr/bin/env python3
"""cut.py — pot 2, forty first-person seeds cut by anchor from Project Gutenberg plain texts.

Each seed is the slice of a normalized source that starts at `start` and stops right before
`end`, trimmed of trailing whitespace. `end` is the text that follows the seam, so the seam is
located, never typed.

Sources: https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt, fetched into <source-dir> when
missing (first cut 2026-09-26).

Normalization, the same as the first-person pot's cut.py: CRLF to LF; editorial page markers
([ii.231]) and footnote marks ([B], [12]) dropped; asterisk dividers dropped; hard-wrapped lines
joined into paragraphs with a blank line between them; _underscore italics_ flattened. Spelling,
capitals and punctuation are the author's.

    python3 cut.py <source-dir>     # writes NN-slug.txt beside this file, prints count and tail
"""
import os
import re
import sys
import urllib.request

SRC = sys.argv[1] if len(sys.argv) > 1 else "."
HERE = os.path.dirname(os.path.abspath(__file__))

DIVIDER = re.compile(r"(?m)^[ \t]*(?:\*[ \t]+)+\*[ \t]*$")
PAGEMARK = re.compile(r"\[[ivxlc]+\.\d+\]")
FOOTMARK = re.compile(r"\[(?:[A-Z0-9]|\d+)\]")
ITALIC = re.compile(r"_([^_\n]+)_")

SEEDS = [
    (34120, "farthest-north", "Once during the morning I had had a narrow escape.", "find a crossing,"),
    (5199, "south", "I started to walk across the floe", "man and bag on to the floe"),
    (6137, "home-of-the-blizzard", "Ninnis, who was walking along", "my own sledge tracks running back"),
    (18985, "journey-to-the-polar-sea", "Whilst we were seated round the fire", "walk more than a few yards"),
    (61931, "whaleship-essex", "At about 11 o’clock at night, having laid down", "his jaws"),
    (20337, "bounty", "Just before sun-rising, Mr. Christian", "threats of instant death, if I did not"),
    (22792, "perils-and-captivity", "Towards seven in the morning, having fallen a little behind", "know whither I was going"),
    (17316, "letters-of-a-soldier", "On the 24th, in the evening, we returned", "moments of solitude that were full"),
    (18910, "nursing-sister", "Friday, October 16th, 2 P.M.", "them. It was not easy getting"),
    (7962, "over-the-top", "How I reached this hole I will never know.", "bleeding to death and was getting"),
    (60908, "diary-from-dixie", "I do not pretend to go to sleep.", "order the fort on one side"),
    (57389, "trial-of-jeanne", "I told her it seemed to me that peace", "I asked her often"),
    (15333, "nat-turner", "And from the first steps of righteousness", "the leaves in the woods"),
    (2276, "justified-sinner", "Immediately after this I was seized with a strange distemper", "this occasioned a confusion"),
    (44881, "confessions-of-a-thug", "So the old Thug sat still", "my own death would have followed"),
    (11962, "mind-that-found-itself", "Certain hallucinations of hearing", "had created the situation"),
    (59899, "ten-days-in-a-mad-house", "The water was ice-cold, and I again", "me, gasping, shivering"),
    (39585, "disappointed-man", "It is too inconceivably horrible to be buried", "cunningly working my reflexes"),
    (13332, "fifteen-years-in-hell", "Such music as then broke upon my senses", "a lion threw his claws"),
    (851, "rowlandson", "During my abode in this place, Philip spake", "invited my master and mistress"),
    (38010, "john-jewitt", "I was, however, soon recalled to my recollection", "the hatch of the steerage was shut"),
    (6960, "mary-jemison", "When the Indians had finished their supper they took", "our family by the color"),
    (71609, "andersonville-diary", "April 26.—Ten days since I wrote in my diary", "get to some house and get"),
    (2792, "my-prisons", "Being almost deprived of human society, I one day", "the insufferable oppression"),
    (43966, "ringcroft", "Then I came out with a resolution to leave the house", "me, I was struck several"),
    (64809, "an-adventure", "I was puzzling my way among the maze of paths", "faint music as of a band"),
    (10002, "house-on-the-borderland", "It was not Halloween.", "heard a faint, frightened whimper"),
    (23172, "the-damned-thing", "I watched again all of last night in the same cover", "notes that stir no chord"),
    (8486, "abbot-thomas", "Half aloud I counted the steps", "a good blow with my iron bar"),
    (14168, "benlian", "I ran to my landing and shouted down into the yard.", "a dying man had ever fought"),
    (593, "the-horla", "Having recovered my senses, I was thirsty again", "there are not two beings in us"),
    (23169, "the-diamond-lens", "What was it that afflicted the sylph?", "its last atom"),
    (37174, "dragon-volant", "In another moment I was placed, as he described", "given the order at"),
    (72971, "a-dead-mans-diary", "My mother, when I first saw her, was standing", "passed away with that wonder"),
    (14471, "a-haunted-island", "Meanwhile, by a sort of instinct, I stepped back", "an opportunity to land"),
    (294, "captain-of-the-polestar", "September 20th, evening.--I crossed the ice", "something in front of us"),
    (376, "plague-year", "His discourse had shocked my resolution a little", "used to pretend, as I have said"),
    (37311, "woolmans-journal", "About eleven at Night I went out on the Deck", "a strengthening Time"),
    (2440, "river-amazons", "On the night of the 22nd the moon appeared with a misty halo.", "save the vessel from being"),
    (32540, "first-summer-in-the-sierra", "August 2. Clouds and showers, about the same as yesterday.", "a side cañon, which"),
]


def fetch(gid):
    path = os.path.join(SRC, f"pg{gid}.txt")
    if not os.path.exists(path):
        url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
        with urllib.request.urlopen(url) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
    return path


def read(gid):
    with open(fetch(gid), encoding="utf-8-sig", newline="") as f:
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
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j].rstrip()


os.makedirs(SRC, exist_ok=True)
for n, (gid, slug, start, end) in enumerate(SEEDS, 1):
    text = cut(read(gid), start, end)
    with open(os.path.join(HERE, f"{n:02d}-{slug}.txt"), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"{n:02d} {slug:<28} {len(text.split()):>4}w  …{text[-50:]!r}")
