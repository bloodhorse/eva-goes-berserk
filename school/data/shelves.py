import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from collections import defaultdict
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHOOL = HERE.parent
SIEVE = SCHOOL / "sieve"
DEDUPE_OUT = SCHOOL / "dedupe" / "out"
OUT = SCHOOL / "shelves" / "day4"
TOKENIZER = SCHOOL / "models" / "bins" / "fantasy.tokenizer" / "tokenizer.json"
SEED = "magdra-day4-heldout-1"
CHUNK = 4 * 2**20
SHINGLE = 8
STRIDE = 4
PAIR_ALARM = 5

MODERN = ["apex", "bcs", "clarkesworld", "deadlands", "fantasy", "fireside", "giganotosaurus", "infinityplus",
          "lightspeed", "nightmare", "thedark", "uncanny", "escapepod", "podcastle", "pseudopod",
          "modern/giganotosaurus", "wayback", "released/shiner"]
SERIALS = ["katalepsis", "necroepilogos", "pale", "twig", "ward", "worm", "wanderinginn", "released/wildbow"]
ANTH = ["anth"]
ANTH_LEDGER = SCHOOL / "inbox" / "anth" / "ledger.jsonl"
ROUGH_KEPT = {"anthology-james-patrick-kelly"}

SHELVES = {
    "modern": {"rate": 0.01, "max_words": 40000, "min_words": 300},
    "anth": {"rate": 0.04, "max_words": 40000, "min_words": 1000},
    "serials": {"rate": 0.02, "max_words": 10**9, "min_words": 300},
    "verse2": {"rate": 0.10, "max_words": 10**9, "min_words": 20},
    "anth-rough": {"rate": 0.0, "max_words": 0, "min_words": 0},
}

READ_ROOTS = [
    ("library", "inbox/clean", "*.txt"),
    ("literary", "modern/fadedpage/text", "*.txt"),
    ("horizons", "modern/strangehorizons/text", "*.txt"),
    ("horizons-verse", "modern/strangehorizons/poetry", "*.txt"),
    ("released", "modern/released", "*/text/*.txt"),
    ("lain", "lain", "**/*.txt"),
    ("wired-core", "wired-core", "**/*.txt"),
    ("wired-bulk", "wired-bulk", "**/*.txt"),
    ("fantasy", "models/box/data/shelves/fantasy-r2", "*.txt"),
    ("base", "models/box/data/base-r2", "*.txt"),
    ("scifi-pd2", "pd2/text/scifi", "*.txt"),
]
READ_SKIP = ("modern/released/shiner/", "modern/released/wildbow/", "modern/released/_scratch/")

BLANK_LINE = re.compile(r"\n[ \t\f\v]*(?:\n[ \t\f\v]*)+")
PACT_HEAD = re.compile(r"^(?:[A-Z][A-Za-z’' ]{2,30} \d+\.[\dx]+|(?:Histories|Gathered Pages)[ :(][^\n]{0,14})$")
SAFE = re.compile(r"[^A-Za-z0-9._-]+")
WORD = re.compile(r"[a-z0-9]+")
APOS = re.compile(r"(?<=[a-z])['’‘`´](?=[a-z])")


def paragraphs(text):
    out = []
    for block in BLANK_LINE.split(text.replace("\r\n", "\n").replace("\r", "\n")):
        block = block.strip("\n")
        if block.strip():
            out.append(block)
    return out


def join(paras):
    return "\n\n".join(paras) + "\n"


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8-sig")


def safe(name):
    return SAFE.sub("_", name).strip("_")


