import hashlib
import json
import os
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import settings
import planner
import reporter
import reviewer
import writer

NAMES = ["Mara", "Tobin", "Elsie", "Corwin", "Hattie", "Joss", "Petra", "Lowell"]
THINGS = ["the lantern", "a tin cup", "the ferry rope", "her coat", "the old radio", "a wet map", "the gate", "his boots"]
PLACES = ["the harbour", "the upper field", "the kitchen", "the signal tower", "the long road", "the cellar"]
VERBS = ["looked at", "turned toward", "walked past", "stood beside", "took hold of", "went back for"]
SPEECH = ["We should go before the tide turns", "I never asked you to stay", "Nobody told me the bridge was out",
          "You heard it too, then", "Leave it where it lies", "There is still bread in the tin"]


def narrative(seed, paragraphs=24, speech=0.35):
    rng = random.Random(seed)
    out = []
    for _ in range(paragraphs):
        a, b = rng.sample(NAMES, 2)
        if rng.random() < speech:
            out.append(f"“{rng.choice(SPEECH)},” {a} said. She {rng.choice(VERBS)} {rng.choice(THINGS)} and "
                       f"{b} nodded, and he was quiet for a while after that.")
        else:
            out.append(f"{a} {rng.choice(VERBS)} {rng.choice(THINGS)} in {rng.choice(PLACES)}. She had been there since "
                       f"morning and her hands were cold. {b} was late again, and when he came he sat down heavily "
                       f"and looked out over {rng.choice(PLACES)} as if he had lost something there. "
                       f"It was the third day and nothing had changed.")
    return out


def interview(seed, turns=10):
    rng = random.Random(seed)
    out = ["Jane Roe's fiction has appeared in many magazines and anthologies. Her debut novel was published in 2019 "
           "and was a finalist for several awards. We talked about writing, readers and her new collection of stories."]
    for i in range(turns):
        out.append(f"APEX MAGAZINE: Question {i}: how do you approach writing a short story when the characters and the "
                   f"plot of the book pull in different directions, and what do your readers and your editor say?")
        out.append(f"JANE ROE: For me the story begins with a character and a genre. I write a draft, then my editor reads "
                   f"it, and the novel or the stories change. Fiction is rewriting, and {rng.choice(['fantasy', 'horror'])} "
                   f"readers know that authors publish what the magazine will take.")
    return out


def review(seed, paragraphs=8):
    rng = random.Random(seed)
    out = []
    for i in range(paragraphs):
        out.append(f"The new collection from this author, published by a small press in 20{10 + i}, gathers twelve stories "
                   f"and a novella. As fiction it is uneven: the characters are thin, the plot of the title story is "
                   f"borrowed from an older novel, and the prose is plain. Readers of {rng.choice(['fantasy', 'horror'])} "
                   f"anthologies will know the themes. The editor's introduction and the author's essay are the best "
                   f"writing in the book, and the publisher has reprinted two award finalists.")
    return out


def poem(seed, stanzas=6):
    rng = random.Random(seed)
    out = []
    for _ in range(stanzas):
        lines = [f"{rng.choice(['salt', 'ash', 'rain', 'bone', 'light'])} on the {rng.choice(['sill', 'water', 'stair', 'field'])}"
                 for _ in range(4)]
        lines[1] = "and the long road going"
        out.append("\n".join(lines))
    return out


def prose_poem(seed, paragraphs=6):
    rng = random.Random(seed)
    return [f"The river keeps what it is given: {rng.choice(['a ring', 'a shoe', 'a name'])}, the last of the light, the sound "
            f"of a door closing in a house that is no longer there. Morning comes over the reeds like a rumour and "
            f"the herons stand in it, patient as fence posts, while the water goes on saying the one word it knows. "
            f"Nothing is asked of anyone. The boats are tied and the nets are dry and the sky is the colour of milk."
            for _ in range(paragraphs)]


def letters(seed, count=6):
    rng = random.Random(seed)
    out = []
    for i in range(count):
        a, b = rng.sample(NAMES, 2)
        out += [f"Dear {a},", f"I was on the night ferry when the engine stopped. The captain said nothing and he went below, "
                f"and we sat in the dark for an hour. A woman beside me had a bird in a cage and she talked to it the whole "
                f"time. When the lights came back her seat was empty and the cage was open. I looked for her on the quay "
                f"and she was not there.", f"Yours, {b}"]
    return out


