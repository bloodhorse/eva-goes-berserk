import json
import os
import resource
import signal
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

SCHEMA = """
create table if not exists meta (key text primary key, value text) without rowid;
create table if not exists docs (
    num integer primary key,
    id text unique not null,
    words integer not null,
    codes integer not null,
    ends blob not null,
    unit_words blob not null,
    hashes blob not null,
    prefixes blob not null,
    flags blob not null,
    sample blob not null,
    segment integer not null
);
create table if not exists doc_codes (num integer primary key, codes blob not null);
create table if not exists files (
    source text not null,
    path text not null,
    size integer not null,
    mtime_ns integer not null,
    doc integer not null,
    primary key (source, path)
) without rowid;
create index if not exists files_doc on files (doc);
create table if not exists skipped (
    source text not null,
    path text not null,
    size integer not null,
    mtime_ns integer not null,
    reason text not null,
    primary key (source, path)
) without rowid;
create table if not exists segments (id integer primary key, entries integer not null);
"""


class Busy(Exception):
    pass


class StructureChanged(Exception):
    pass


def crash_point(name):
    wanted = os.environ.get("DEDUPE_CRASH_AT", "")
    if not wanted:
        return
    point, _, count = wanted.partition(":")
    if point != name:
        return
    seen = crash_point.seen.get(name, 0) + 1
    crash_point.seen[name] = seen
    if seen >= int(count or 1):
        os.kill(os.getpid(), signal.SIGKILL)


crash_point.seen = {}


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def lock(state_dir):
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "lock"
    for attempt in range(3):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                holder = int(path.read_text().split()[0])
            except (OSError, ValueError, IndexError):
                holder = None
                time.sleep(0.2)
                try:
                    holder = int(path.read_text().split()[0])
                except (OSError, ValueError, IndexError):
                    holder = None
            if holder is not None and holder != os.getpid() and process_alive(holder):
                raise Busy(f"another run holds {path} (pid {holder})")
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
            print(f"cleared a stale lock (pid {holder})", file=sys.stderr)
            continue
        with os.fdopen(fd, "w") as f:
            f.write(f"{os.getpid()} {int(time.time())}\n")
        break
    else:
        raise Busy(f"could not take {path}")
    try:
        yield
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def write_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(temp, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def write_jsonl(path, records):
    write_atomic(path, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records))