def rough_books():
    out = set()
    try:
        with open(ANTH_LEDGER, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    except OSError:
        return out
    for r in rows:
        said = json.dumps([r.get("format"), r.get("warnings")]).casefold()
        if r.get("slug") and r.get("status") == "ok" and "pdf" in said and r["slug"] not in ROUGH_KEPT:
            out.add(r["slug"] + ".txt")
    return out


def shelf_of(record, rough=frozenset()):
    if record["kind"] == "verse":
        return "verse2"
    if record["kind"] not in ("fiction", "mixed"):
        return None
    source = record["source"]
    if source in MODERN:
        return "modern"
    if source in SERIALS:
        return "serials"
    if source in ANTH:
        return "anth-rough" if record["path"] in rough else "anth"
    return "UNASSIGNED"


def stem_of(record):
    path = record["path"][:-4] if record["path"].endswith(".txt") else record["path"]
    return safe(record["source"].replace("/", "-")) + "--" + safe(path.replace("/text/", "/").replace("/", "-"))


def work(shelf, record, key, name, text, title=None, authors=None, eligible=True, note=None):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return {"shelf": shelf, "key": key, "name": name + ".txt", "text": text if text.endswith("\n") else text + "\n",
            "source": record["source"], "source_path": f"sieve/out/{record['kind']}/{record['source']}/{record['path']}",
            "title": title if title is not None else record.get("title"),
            "authors": authors if authors is not None else record.get("authors") or [],
            "eligible": eligible, "note": note}


def piece_mark(text, seen):
    words = WORD.findall(text.lower())[:120]
    mark = hashlib.sha1(" ".join(words).encode("ascii", "ignore")).hexdigest()[:10]
    while mark in seen:
        mark = hashlib.sha1(mark.encode("ascii")).hexdigest()[:10]
    seen.add(mark)
    return mark


def split_anthology(record, text, notes):
    sections = record.get("sections") or []
    base = stem_of(record)
    key = f"{record['source']}/{record['path']}"
    whole = [work("anth", record, key, base, text, eligible=False, note="whole book")]
    if len([s for s in sections if s["kind"] in ("story", "nonfiction-kept")]) < 2:
        return whole
    source_file = DEDUPE_OUT / record["source"] / record["path"]
    try:
        data = source_file.read_bytes()
    except OSError:
        notes.append(f"anth: {record['path']} kept whole: the deduper's copy is gone")
        return whole
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        notes.append(f"anth: {record['path']} kept whole: the deduper's copy changed after the sieve's plan")
        return whole
    paras = paragraphs(data.decode("utf-8-sig"))
    keep = [True] * len(paras)
    for cut in record["cuts"]:
        a, b = cut["paragraphs"]
        keep[a:b] = [False] * (b - a)
    if len(paras) != record["paragraphs"] or join([p for p, k in zip(paras, keep) if k]) != join(paragraphs(text)):
        notes.append(f"anth: {record['path']} kept whole: the sieve's cuts do not rebuild its output")
        return whole
    owner = [None] * len(paras)
    for n, s in enumerate(sections):
        a, b = s["paragraphs"]
        for i in range(a, min(b, len(paras))):
            owner[i] = n
    pieces = []
    current = None
    last_section = None
    for i, p in enumerate(paras):
        if not keep[i]:
            continue
        n = owner[i]
        starts = n is not None and n != last_section and sections[n]["kind"] in ("story", "nonfiction-kept")
        if n is not None:
            last_section = n
        if current is None or starts:
            current = {"paras": [], "kind": sections[n]["kind"] if n is not None else "fragment",
                       "title": sections[n].get("title") if n is not None else None}
            pieces.append(current)
        current["paras"].append(p)
    merged = []
    for piece in pieces:
        words = sum(len(p.split()) for p in piece["paras"])
        if merged and (words < 150 or merged[-1]["kind"] == "fragment"):
            if merged[-1]["kind"] == "fragment":
                merged[-1]["kind"], merged[-1]["title"] = piece["kind"], piece["title"]
            merged[-1]["paras"] += piece["paras"]
        else:
            merged.append(piece)
    if join([p for piece in merged for p in piece["paras"]]) != join(paragraphs(text)):
        notes.append(f"anth: {record['path']} kept whole: the pieces do not add up to the book")
        return whole
    out = []
    seen = set()
    for n, piece in enumerate(merged):
        mark = piece_mark(join(piece["paras"]), seen)
        out.append(work("anth", record, f"{key}#{mark}", f"{base}--{n:03d}", join(piece["paras"]),
                        title=f"{record.get('title') or record['path']}: {piece['title'] or ''}".strip(": "),
                        eligible=piece["kind"] == "story", note=piece["kind"]))
    return out


def split_pact(record, text, notes):
    paras = paragraphs(text)
    pieces = []
    for p in paras:
        if PACT_HEAD.match(p) or not pieces:
            pieces.append([])
        pieces[-1].append(p)
    if len(pieces) < 100 or join([p for piece in pieces for p in piece]) != join(paras):
        notes.append(f"serials: pact kept whole: {len(pieces)} chapter headings found")
        return [work("serials", record, "released/wildbow/pact.txt", "released-wildbow--pact", text, eligible=False)]
    base = stem_of(record)
    seen = set()
    return [work("serials", record, f"released/wildbow/pact.txt#{piece_mark(join(piece), seen)}", f"{base}--{n:03d}", join(piece),
                 title=f"Pact: {piece[0][:60]}") for n, piece in enumerate(pieces)]


def gather():
    notes = []
    works = defaultdict(list)
    unassigned = defaultdict(int)
    missing = 0
    with open(SIEVE / "state" / "plan.jsonl", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    rough = rough_books()
    for record in sorted(records, key=lambda r: (r["source"], r["path"])):
        shelf = shelf_of(record, rough)
        if shelf is None:
            continue
        if shelf == "UNASSIGNED":
            unassigned[record["source"]] += 1
            continue
        path = SIEVE / "out" / record["kind"] / record["source"] / record["path"]
        try:
            text = read_text(path)
        except OSError:
            missing += 1
            continue
        if not text.strip():
            continue
        if shelf == "anth":
            works[shelf] += split_anthology(record, text, notes)
        elif shelf == "anth-rough":
            works[shelf].append(work(shelf, record, f"{record['source']}/{record['path']}", stem_of(record), text, eligible=False, note="pdf-derived, whole book"))
        elif record["source"] == "released/wildbow":
            works[shelf] += split_pact(record, text, notes)
        else:
            works[shelf].append(work(shelf, record, f"{record['source']}/{record['path']}", stem_of(record), text))
    if unassigned:
        notes.append("UNASSIGNED fiction sources, on no shelf: " + ", ".join(f"{k} ({v} files)" for k, v in sorted(unassigned.items())))
    if missing:
        notes.append(f"{missing} files the sieve's plan names are not in sieve/out (run the sieve's apply)")
    for shelf, items in works.items():
        names = [w["name"] for w in items]
        if len(names) != len(set(names)):
            raise SystemExit(f"{shelf}: two works share a file name")
    return works, notes


def prep_chunks(text):
    buf, n = [], 0
    for line in io.StringIO(text):
        buf.append(line)
        n += len(line)
        if n >= CHUNK and line.strip() == "":
            yield "".join(buf)
            buf, n = [], 0
    yield "".join(buf)


def count_tokens(texts, cache):
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(TOKENIZER))
    keys = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
    todo = [(k, t) for k, t in dict(zip(keys, texts)).items() if k not in cache]
    todo.sort(key=lambda kt: len(kt[1]))
    for start in range(0, len(todo), 512):
        batch = todo[start:start + 512]
        chunks, owner = [], []
        for k, t in batch:
            for c in prep_chunks(t.replace("\r\n", "\n").replace("\r", "\n")):
                chunks.append(c)
                owner.append(k)
        totals = defaultdict(int)
        for k, enc in zip(owner, tok.encode_batch(chunks, add_special_tokens=False)):
            totals[k] += len(enc.ids)
        for k, _ in batch:
            cache[k] = totals[k] + 1
    return [cache[k] for k in keys]


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    os.replace(tmp, path)


def read_list(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip() and not line.startswith("#")]
    except OSError:
        return []


def lot(shelf, key):
    return int(hashlib.sha256(f"{SEED}:{shelf}:{key}".encode("utf-8")).hexdigest()[:12], 16) / 16**12


def choose(shelf, items, notes):
    rule = SHELVES[shelf]
    folder = OUT / shelf
    before = set(read_list(folder / "heldout.txt"))
    rejected = {line.split("\t")[0] for line in read_list(folder / "heldout-rejected.txt")}
    present = {w["key"] for w in items}
    chosen = set()
    for w in items:
        fits = w["eligible"] and rule["min_words"] <= w["words"] <= rule["max_words"]
        if w["key"] in rejected:
            continue
        if w["key"] in before or (fits and lot(shelf, w["key"]) < rule["rate"]):
            chosen.add(w["key"])
    if before:
        gone = sorted(before - present)
        new = sorted(chosen - before)
        if gone:
            notes.append(f"{shelf}: {len(gone)} held-out works of the saved list are no longer in the input: " + ", ".join(gone[:5]))
        if new:
            notes.append(f"{shelf}: {len(new)} works joined the held-out list (new input): " + ", ".join(new[:5]))
    return chosen


def norm_words(text):
    return WORD.findall(APOS.sub("", text.lower()))


def shingles(words, stride):
    out = []
    for i in range(0, len(words) - SHINGLE + 1, stride):
        out.append(hashlib.blake2b(" ".join(words[i:i + SHINGLE]).encode("ascii", "ignore"), digest_size=8).digest())
    return out


HELD = {}


def scan_file(job):
    label, path = job
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return label, path, {}, 0
    words = norm_words(text)
    hits = defaultdict(int)
    for h in shingles(words, STRIDE):
        for owner in HELD.get(h, ()):
            hits[owner] += 1
    return label, path, dict(hits), len(words)


def contamination(works, deep, jobs, also=()):
    global HELD
    HELD = {}
    held_words = 0
    for shelf, items in works.items():
        for w in items:
            if w["split"] == "heldout":
                ws = norm_words(w["text"])
                held_words += len(ws)
                for h in set(shingles(ws, 1)):
                    HELD.setdefault(h, []).append(f"{shelf}:{w['key']}")
    targets = []
    for shelf in works:
        folder = OUT / shelf / "train"
        targets += [(f"day4/{shelf}", str(folder / n)) for n in sorted(os.listdir(folder)) if n.endswith(".txt")]
    roots = []
    if deep:
        for label, rel, glob in READ_ROOTS:
            root = SCHOOL / rel
            found = [str(p) for p in sorted(root.glob(glob)) if not any(s in str(p) for s in READ_SKIP)] if root.is_dir() else []
            roots.append((label, rel, len(found)))
            targets += [(f"read/{label}", p) for p in found]
    for spec in also:
        label, _, folder = spec.partition("=")
        found = [os.path.join(folder, n) for n in sorted(os.listdir(folder)) if n.endswith(".txt")]
        roots.append((label, folder, len(found)))
        targets += [(f"read/{label}", p) for p in found]
    pairs = []
    scanned = defaultdict(lambda: [0, 0])
    with get_context("fork").Pool(jobs) as pool:
        for label, path, hits, n in pool.imap_unordered(scan_file, targets, chunksize=16):
            scanned[label][0] += 1
            scanned[label][1] += n
            for owner, count in hits.items():
                pairs.append({"heldout": owner, "against": label, "file": os.path.relpath(path, SCHOOL) if path.startswith(str(SCHOOL)) else path,
                              "shared_sampled_shingles": count})
    pairs.sort(key=lambda p: (-p["shared_sampled_shingles"], p["heldout"], p["file"]))
    return {"heldout_words": held_words, "heldout_shingles": len(HELD), "scanned": {k: {"files": v[0], "words": v[1]} for k, v in sorted(scanned.items())},
            "read_roots": [{"shelf": a, "path": b, "files": c} for a, b, c in roots], "deep": deep,
            "alarm_at": PAIR_ALARM, "pairs_at_alarm": [p for p in pairs if p["shared_sampled_shingles"] >= PAIR_ALARM],
            "pairs_below_alarm": len([p for p in pairs if p["shared_sampled_shingles"] < PAIR_ALARM]),
            "worst_below_alarm": [p for p in pairs if p["shared_sampled_shingles"] < PAIR_ALARM][:20]}


def write_shelf(shelf, items, trash):
    folder = OUT / shelf
    moved = written = 0
    for split in ("train", "heldout"):
        target = folder / split
        target.mkdir(parents=True, exist_ok=True)
        want = {w["name"]: w for w in items if w["split"] == split}
        for name in sorted(os.listdir(target)):
            if name not in want:
                dest = trash / shelf / split / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target / name, dest)
                moved += 1
        for name, w in want.items():
            data = w["text"].encode("utf-8")
            path = target / name
            try:
                same = path.stat().st_size == len(data) and path.read_bytes() == data
            except OSError:
                same = False
            if not same:
                write_atomic(path, data)
                written += 1
    manifest = "".join(json.dumps({"key": w["key"], "split": w["split"], "file": f"{w['split']}/{w['name']}", "source": w["source"],
                                   "source_path": w["source_path"], "title": w["title"], "authors": w["authors"], "note": w["note"],
                                   "words": w["words"], "tokens": w["tokens"], "bytes": len(w["text"].encode("utf-8"))},
                                  ensure_ascii=False) + "\n" for w in items)
    write_atomic(folder / "manifest.jsonl", manifest)
    held = sorted(w["key"] for w in items if w["split"] == "heldout")
    write_atomic(folder / "heldout.txt", "".join(k + "\n" for k in held))
    return written, moved


