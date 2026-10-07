import hashlib
import json
import os
import time

import shape
from settings import WHOLE_KINDS

from store import lock, peak_memory_mb, read_jsonl, write_atomic, write_jsonl


class NoPlan(Exception):
    pass


def load_plan(cfg):
    plan_file = cfg.state / "plan.jsonl"
    if not plan_file.exists():
        raise NoPlan(f"no plan at {plan_file}; run plan first")
    return read_jsonl(plan_file)


def render(record, data):
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        return None
    if record["kind"] in WHOLE_KINDS or not record["cuts"]:
        return data
    paras = shape.paragraphs(data.decode("utf-8-sig"))
    if len(paras) != record["paragraphs"]:
        return None
    keep = [True] * len(paras)
    for cut in record["cuts"]:
        a, b = cut["paragraphs"]
        keep[a:b] = [False] * (b - a)
    return shape.render(paras, keep).encode("utf-8")


def run(cfg, say=print):
    started = time.time()
    with lock(cfg.state):
        plan = load_plan(cfg)
        previous = {(e["source"], e["path"]): e for e in read_jsonl(cfg.out / "ledger.jsonl")}
        cfg.out.mkdir(parents=True, exist_ok=True)
        ledger = []
        expected = set()
        tally = {"written": 0, "untouched": 0, "stale": 0, "missing": 0, "emptied": 0}
        for record in plan:
            source_file = cfg.dedupe.out / record["source"] / record["path"]
            key = hashlib.sha256(json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest()[:20]
            entry = {"source": record["source"], "path": record["path"], "file": str(source_file),
                     "kind": record["kind"], "words_in": record["words"], "words_out": 0,
                     "cuts": [{"reason": c["reason"], "words": c["words"], "paragraphs": c["paragraphs"]}
                              for c in record["cuts"]], "plan_key": key}
            target = cfg.out / record["kind"] / record["source"] / record["path"]
            before = previous.get((record["source"], record["path"]))
            try:
                stat = os.stat(source_file)
                stamp = [stat.st_size, stat.st_mtime_ns]
            except OSError:
                ledger.append(dict(entry, action="missing"))
                tally["missing"] += 1
                continue
            if before and before.get("plan_key") == key and before.get("source_stat") == stamp \
                    and before.get("action") in ("written", "emptied"):
                if before["action"] == "emptied":
                    ledger.append(before)
                    tally["emptied"] += 1
                    continue
                try:
                    same = os.stat(target).st_size == before.get("out_bytes")
                except OSError:
                    same = False
                if same:
                    ledger.append(before)
                    expected.add(str(target))
                    tally["untouched"] += 1
                    continue
            try:
                with open(source_file, "rb") as f:
                    data = f.read()
                made = render(record, data)
            except (OSError, UnicodeDecodeError):
                made = None
            if made is None:
                ledger.append(dict(entry, action="stale"))
                tally["stale"] += 1
                continue
            if not made.strip():
                ledger.append(dict(entry, action="emptied", source_stat=stamp))
                tally["emptied"] += 1
                continue
            try:
                with open(target, "rb") as f:
                    same = f.read() == made
            except OSError:
                same = False
            if not same:
                write_atomic(target, made)
                tally["written"] += 1
            else:
                tally["untouched"] += 1
            expected.add(str(target))
            ledger.append(dict(entry, action="written", words_out=shape.count(made.decode("utf-8-sig")),
                               out=str(target.relative_to(cfg.out)), out_bytes=len(made), source_stat=stamp))
        trashed = sweep(cfg, expected)
        write_jsonl(cfg.out / "ledger.jsonl", ledger)
    say(f"apply: {tally['written']} files written, {tally['untouched']} already right, {tally['emptied']} cut to nothing, "
        f"{tally['stale']} stale, {tally['missing']} missing, {trashed} moved to out/.trash; "
        f"{time.time() - started:.1f}s, peak {peak_memory_mb():.0f} MB")
    if tally["stale"] or tally["missing"]:
        say("apply: stale and missing files changed or went after the plan was made (a dedupe run); run plan and apply again")
    return tally


def sweep(cfg, expected):
    trash = cfg.out / ".trash" / time.strftime("%Y%m%d-%H%M%S")
    moved = 0
    for folder, subfolders, names in os.walk(cfg.out, topdown=False):
        if ".trash" in os.path.relpath(folder, cfg.out).split(os.sep):
            continue
        for name in names:
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, cfg.out)
            if rel == "ledger.jsonl":
                continue
            if name.startswith(".") and name.endswith(".tmp"):
                os.unlink(full)
                continue
            if full in expected:
                continue
            destination = trash / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(full, destination)
            moved += 1
        if folder != str(cfg.out) and not os.listdir(folder):
            os.rmdir(folder)
    return moved
