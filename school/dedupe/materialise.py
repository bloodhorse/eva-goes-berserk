import hashlib
import json
import os
import time

import words
from scan import record_text, stat_of
from store import lock, peak_memory_mb, read_jsonl, write_atomic, write_jsonl


class NoPlan(Exception):
    pass


def target_of(cfg, source, path):
    if source.format == "jsonl":
        return cfg.out / source.name / (path.replace("#", "/") + ".txt")
    return cfg.out / source.name / path


def source_bytes(source, path):
    if source.format == "jsonl":
        text = record_text(source, path)
        if text is None:
            raise FileNotFoundError(path)
        return text.encode("utf-8")
    with open(source.path / path, "rb") as f:
        return f.read()


def label(counterpart):
    return f"{counterpart['source']}:{counterpart['path']}" if counterpart else None


def render(cfg, record, data):
    if hashlib.sha256(data).hexdigest() != record["doc"]:
        return None
    if record["action"] == "keep":
        return data
    all_units = words.units(data.decode("utf-8-sig"), cfg.structure.long_paragraph_words)
    if len(all_units) != record["units"]:
        return None
    keep = [False] * len(all_units)
    for start, stop in record["keep_units"]:
        keep[start:stop] = [True] * (stop - start)
    return words.join_units(all_units, keep).encode("utf-8")


def run(cfg, say=print):
    started = time.time()
    with lock(cfg.state):
        plan_file = cfg.state / "plan.jsonl"
        if not plan_file.exists():
            raise NoPlan(f"no plan at {plan_file}; run plan first")
        plan = read_jsonl(plan_file)
        previous = {(e["source"], e["path"]): e for e in read_jsonl(cfg.out / "ledger.jsonl")}
        cfg.out.mkdir(parents=True, exist_ok=True)
        ledger = []
        expected = set()
        tally = {"kept": 0, "edited": 0, "dropped": 0, "stale": 0, "missing": 0, "written": 0, "untouched": 0}
        for record in plan:
            source = cfg.by_name.get(record["source"])
            if source is None:
                continue
            key = hashlib.sha256(json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest()[:20]
            entry = {"source": record["source"], "path": record["path"], "file": str(source.path / record["path"]),
                     "words_in": record["words"], "words_out": 0, "reason": record.get("reason"),
                     "counterpart": label(record.get("counterpart")), "plan_key": key}
            if record["action"] == "drop":
                ledger.append(dict(entry, action="dropped"))
                tally["dropped"] += 1
                continue
            stat_path = source.path / record["path"].partition("#")[0] if source.format == "jsonl" else source.path / record["path"]
            stat = stat_of(stat_path)
            if stat is None:
                ledger.append(dict(entry, action="missing", reason="the source file is gone; scan and plan again"))
                tally["missing"] += 1
                continue
            target = target_of(cfg, source, record["path"])
            action = "kept" if record["action"] == "keep" else "edited"
            before = previous.get((record["source"], record["path"]))
            if (before and before.get("plan_key") == key and before.get("source_stat") == list(stat[:2])
                    and before.get("action") == action and stat_of(target) is not None
                    and stat_of(target)[0] == before.get("out_bytes")):
                ledger.append(before)
                expected.add(target)
                tally[action] += 1
                tally["untouched"] += 1
                continue
            try:
                data = source_bytes(source, record["path"])
                made = render(cfg, record, data)
            except (OSError, UnicodeDecodeError):
                made = None
            if made is None:
                ledger.append(dict(entry, action="stale",
                                   reason="the source file changed after the scan; scan and plan again"))
                tally["stale"] += 1
                continue
            try:
                with open(target, "rb") as f:
                    same = f.read() == made
            except OSError:
                same = False
            if not same:
                write_atomic(target, made)
                tally["written"] += 1
            expected.add(target)
            ledger.append(dict(entry, action=action, words_out=len(made.decode("utf-8-sig").split()),
                               out=str(target.relative_to(cfg.out)), out_bytes=len(made), source_stat=list(stat[:2])))
            tally[action] += 1
        trashed = sweep(cfg, expected)
        write_jsonl(cfg.out / "ledger.jsonl", ledger)
    say(f"apply: {tally['kept']} kept, {tally['edited']} edited, {tally['dropped']} dropped, "
        f"{tally['stale']} stale, {tally['missing']} missing; {tally['written']} files written, "
        f"{tally['untouched']} already right, {trashed} moved to out/.trash; "
        f"{time.time() - started:.1f}s, peak {peak_memory_mb():.0f} MB")
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
            if cfg.out / rel in expected:
                continue
            destination = trash / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(full, destination)
            moved += 1
        if folder != str(cfg.out) and not os.listdir(folder):
            os.rmdir(folder)
    return moved