def tree_digest(folder):
    h = hashlib.sha256()
    n = size = 0
    for name in sorted(os.listdir(folder), key=lambda s: s.encode("utf-8")):
        if name.endswith(".txt"):
            data = (folder / name).read_bytes()
            h.update(data)
            n += 1
            size += len(data)
    return n, size, h.hexdigest()


def summarise(works):
    out = {}
    for shelf, items in works.items():
        s = {"works": len(items)}
        for split in ("train", "heldout"):
            part = [w for w in items if w["split"] == split]
            n, size, digest = tree_digest(OUT / shelf / split)
            s[split] = {"files": n, "bytes": size, "sha256": digest, "words": sum(w["words"] for w in part),
                        "tokens": sum(w["tokens"] for w in part), "bin_bytes": 2 * sum(w["tokens"] for w in part)}
        words = s["train"]["words"] + s["heldout"]["words"]
        tokens = s["train"]["tokens"] + s["heldout"]["tokens"]
        s["words"], s["tokens"] = words, tokens
        s["tokens_per_word"] = round(tokens / max(words, 1), 4)
        s["heldout_share_of_tokens"] = round(s["heldout"]["tokens"] / max(tokens, 1), 4)
        by = defaultdict(lambda: {"works": 0, "words": 0, "tokens": 0, "heldout_works": 0, "heldout_tokens": 0})
        authors = defaultdict(int)
        for w in items:
            b = by[w["source"]]
            b["works"] += 1
            b["words"] += w["words"]
            b["tokens"] += w["tokens"]
            if w["split"] == "heldout":
                b["heldout_works"] += 1
                b["heldout_tokens"] += w["tokens"]
            authors[", ".join(" ".join(a.split()) for a in w["authors"]) or "(unknown)"] += w["tokens"]
        for b in by.values():
            b["tokens_per_word"] = round(b["tokens"] / max(b["words"], 1), 4)
        s["by_source"] = dict(sorted(by.items()))
        s["top_authors"] = [{"author": a, "tokens": t, "share": round(t / max(tokens, 1), 4)}
                            for a, t in sorted(authors.items(), key=lambda kv: -kv[1])[:8]]
        out[shelf] = s
    return out


