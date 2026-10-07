import gzip
import hashlib
import json
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor

import books
import judge
import shape
from settings import WHOLE_KINDS

import ledgers
from store import lock, peak_memory_mb, read_jsonl, write_atomic, write_jsonl

HASH_TAIL = re.compile(r"--[0-9a-f]{12,}$")
TRAILING_NUMBER = re.compile(r"\s+\d+\s*$")
SHAPE_KEYS = ("lines", "line_words_mean", "stanza_share", "short_open_share", "quote_share", "speech_share", "qa_turns", "qa_share",
              "meta", "biblio", "narrative", "address")


class Doc:
    def __init__(self, cfg, source, path):
        self.source = source.name
        self.path = path
        self.file = cfg.dedupe.out / source.name / path
        self.profile = cfg.profile(source.name)
        self.slug = os.path.splitext(os.path.basename(path))[0]
        self.title = HASH_TAIL.sub("", self.slug).replace("-", " ")
        self.authors = []
        self.url = ""
        self.classes = []
        self.label = None
        self.words_in = 0
        self.excerpt_hint = False
        self.ledger_kind = None
        self.columnist = None
        self.raw = None
        self.record = None
        self.surnames = set()


def listing(root):
    out = []
    try:
        for folder, subfolders, names in os.walk(root):
            subfolders[:] = [d for d in subfolders if not d.startswith(".")]
            for name in names:
                if name.endswith(".txt") and not name.startswith("."):
                    out.append(os.path.relpath(os.path.join(folder, name), root))
    except OSError:
        return []
    return sorted(out)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            found = json.load(f)
        return found if isinstance(found, dict) else None
    except (OSError, ValueError):
        return None


def gather(cfg):
    words_in = {}
    for entry in read_jsonl_safe(cfg.dedupe.out / "ledger.jsonl"):
        words_in[(entry.get("source"), entry.get("path"))] = entry.get("words_in") or 0
    docs = []
    for source in sorted(cfg.sources, key=lambda s: s.name):
        try:
            table = ledgers.table(source)
        except (OSError, ValueError):
            table = {}
        for path in listing(cfg.dedupe.out / source.name):
            doc = Doc(cfg, source, path)
            doc.words_in = words_in.get((source.name, path), 0)
            meta = read_json(source.metadata / (doc.slug + ".json")) if source.metadata else None
            record = ledgers.find(table, path)
            doc.record = record
            if meta:
                doc.title = shape.squash(str(meta.get("title") or doc.title))
                doc.authors = [TRAILING_NUMBER.sub("", str(a)).strip() for a in meta.get("authors") or [] if a]
                doc.url = str(meta.get("url") or "")
                doc.classes = [str(c) for c in meta.get("classes") or []]
                doc.excerpt_hint = bool(meta.get("is_excerpt_hint"))
                if meta.get("raw_path") and source.name in cfg.html_labels:
                    doc.raw = source.metadata.parent.parent / str(meta["raw_path"])
            if record:
                if record.get("title") and not meta:
                    doc.title = shape.squash(str(record["title"]))
                if record.get("author") and not doc.authors:
                    doc.authors = [str(record["author"])]
                if record.get("url") and not doc.url:
                    doc.url = str(record["url"])
                doc.ledger_kind = str(record.get("kind")) if record.get("kind") else None
            doc.surnames = shape.surnames(doc.authors)
            docs.append(doc)
    return docs


def read_jsonl_safe(path):
    try:
        return read_jsonl(path)
    except (OSError, ValueError):
        return []


def mark_columnists(cfg, docs):
    strong = cfg.patterns["title_nonfiction_strong"]
    tally = {}
    for doc in docs:
        for author in doc.authors[:1]:
            key = (doc.source, author.casefold())
            mine = tally.setdefault(key, [0, 0])
            mine[0] += 1
            mine[1] += 1 if strong.search(doc.title) else 0
    for doc in docs:
        for author in doc.authors[:1]:
            total, columns = tally[(doc.source, author.casefold())]
            if columns >= 3 and columns >= 0.5 * total:
                doc.columnist = f"{author}: {columns} of {total} titles are columns"


