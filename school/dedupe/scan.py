import hashlib
import json
import os
import time

import numpy as np

import words
from store import Index, crash_point, lock, peak_memory_mb, write_jsonl

STABLE_REASONS = {"too large", "empty", "not utf-8", "binary", "no words", "bad json"}


def walk(source):
    root = str(source.path)
    complete = True
    found = []

    def fail(error):
        nonlocal complete
        if not isinstance(error, FileNotFoundError) or error.filename == root:
            complete = False

    if not os.path.isdir(root):
        return [], False
    for folder, subfolders, names in os.walk(root, onerror=fail):
        subfolders[:] = sorted(d for d in subfolders if not d.startswith("."))
        for name in names:
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if name.startswith(".") or not source.pattern.match(rel):
                continue
            found.append((rel, full))
    return sorted(found), complete


def stat_of(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_size, max(st.st_mtime_ns, st.st_ctime_ns), st.st_mtime_ns


def read_settled(full, before):
    try:
        with open(full, "rb") as f:
            data = f.read()
    except OSError:
        return None, "vanished"
    if stat_of(full) != before:
        return None, "changed while reading"
    return data, None


def decode(data):
    if b"\x00" in data:
        return None, "binary"
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "not utf-8"
    if not text.strip():
        return None, "empty"
    return text, None


class Scanner:
    def __init__(self, cfg, index, say):
        self.cfg = cfg
        self.index = index
        self.db = index.db
        self.say = say
        self.pending_docs = {}
        self.pending_links = []
        self.pending_skips = []
        self.pending_words = 0
        self.known = {r[0]: r[1] for r in self.db.execute("select id, num from docs")}
        self.next_num = int(self.db.execute("select coalesce(max(num), 0) from docs").fetchone()[0]) + 1
        self.counts = {"unchanged": 0, "indexed": 0, "relinked": 0, "skipped": 0, "vanished": 0, "words": 0}
        self.skips = []

    def skip(self, source, rel, stat, reason):
        self.counts["skipped"] += 1
        self.skips.append({"source": source.name, "path": rel, "reason": reason})
        if reason in STABLE_REASONS and stat is not None:
            self.pending_skips.append((source.name, rel, stat[0], stat[1], reason))

    def take_text(self, source, rel, stat, doc_id, text):
        num = self.known.get(doc_id)
        if num is None and doc_id in self.pending_docs:
            num = self.pending_docs[doc_id][0]
        if num is not None:
            self.pending_links.append((source.name, rel, stat[0], stat[1], num))
            self.counts["relinked"] += 1
            return
        s = self.cfg.structure
        enc = words.encode(text, s.long_paragraph_words, s.heading_max_words)
        if len(enc.codes) == 0:
            self.skip(source, rel, stat, "no words")
            return
        num = self.next_num
        self.next_num += 1
        unique = np.unique(words.shingles(enc.codes, s.shingle_words))
        self.pending_docs[doc_id] = (num, enc, unique, int(enc.words.sum()))
        self.pending_links.append((source.name, rel, stat[0], stat[1], num))
        self.pending_words += len(enc.codes)
        self.counts["indexed"] += 1
        self.counts["words"] += int(enc.words.sum())
        if self.pending_words >= self.cfg.scan.batch_words:
            self.flush()

    def flush(self):
        if not (self.pending_docs or self.pending_links or self.pending_skips):
            return
        segment = 0
        if self.pending_docs:
            segment = self.index.next_segment_id()
            hashes = np.concatenate([u for _, _, u, _ in self.pending_docs.values()])
            docs = np.concatenate([np.full(len(u), num, dtype=np.uint32) for num, _, u, _ in self.pending_docs.values()])
            self.index.write_segment(segment, hashes, docs)
            crash_point("segment")
        modulus = self.cfg.structure.sample_modulus
        self.db.execute("begin immediate")
        if self.pending_docs:
            self.index.register_segment(segment, int(sum(len(u) for _, _, u, _ in self.pending_docs.values())))
        for doc_id, (num, enc, unique, word_count) in self.pending_docs.items():
            self.db.execute(
                "insert into docs values (?,?,?,?,?,?,?,?,?,?,?)",
                (num, doc_id, word_count, len(enc.codes), enc.ends.tobytes(), enc.words.tobytes(),
                 enc.hashes.tobytes(), enc.prefixes.tobytes(), enc.flags.tobytes(),
                 words.sampled(unique, modulus).astype("<u8").tobytes(), segment))
            self.db.execute("insert into doc_codes values (?, ?)", (num, enc.codes.tobytes()))
        self.db.executemany("insert or replace into files values (?,?,?,?,?)", self.pending_links)
        self.db.executemany("delete from skipped where source = ? and path = ?",
                            [(l[0], l[1]) for l in self.pending_links])
        self.db.executemany("insert or replace into skipped values (?,?,?,?,?)", self.pending_skips)
        self.db.executemany("delete from files where source = ? and path = ?",
                            [(s[0], s[1]) for s in self.pending_skips])
        crash_point("commit")
        self.db.execute("commit")
        for doc_id, (num, _, _, _) in self.pending_docs.items():
            self.known[doc_id] = num
        self.pending_docs.clear()
        self.pending_links.clear()
        self.pending_skips.clear()
        self.pending_words = 0
        crash_point("batch")

    def scan_source(self, source):
        started = time.time()
        before = dict(self.counts)
        found, complete = walk(source)
        if not complete:
            self.say(f"  {source.name}: {source.path} could not be listed in full; nothing is forgotten this run")
        have = {r[0]: (r[1], r[2]) for r in self.db.execute(
            "select path, size, mtime_ns from files where source = ?", (source.name,))}
        bad = {r[0]: (r[1], r[2]) for r in self.db.execute(
            "select path, size, mtime_ns from skipped where source = ?", (source.name,))}
        seen = set()
        settle_ns = int(self.cfg.scan.settle_seconds * 1e9)
        for rel, full in found:
            stat = stat_of(full)
            if stat is None:
                continue
            if source.format == "jsonl":
                self.scan_jsonl(source, rel, full, stat, have, seen, settle_ns)
                continue
            seen.add(rel)
            if have.get(rel) == stat[:2]:
                self.counts["unchanged"] += 1
                continue
            if bad.get(rel) == stat[:2]:
                self.counts["skipped"] += 1
                continue
            if time.time_ns() - stat[2] < settle_ns:
                self.skip(source, rel, stat, "settling")
                continue
            if stat[0] > self.cfg.scan.max_file_bytes:
                self.skip(source, rel, stat, "too large")
                continue
            if stat[0] == 0:
                self.skip(source, rel, stat, "empty")
                continue
            data, problem = read_settled(full, stat)
            if problem:
                self.skip(source, rel, stat, problem)
                continue
            text, problem = decode(data)
            if problem:
                self.skip(source, rel, stat, problem)
                continue
            try:
                self.take_text(source, rel, stat, hashlib.sha256(data).hexdigest(), text)
            except Exception as error:
                self.skip(source, rel, stat, f"failed: {type(error).__name__}: {error}")
        if complete:
            gone = [(source.name, p) for p in have if p not in seen]
            lost = [(source.name, p) for p in bad if p not in seen]
            if gone or lost:
                self.flush()
                self.db.execute("begin immediate")
                self.db.executemany("delete from files where source = ? and path = ?", gone)
                self.db.executemany("delete from skipped where source = ? and path = ?", lost)
                self.db.execute("commit")
                self.counts["vanished"] += len(gone)
        delta = {k: self.counts[k] - before[k] for k in self.counts}
        self.say(f"  {source.name}: {len(found)} listed, {delta['indexed']} read ({delta['words']:,} words), "
                 f"{delta['relinked']} known by content, {delta['unchanged']} unchanged, "
                 f"{delta['skipped']} skipped, {delta['vanished']} gone, {time.time() - started:.1f}s")

    def scan_jsonl(self, source, rel, full, stat, have, seen, settle_ns):
        prefix = rel + "#"
        mine = [p for p in have if p.startswith(prefix)]
        if mine and all(have[p] == stat[:2] for p in mine):
            seen.update(mine)
            self.counts["unchanged"] += len(mine)
            return
        if time.time_ns() - stat[2] < settle_ns:
            seen.update(mine)
            self.skip(source, rel, stat, "settling")
            return
        if stat[0] > self.cfg.scan.max_file_bytes:
            self.skip(source, rel, stat, "too large")
            return
        data, problem = read_settled(full, stat)
        if problem:
            seen.update(mine)
            self.skip(source, rel, stat, problem)
            return
        text, problem = decode(data)
        if problem:
            self.skip(source, rel, stat, problem)
            return
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                body = record[source.text_field]
                name = prefix + str(record.get(source.id_field, line_number))
            except (ValueError, KeyError, TypeError):
                self.skip(source, f"{prefix}{line_number}", None, "bad json")
                continue
            if not isinstance(body, str) or not body.strip():
                continue
            seen.add(name)
            self.take_text(source, name, stat, hashlib.sha256(body.encode("utf-8")).hexdigest(), body)


def record_text(source, rel):
    file_rel, _, wanted = rel.partition("#")
    with open(source.path / file_rel, encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if str(record.get(source.id_field, line_number)) == wanted:
                return record.get(source.text_field)
    return None


def source_text(source, rel):
    if source.format == "jsonl":
        text = record_text(source, rel)
        if text is None:
            raise FileNotFoundError(rel)
        return text, hashlib.sha256(text.encode("utf-8")).hexdigest()
    with open(source.path / rel, "rb") as f:
        data = f.read()
    return data.decode("utf-8-sig"), hashlib.sha256(data).hexdigest()


def run(cfg, say=print):
    started = time.time()
    with lock(cfg.state):
        index = Index(cfg)
        scanner = Scanner(cfg, index, say)
        try:
            for source in cfg.sources:
                scanner.scan_source(source)
            scanner.flush()
            merged = index.merge_segments()
            rows = index.db.execute("select source, path, reason from skipped").fetchall()
            stable = {(r[0], r[1]): r[2] for r in rows}
            for s in scanner.skips:
                stable.setdefault((s["source"], s["path"]), s["reason"])
            write_jsonl(cfg.state / "skipped.jsonl",
                        [{"source": k[0], "path": k[1], "reason": v} for k, v in sorted(stable.items())])
            files, docs = index.db.execute("select count(*), count(distinct doc) from files").fetchone()
        finally:
            index.close()
    c = scanner.counts
    say(f"scan: {files} files, {docs} distinct texts in the index; this run read {c['indexed']} "
        f"({c['words']:,} words), {c['relinked']} known by content, {c['unchanged']} unchanged, "
        f"{len(stable)} skipped, {c['vanished']} gone{', segments merged' if merged else ''}; "
        f"{time.time() - started:.1f}s, peak {peak_memory_mb():.0f} MB")
    return c