def fake_interview(seed, turns=12):
    rng = random.Random(seed)
    out = ["TRANSCRIPT OF INTERVIEW 14", "Subject was found at the quarry on the third night."]
    for i in range(turns):
        out.append(f"DETECTIVE HALE: Tell me again what you saw when he opened the door and where she was standing.")
        out.append(f"WITNESS: He had the lantern in his hand. She was by the window and her face was white. I heard the "
                   f"dog and then he turned and looked at me and said nothing. I ran. I never saw her after that night.")
    return out


def text_of(parts):
    return "\n\n".join(parts) + "\n"


def tree_digest(root):
    digest = hashlib.sha256()
    for folder, subfolders, names in os.walk(root):
        subfolders[:] = sorted(d for d in subfolders if d != ".trash")
        for name in sorted(names):
            full = os.path.join(folder, name)
            digest.update(os.path.relpath(full, root).encode())
            with open(full, "rb") as f:
                digest.update(f.read())
    return digest.hexdigest()


class Tree(unittest.TestCase):
    sources = """
[[source]]
name = "mag"
path = "../src/mag"
kind = "incoming"
priority = 50
metadata = "../meta/mag"

[[source]]
name = "pod"
path = "../src/pod"
kind = "incoming"
priority = 40

[[source]]
name = "serial"
path = "../src/serial"
kind = "incoming"
priority = 30

[[source]]
name = "anth"
path = "../src/anth"
kind = "incoming"
priority = 10
container = true
ledger = "../src/anth/ledger.jsonl"

[[source]]
name = "shelf"
path = "../src/shelf"
kind = "read"
priority = 90
"""
    sieve = """
dedupe = "../dedupe/sources.toml"
jobs = 1
fiction_index = []

[profiles]
pod = "podcast"
serial = "serial"

[groups]
magazines = ["mag"]
podcasts = ["pod"]
anthologies = ["anth"]
serials = ["serial"]

[books.essay-book]
keep_essays = true
"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sieve-test-")).resolve()
        (self.root / "dedupe").mkdir()
        (self.root / "sieve").mkdir()
        real = HERE.parent / "dedupe" / "thresholds.toml"
        (self.root / "dedupe" / "sources.toml").write_text(f'thresholds = "{real}"\n' + self.sources, encoding="utf-8")
        (self.root / "sieve" / "sieve.toml").write_text(
            f'thresholds = "{HERE / "thresholds.toml"}"\n' + self.sieve, encoding="utf-8")
        for name in ("mag", "pod", "serial", "anth", "shelf"):
            (self.root / "src" / name).mkdir(parents=True)
            (self.root / "dedupe" / "out" / name).mkdir(parents=True)
        (self.root / "dedupe" / "state").mkdir()
        (self.root / "dedupe" / "state" / "plan.jsonl").write_text("{}\n", encoding="utf-8")
        self.said = []

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, source, name, parts, meta=None, raw=None):
        path = self.root / "dedupe" / "out" / source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = raw if raw is not None else text_of(parts).encode("utf-8")
        path.write_bytes(data)
        if meta is not None:
            folder = self.root / "meta" / source
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (Path(name).stem + ".json")).write_text(json.dumps(meta), encoding="utf-8")
        return path

    def ledger(self, records):
        (self.root / "src" / "anth" / "ledger.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

    def overrides(self, text):
        (self.root / "sieve" / "overrides.toml").write_text(text, encoding="utf-8")

    def cfg(self):
        return settings.Settings(self.root / "sieve" / "sieve.toml")

    def plan(self):
        cfg = self.cfg()
        planner.run(cfg, say=self.said.append)
        return {(r["source"], r["path"]): r for r in writer.load_plan(cfg)}

    def apply(self):
        return writer.run(self.cfg(), say=self.said.append)

    def out(self, kind, source, name):
        return (self.root / "sieve" / "out" / kind / source / name).read_text(encoding="utf-8")

    def reasons(self, record):
        return [c["reason"] for c in record["cuts"]]