def html_labels(cfg, docs):
    cache_file = cfg.state / "labels.json"
    cache = read_json(cache_file) or {}
    fresh = {}
    changed = False
    for doc in docs:
        if doc.raw is None:
            continue
        try:
            stat = os.stat(doc.raw)
        except OSError:
            continue
        key = str(doc.raw)
        rules = cfg.html_labels[doc.source]
        stamp = [stat.st_size, stat.st_mtime_ns, "\n".join(rule.pattern for rule in rules)]
        before = cache.get(key)
        if before and before[:3] == stamp:
            fresh[key] = before
        else:
            label = None
            try:
                with gzip.open(doc.raw, "rt", encoding="utf-8", errors="replace") as f:
                    page = f.read()
                for rule in rules:
                    found = rule.search(page)
                    if found and shape.squash(found.group(1)):
                        label = shape.squash(found.group(1)).casefold()
                        break
            except (OSError, EOFError, ValueError):
                label = None
            fresh[key] = stamp + [label]
            changed = True
        doc.label = fresh[key][3] or None
    if changed or len(fresh) != len(cache):
        write_atomic(cache_file, json.dumps(fresh, ensure_ascii=False, sort_keys=True))


def resolve(paras, anchor, start=0):
    wanted = shape.squash(anchor)
    if not wanted:
        return None
    for i in range(start, len(paras)):
        if shape.squash(paras[i][:len(anchor) + 200]).startswith(wanted):
            return i
    return None


def apply_overrides(cfg, doc, record, paras, counts, reasons):
    applied = []
    problems = []
    for rule in cfg.overrides:
        if not rule.matches(doc.source, doc.path, doc.title):
            continue
        note = {"number": rule.number, "reason": rule.reason}
        if rule.kind:
            note["kind"] = rule.kind
            note["was"] = record["kind"]
            record["kind"] = rule.kind
            record["why"] = f"override {rule.number}: {rule.reason}" if rule.reason else f"override {rule.number}"
        for span, cutting in ((rule.cut, True), (rule.keep, False)):
            if not span:
                continue
            a = resolve(paras, span["from"])
            if a is None:
                problems.append(f"override {rule.number}: no paragraph opens with “{span['from'][:50]}”")
                continue
            to = span.get("to")
            if to is None:
                b = a
            elif to == "$":
                b = len(paras) - 1
            else:
                b = resolve(paras, to, a)
                if b is None:
                    problems.append(f"override {rule.number}: no paragraph after the start opens with “{to[:50]}”")
                    continue
            for i in range(a, b + 1):
                if cutting:
                    reasons[i] = rule.cut_reason
                else:
                    reasons.pop(i, None)
            note["cut" if cutting else "keep"] = [a, b + 1]
        applied.append(note)
    if applied:
        record["overrides"] = applied
    if problems:
        record["override_problems"] = problems


def plan_one(cfg, doc):
    try:
        with open(doc.file, "rb") as f:
            data = f.read()
    except OSError as error:
        return None, {"source": doc.source, "path": doc.path, "reason": f"cannot be read: {error.__class__.__name__}"}
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, {"source": doc.source, "path": doc.path, "reason": "not UTF-8"}
    paras = shape.paragraphs(text)
    if not paras:
        return None, {"source": doc.source, "path": doc.path, "reason": "no text"}
    counts = [shape.count(p) for p in paras]
    record = {"source": doc.source, "path": doc.path, "sha256": hashlib.sha256(data).hexdigest(),
              "words": sum(counts), "paragraphs": len(paras), "profile": doc.profile,
              "title": doc.title, "authors": doc.authors}
    reasons = {}
    flags = []
    if doc.profile == "anthology":
        reasons, sections, flags, counts = books.plan_book(cfg, doc, paras, doc.record)
        kept_essays = sum(s["words"] for s in sections if s["kind"] == "nonfiction-kept") \
            + sum(s.get("headnote_words", 0) for s in sections if s.get("headnote_kept"))
        record["kind"] = "mixed" if kept_essays else "fiction"
        record["why"] = "an anthology, cut into sections" + (
            f"; {kept_essays} words of essays kept by the book's switch" if kept_essays else "")
        if not kept_essays and len(reasons) == len(paras):
            record["kind"] = "nonfiction"
            record["why"] = "an anthology file with no story left in it: every section is apparatus"
        record["sections"] = sections
        record["evidence"] = flags
        if kept_essays:
            record["words_nonfiction_kept"] = kept_essays
    else:
        feats = shape.features(paras, cfg)
        kind, why, evidence = judge.classify(cfg, doc, paras, feats)
        record["kind"] = kind
        record["why"] = why
        record["shape"] = {k: feats[k] for k in SHAPE_KEYS}
        if kind not in WHOLE_KINDS:
            cuts, flags = judge.cut_edges(cfg, doc, paras)
            for cut in cuts:
                for i in range(*cut["paragraphs"]):
                    reasons[i] = cut["reason"]
        record["evidence"] = evidence + flags
    apply_overrides(cfg, doc, record, paras, counts, reasons)
    cuts = judge.spans(reasons, counts) if record["kind"] not in WHOLE_KINDS else []
    record["cuts"] = cuts
    record["words_cut"] = sum(c["words"] for c in cuts)
    record["words_out"] = record["words"] - record["words_cut"]
    return record, None