def build(args):
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    works, notes = gather()
    cache_path = OUT / ".tokens.json"
    cache = load_json(cache_path, {})
    for shelf, items in works.items():
        tokens = count_tokens([w["text"] for w in items], cache)
        for w, t in zip(items, tokens):
            w["tokens"] = t
            w["words"] = len(w["text"].split())
    write_atomic(cache_path, json.dumps(cache))
    trash = OUT / ".trash" / time.strftime("%Y%m%d-%H%M%S")
    for shelf in SHELVES:
        items = works.get(shelf, [])
        chosen = choose(shelf, items, notes)
        for w in items:
            w["split"] = "heldout" if w["key"] in chosen else "train"
        written, moved = write_shelf(shelf, items, trash)
        print(f"{shelf}: {len(items)} works, {len(chosen)} held out; {written} files written, {moved} moved to .trash")
    report = contamination(works, args.deep, args.jobs, args.also)
    demoted = defaultdict(list)
    for p in report["pairs_at_alarm"]:
        shelf, key = p["heldout"].split(":", 1)
        demoted[shelf].append((key, p))
    if demoted and not args.keep_contaminated:
        for shelf, found in demoted.items():
            lines = read_list(OUT / shelf / "heldout-rejected.txt")
            known = {line.split("\t")[0] for line in lines}
            for key, p in found:
                if key not in known:
                    known.add(key)
                    lines.append(f"{key}\tshares {p['shared_sampled_shingles']} sampled shingles with {p['file']}")
            write_atomic(OUT / shelf / "heldout-rejected.txt", "".join(line + "\n" for line in lines))
            keys = {key for key, _ in found}
            for w in works[shelf]:
                if w["key"] in keys:
                    w["split"] = "train"
            write_shelf(shelf, works[shelf], trash)
            notes.append(f"{shelf}: {len(keys)} held-out works shared text with a training or read file and went to train (heldout-rejected.txt)")
        report["after_demotion"] = contamination(works, args.deep, args.jobs, args.also)
    final = report.get("after_demotion", report)
    report["verdict"] = "CLEAN" if not final["pairs_at_alarm"] else "CONTAMINATED"
    write_atomic(OUT / "contamination.json", json.dumps(report, ensure_ascii=False, indent=1))
    summary = {"seed": SEED, "tokenizer": str(TOKENIZER.relative_to(SCHOOL)),
               "sieve_plan": load_json(SIEVE / "state" / "run.json", {}), "shelves": summarise(works), "notes": notes,
               "contamination": {"verdict": report["verdict"], "checked_against": sorted(final["scanned"])}}
    write_atomic(OUT / "summary.json", json.dumps(summary, ensure_ascii=False, indent=1))
    print()
    print(f"{'shelf':10} {'works':>6} {'held':>5} {'words':>12} {'train tok':>12} {'held tok':>10} {'held %':>7} {'tok/word':>8}")
    for shelf, s in summary["shelves"].items():
        print(f"{shelf:10} {s['works']:6d} {s['heldout']['files']:5d} {s['words']:12,d} {s['train']['tokens']:12,d} "
              f"{s['heldout']['tokens']:10,d} {100 * s['heldout_share_of_tokens']:6.2f}% {s['tokens_per_word']:8.4f}")
    print()
    for note in notes:
        print("NOTE " + note)
    print(f"contamination ({'day4 and read shelves' if args.deep else 'day4 shelves only'}): {report['verdict']}, "
          f"{len(report['pairs_at_alarm'])} pairs at or over {PAIR_ALARM} shared sampled shingles before demotion, "
          f"{final['pairs_below_alarm']} below")
    sys.path.insert(0, str(HERE))
    from health import health
    print()
    for shelf in SHELVES:
        for split in ("train", "heldout"):
            health(str(OUT / shelf / split))
    print(f"\n{time.time() - started:.0f}s; summary in {OUT / 'summary.json'}")
    return 0 if report["verdict"] == "CLEAN" else 1


