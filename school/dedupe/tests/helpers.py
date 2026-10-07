import hashlib
import io
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

import lookup
import materialise
import plan
import report
import scan
from config import Config

SYLLABLES = ["ka", "lo", "mi", "ren", "tu", "shi", "vor", "an", "del", "qua", "est", "ium", "bra", "ol", "fen",
             "gar", "hu", "ix", "jo", "nem", "pa", "sto", "wy", "zu", "cha", "dre", "eb", "fli", "gon", "hal"]


def vocabulary():
    rng = random.Random(7)
    seen = []
    while len(seen) < 3000:
        word = "".join(rng.choice(SYLLABLES) for _ in range(rng.randint(2, 4)))
        if word not in seen:
            seen.append(word)
    return seen


VOCABULARY = vocabulary()


def sentence(rng, low=8, high=18):
    chosen = [rng.choice(VOCABULARY) for _ in range(rng.randint(low, high))]
    return chosen[0].capitalize() + " " + " ".join(chosen[1:]) + "."


def paragraphs(seed, count, low=2, high=5):
    rng = random.Random(seed)
    return [" ".join(sentence(rng) for _ in range(rng.randint(low, high))) for _ in range(count)]


def story(seed, count=30):
    return paragraphs(seed, count)


def text_of(parts):
    return "\n\n".join(parts) + "\n"


def tree_digest(root):
    digest = hashlib.sha256()
    for folder, subfolders, names in os.walk(root):
        subfolders.sort()
        for name in sorted(names):
            full = os.path.join(folder, name)
            digest.update(os.path.relpath(full, root).encode())
            with open(full, "rb") as f:
                digest.update(f.read())
    return digest.hexdigest()


class Bench:
    def __init__(self, sources, overrides=None):
        self.dir = Path(tempfile.mkdtemp(prefix="dedupe-test-"))
        self.sources = sources
        self.extra = []
        self.overrides = {"scan": {"settle_seconds": 0}}
        for table, patch in (overrides or {}).items():
            self.overrides.setdefault(table, {}).update(patch)
        for name in sources:
            (self.dir / "roots" / name).mkdir(parents=True)
        self.write_config()

    def write_config(self):
        lines = [f'thresholds = "{HERE / "thresholds.toml"}"', ""]
        for table, patch in self.overrides.items():
            lines.append(f"[override.{table}]")
            lines.extend(f"{key} = {json.dumps(value)}" for key, value in patch.items())
            lines.append("")
        for name, (kind, priority, *more) in self.sources.items():
            lines += ["[[source]]", f'name = "{name}"', f'path = "roots/{name}"', 'glob = "**/*.txt"',
                      f'kind = "{kind}"', f"priority = {priority}", f"container = {json.dumps(name == 'anth')}"]
            lines += [f"{key} = {json.dumps(value)}" for key, value in (more[0] if more else {}).items()]
            lines.append("")
        lines.extend(self.extra)
        (self.dir / "sources.toml").write_text("\n".join(lines))

    @property
    def cfg(self):
        return Config(self.dir / "sources.toml")

    def put(self, source, name, content):
        path = self.dir / "roots" / source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content if isinstance(content, str) else text_of(content), encoding="utf-8")
        return path

    def scan(self):
        return scan.run(self.cfg, say=lambda *a: None)

    def plan(self):
        records = plan.run(self.cfg, say=lambda *a: None)
        return {(r["source"], r["path"]): r for r in records}

    def apply(self):
        return materialise.run(self.cfg, say=lambda *a: None)

    def report(self):
        report.run(self.cfg, say=lambda *a: None)
        return (self.dir / "report.md").read_text()

    def go(self):
        self.scan()
        records = self.plan()
        self.apply()
        return records

    def lookup(self, text):
        path = self.dir / "query.txt"
        path.write_text(text)
        return lookup.run(self.cfg, str(path), as_json=True, out=io.StringIO())

    def out(self, source, name):
        return (self.dir / "out" / source / name).read_text(encoding="utf-8")

    def out_exists(self, source, name):
        return (self.dir / "out" / source / name).exists()

    def state_bytes(self):
        return b"".join((self.dir / "state" / name).read_bytes()
                        for name in ("plan.jsonl", "pairs.jsonl", "boilerplate.jsonl"))

    def pairs(self):
        return [json.loads(line) for line in (self.dir / "state" / "pairs.jsonl").read_text().splitlines()]

    def skipped(self):
        return {(s["source"], s["path"]): s["reason"] for s in
                (json.loads(line) for line in (self.dir / "state" / "skipped.jsonl").read_text().splitlines())}

    def ledger(self):
        return {(e["source"], e["path"]): e for e in
                (json.loads(line) for line in (self.dir / "out" / "ledger.jsonl").read_text().splitlines())}

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class Case(unittest.TestCase):
    sources = {"mag": ("incoming", 50), "anth": ("incoming", 10), "shelf": ("read", 80)}
    overrides = None

    def setUp(self):
        self.bench = Bench(self.sources, self.overrides)
        self.addCleanup(self.bench.close)