WORKER = {}


def worker_start(config_file):
    import settings
    WORKER["cfg"] = settings.Settings(config_file)


def worker_plan(doc):
    return plan_one(WORKER["cfg"], doc)


def build(cfg, shuffle=None):
    docs = gather(cfg)
    if shuffle is not None:
        shuffle(docs)
    mark_columnists(cfg, docs)
    html_labels(cfg, docs)
    records = []
    skipped = []
    jobs = cfg.jobs or os.cpu_count() or 1
    if jobs > 1 and len(docs) >= 64:
        with ProcessPoolExecutor(max_workers=jobs, initializer=worker_start, initargs=(str(cfg.file),)) as pool:
            results = list(pool.map(worker_plan, docs, chunksize=16))
    else:
        results = [plan_one(cfg, doc) for doc in docs]
    for record, skip in results:
        if record is not None:
            records.append(record)
        else:
            skipped.append(skip)
    records.sort(key=lambda r: (r["source"], r["path"]))
    skipped.sort(key=lambda r: (r["source"], r["path"]))
    return records, skipped


def dedupe_stamp(cfg):
    plan_file = cfg.dedupe.state / "plan.jsonl"
    out = {"plan": str(plan_file), "plan_mtime": None, "plan_records": None, "ledger_mtime": None}
    try:
        out["plan_mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.stat(plan_file).st_mtime))
        with open(plan_file, "rb") as f:
            out["plan_records"] = sum(1 for _ in f)
    except OSError:
        pass
    try:
        ledger = cfg.dedupe.out / "ledger.jsonl"
        out["ledger_mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.stat(ledger).st_mtime))
    except OSError:
        pass
    return out


def run(cfg, say=print):
    started = time.time()
    with lock(cfg.state):
        before = dedupe_stamp(cfg)
        records, skipped = build(cfg)
        after = dedupe_stamp(cfg)
        write_jsonl(cfg.state / "plan.jsonl", records)
        write_jsonl(cfg.state / "skipped.jsonl", skipped)
        used = {note["number"] for r in records for note in r.get("overrides", [])}
        unused = [rule.describe() for rule in cfg.overrides if rule.number not in used]
        run_info = {"made_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - started, 1),
                    "files": len(records), "skipped": len(skipped), "dedupe": after,
                    "dedupe_moved_during_run": before != after, "overrides": len(cfg.overrides),
                    "overrides_unused": unused}
        write_atomic(cfg.state / "run.json", json.dumps(run_info, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    tally = {}
    for r in records:
        tally[r["kind"]] = tally.get(r["kind"], 0) + 1
    said = ", ".join(f"{n} {kind}" for kind, n in sorted(tally.items()))
    say(f"plan: {len(records)} files ({said}); {len(skipped)} skipped; {sum(len(r['cuts']) for r in records)} cuts, "
        f"{sum(r['words_cut'] for r in records)} words; {time.time() - started:.1f}s, peak {peak_memory_mb():.0f} MB")
    if before != after:
        say("plan: the deduper's plan or ledger changed while this ran; run plan again when it has finished")
    return records