def read_jsonl(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def peak_memory_mb():
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


class Index:
    def __init__(self, cfg, readonly=False):
        self.cfg = cfg
        self.dir = cfg.state
        self.segment_dir = self.dir / "segments"
        self.readonly = readonly
        if readonly:
            if not (self.dir / "index.sqlite").exists():
                raise FileNotFoundError(f"no index at {self.dir}; run scan first")
            self.db = sqlite3.connect(f"file:{self.dir / 'index.sqlite'}?mode=ro", uri=True, timeout=60)
        else:
            self.segment_dir.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(self.dir / "index.sqlite", timeout=60, isolation_level=None)
            self.db.execute("pragma journal_mode=wal")
            self.db.execute("pragma synchronous=full")
            self.db.executescript(SCHEMA)
            self.check_structure()
            self.sweep_orphans()

    def close(self):
        self.db.close()

    def check_structure(self):
        key = self.cfg.structure_key()
        row = self.db.execute("select value from meta where key='structure'").fetchone()
        if row is None:
            self.db.execute("insert into meta values ('structure', ?)", (key,))
        elif row[0] != key:
            raise StructureChanged(
                f"the index was built with structure {row[0]}, the config says {key}; run `dedupe.py rebuild`")

    def segment_ids(self):
        return [r[0] for r in self.db.execute("select id from segments order by id")]

    def segment_paths(self, segment):
        return self.segment_dir / f"{segment:06d}.hash", self.segment_dir / f"{segment:06d}.doc"

    def sweep_orphans(self):
        known = set(self.segment_ids())
        for entry in self.segment_dir.iterdir():
            stem = entry.name.split(".")[0]
            if entry.name.startswith(".") or not stem.isdigit() or int(stem) not in known:
                entry.unlink(missing_ok=True)
        for entry in self.dir.iterdir():
            if entry.name.startswith(".") and entry.name.endswith(".tmp"):
                entry.unlink(missing_ok=True)

    def next_segment_id(self):
        row = self.db.execute("select value from meta where key='segment_seq'").fetchone()
        return int(row[0]) + 1 if row else 1

    def write_segment(self, segment, hashes, docs):
        order = np.argsort(hashes, kind="stable")
        hash_path, doc_path = self.segment_paths(segment)
        for path, array in ((hash_path, hashes[order].astype("<u8")), (doc_path, docs[order].astype("<u4"))):
            temp = path.with_name("." + path.name + ".tmp")
            with open(temp, "wb") as f:
                array.tofile(f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, path)

    def register_segment(self, segment, entries):
        self.db.execute("insert into segments values (?, ?)", (segment, entries))
        self.db.execute("insert or replace into meta values ('segment_seq', ?)", (str(segment),))

    def open_segments(self):
        out = []
        for segment, entries in self.db.execute("select id, entries from segments order by id").fetchall():
            if entries == 0:
                continue
            hash_path, doc_path = self.segment_paths(segment)
            out.append((np.memmap(hash_path, dtype="<u8", mode="r"), np.memmap(doc_path, dtype="<u4", mode="r")))
        return out

    def live_doc_nums(self):
        return np.fromiter((r[0] for r in self.db.execute("select distinct doc from files")), dtype=np.uint32)

    def merge_segments(self, force=False):
        ids = self.segment_ids()
        dead = [r[0] for r in self.db.execute(
            "select num from docs where num not in (select distinct doc from files)")]
        if not force and len(ids) <= self.cfg.scan.segment_merge_count:
            return False
        if len(ids) <= 1 and not dead:
            return False
        opened = self.open_segments()
        live = np.zeros(int(self.db.execute("select coalesce(max(num), 0) from docs").fetchone()[0]) + 1, dtype=bool)
        live[self.live_doc_nums()] = True
        merged = self.next_segment_id()
        hash_path, doc_path = self.segment_paths(merged)
        temp_hash = hash_path.with_name("." + hash_path.name + ".tmp")
        temp_doc = doc_path.with_name("." + doc_path.name + ".tmp")
        slices = 64
        bounds = [np.uint64((i << 64) // slices) for i in range(slices)]
        entries = 0
        with open(temp_hash, "wb") as hash_file, open(temp_doc, "wb") as doc_file:
            for i in range(slices):
                parts_h, parts_d = [], []
                for hashes, docs in opened:
                    lo = int(np.searchsorted(hashes, bounds[i], "left"))
                    hi = int(np.searchsorted(hashes, bounds[i + 1], "left")) if i + 1 < slices else len(hashes)
                    d = np.asarray(docs[lo:hi])
                    keep = live[d]
                    parts_h.append(np.asarray(hashes[lo:hi])[keep])
                    parts_d.append(d[keep])
                h = np.concatenate(parts_h) if parts_h else np.empty(0, dtype="<u8")
                d = np.concatenate(parts_d) if parts_d else np.empty(0, dtype="<u4")
                order = np.argsort(h, kind="stable")
                h[order].astype("<u8").tofile(hash_file)
                d[order].astype("<u4").tofile(doc_file)
                entries += len(h)
            for f in (hash_file, doc_file):
                f.flush()
                os.fsync(f.fileno())
        del opened
        os.replace(temp_hash, hash_path)
        os.replace(temp_doc, doc_path)
        crash_point("merge")
        self.db.execute("begin immediate")
        self.db.execute("delete from segments")
        self.register_segment(merged, entries)
        self.db.execute("update docs set segment = ? where num in (select distinct doc from files)", (merged,))
        self.db.execute("delete from doc_codes where num not in (select distinct doc from files)")
        self.db.execute("delete from docs where num not in (select distinct doc from files)")
        self.db.execute("commit")
        self.sweep_orphans()
        return True

    def doc_codes(self, num):
        row = self.db.execute("select codes from doc_codes where num = ?", (num,)).fetchone()
        return np.frombuffer(row[0], dtype="<u4")