def reject(args):
    folder = OUT / args.shelf
    names = {}
    with open(folder / "manifest.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            names[os.path.basename(r["file"])] = r["key"]
            names[r["key"]] = r["key"]
    lines = read_list(folder / "heldout-rejected.txt")
    for name in args.works:
        if name not in names:
            raise SystemExit(f"{args.shelf}: no work called {name} in the manifest")
        lines.append(f"{names[name]}\t{args.reason}")
        print(f"{args.shelf}: {names[name]} will go to train at the next build")
    write_atomic(folder / "heldout-rejected.txt", "".join(line + "\n" for line in lines))


def count(args):
    cache = {}
    for folder in args.folders:
        names = sorted(n for n in os.listdir(folder) if os.path.isfile(os.path.join(folder, n)))
        texts = []
        for n in names:
            with open(os.path.join(folder, n), encoding="utf-8", errors="replace") as f:
                texts.append(f.read())
        tokens = sum(count_tokens(texts, cache))
        words = sum(len(t.split()) for t in texts)
        print(f"{folder}: {len(names)} files, {words:,} words, {tokens:,} tokens as prep.py counts them, {tokens / max(words, 1):.4f} tokens a word")


def main():
    parser = argparse.ArgumentParser(prog="shelves.py")
    commands = parser.add_subparsers(dest="command")
    b = commands.add_parser("build")
    b.add_argument("--deep", action="store_true")
    b.add_argument("--keep-contaminated", action="store_true")
    b.add_argument("--also", action="append", default=[], metavar="LABEL=FOLDER")
    b.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    c = commands.add_parser("count")
    c.add_argument("folders", nargs="+")
    r = commands.add_parser("reject")
    r.add_argument("shelf", choices=sorted(SHELVES))
    r.add_argument("works", nargs="+")
    r.add_argument("--reason", default="rejected by hand")
    args = parser.parse_args()
    if args.command == "reject":
        return reject(args)
    if args.command == "count":
        return count(args)
    if args.command == "build":
        return build(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
