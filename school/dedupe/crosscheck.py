import argparse
import glob
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from config import Config, ConfigError
from store import read_jsonl, write_jsonl

TOKEN = re.compile(r"[a-z0-9]+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])[\"”’')\]]*\s+|\n[ \t]*\n")
BRACKETS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
NAME_SPLIT = re.compile(r"\s+(?:and|with|&)\s+|\s*[;/]\s*|\s*,\s*(?=\S+\s+\S)", re.I)
NUMERAL = re.compile(r"(?:[ivxlcdm]+|\d+)")
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md"}
GENERIC = {"introduction", "contents", "acknowledgments", "acknowledgements", "foreword", "preface", "afterword",
           "prologue", "epilogue", "notes", "copyright", "dedication", "about the author", "about the authors",
           "about the editor", "about the editors", "table of contents", "the end", "end", "part one", "part two",
           "part three", "part four", "part five", "one", "two", "three", "four", "five", "six", "seven", "eight",
           "nine", "ten", "summation", "honorable mentions", "also by", "title page", "epigraph", "interlude",
           "author s note", "authors note", "index", "bibliography", "appendix", "credits", "permissions",
           "story notes", "translated by", "edited by", "fiction", "poetry", "nonfiction", "non fiction"}


MARKS = {i: None for i in range(sys.maxunicode + 1) if unicodedata.category(chr(i)) == "Mn"}
MARKS.update({ord(c): None for c in "’'‘ʼ"})


def fold(text):
    return unicodedata.normalize("NFKD", text).casefold().translate(MARKS)


SHOW_PREFIX = re.compile(r"^\s*([\w’' ]{2,24}?)\s*#?\d+[a-z]?\s*(?:,\s*[\w ]{0,24})?[:–—-]\s+(.+)$", re.I)


def norm(text):
    return " ".join(TOKEN.findall(fold(BRACKETS.sub(" ", text))))


def norm_title(title, source_name):
    title = " ".join(title.split())
    tail = re.split(r"\s+[-–—|]\s+", title)
    if len(tail) > 1 and norm(tail[-1]).replace(" ", "") in norm(source_name).replace(" ", ""):
        title = title[:title.rindex(tail[-1])].rstrip(" -–—|")
    numbered = SHOW_PREFIX.match(title)
    if numbered:
        show = norm(numbered.group(1)).replace(" ", "")
        if show and (show in norm(source_name).replace(" ", "") or show.endswith("episode")) \
                and norm(numbered.group(2)):
            title = numbered.group(2)
    return norm(title)


def surname_of(name):
    tokens = [t for t in TOKEN.findall(fold(name)) if t not in SUFFIXES and not t.isdigit()]
    return tokens[-1] if tokens else ""


def author_names(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        parts = raw
    else:
        raw = raw.strip()
        head, _, tail = raw.partition(",")
        if tail and "," not in tail and " and " not in raw and len(tail.split()) <= 4 and len(head.split()) <= 2:
            parts = [tail.strip() + " " + head.strip()]
        else:
            parts = NAME_SPLIT.split(raw)
    out = []
    for part in parts:
        part = BRACKETS.sub(" ", str(part))
        part = re.sub(r"\b(?:translated|edited|illustrated|narrated)\s+by\b.*", "", part, flags=re.I)
        cleaned = " ".join(w for w in norm(part).split() if not w.isdigit())
        if cleaned and cleaned not in ("various", "anonymous", "unknown"):
            out.append(cleaned)
    return out


def sentence_list(text, least=8):
    text = re.sub(r"[-‐‑]\n[ \t]*(?=[a-z])", "", text)
    out = []
    for piece in SENTENCE_SPLIT.split(fold(text)):
        if not piece:
            continue
        tokens = TOKEN.findall(piece)
        if len(tokens) >= least:
            out.append((hash(" ".join(tokens)), tokens))
    return out


def sentence_table(text, least=8):
    out = {}
    for key, tokens in sentence_list(text, least):
        out.setdefault(key, tokens)
    return out


def sentence_keys(text, least=8):
    return set(sentence_table(text, least))


class Place:
    __slots__ = ("source", "path", "line", "title", "authors", "how")

    def __init__(self, source, path, line, title, authors, how):
        self.source, self.path, self.line, self.title, self.authors, self.how = source, path, line, title, authors, how

    @property
    def file(self):
        return (self.source, self.path)

    def label(self):
        return f"{self.source}:{self.path}" + (f"@{self.line + 1}" if self.line is not None else "")


class Corpus:
    def __init__(self, cfg):
        self.cfg = cfg
        self.c = cfg.crosscheck
        self.texts = {}
        self.keys = {}
        self.out_keys = {}
        self.line_cache = {}
        self.regions = {}

    def path_of(self, file):
        return self.cfg.by_name[file[0]].path / file[1]

    def text(self, file):
        if file not in self.texts:
            try:
                with open(self.path_of(file), encoding="utf-8-sig", errors="replace") as f:
                    self.texts[file] = f.read()
            except OSError:
                self.texts[file] = ""
            if len(self.texts) > 400:
                for old in list(self.texts)[:200]:
                    del self.texts[old]
        return self.texts[file]

    def sentence_set(self, file):
        if file not in self.keys:
            self.keys[file] = sentence_keys(self.text(file))
        return self.keys[file]

    def out_set(self, file):
        if file not in self.out_keys:
            try:
                with open(self.cfg.out / file[0] / file[1], encoding="utf-8-sig", errors="replace") as f:
                    self.out_keys[file] = sentence_keys(f.read())
            except OSError:
                self.out_keys[file] = None
        return self.out_keys[file]

    def lines(self, file):
        if file not in self.line_cache:
            self.line_cache[file] = [l for l in self.text(file).split("\n") if l.strip()]
        return self.line_cache[file]

    def region(self, place):
        if place.line is None:
            return self.sentence_set(place.file)
        spot = (place.file, place.line)
        if spot not in self.regions:
            lines = self.lines(place.file)
            taken, count = [], 0
            for line in lines[place.line:]:
                taken.append(line)
                count += len(line.split())
                if count >= self.c.region_words:
                    break
            self.regions[spot] = sentence_keys("\n\n".join(taken))
        return self.regions[spot]


def metadata_works(cfg):
    works = []
    for source in cfg.sources:
        if source.kind == "reference" or source.format != "txt":
            continue
        if source.metadata:
            for path in sorted(glob.glob(str(source.metadata / "*.json"))):
                try:
                    with open(path, encoding="utf-8") as f:
                        record = json.load(f)
                except (OSError, ValueError):
                    continue
                rel = os.path.splitext(os.path.basename(path))[0] + ".txt"
                if record.get("title") and (source.path / rel).exists():
                    works.append(Place(source.name, rel, None, record["title"],
                                       author_names(record.get("authors") or record.get("author")), "metadata"))
        elif source.ledger:
            for path in sorted(glob.glob(str(source.ledger))):
                base = os.path.dirname(path)
                for record in read_jsonl(path):
                    if not record.get("title"):
                        continue
                    candidates = []
                    if record.get("file"):
                        candidates.append(os.path.join(base, record["file"]))
                    for key in (record.get("slug"), record.get("dir")):
                        if key:
                            candidates.append(str(source.path / (str(key) + ".txt")))
                    for candidate in candidates:
                        rel = os.path.relpath(os.path.realpath(candidate), os.path.realpath(source.path))
                        if not rel.startswith("..") and source.pattern.match(rel.replace(os.sep, "/")) \
                                and os.path.isfile(candidate):
                            works.append(Place(source.name, rel.replace(os.sep, "/"), None, record["title"],
                                               author_names(record.get("author") or record.get("authors")), "ledger"))
                            break
    return works


def heading_parts(line, max_words):
    stripped = line.strip()
    if not stripped or len(stripped.split()) > max_words or len(stripped) > 160:
        return []
    if stripped[-1] in ".,;”\"" and not stripped.endswith("..."):
        return []
    if stripped[0] in "“\"—-":
        return []
    parts = {norm(stripped)}
    for piece in re.split(r":\s+|\s+by\s+|\s+[|•·]\s+", stripped, flags=re.I):
        parts.add(norm(piece))
    return [p for p in parts if p and p not in GENERIC and not all(NUMERAL.fullmatch(t) for t in p.split())]


class Headings:
    def __init__(self, cfg, corpus, works):
        self.c = cfg.crosscheck
        self.corpus = corpus
        self.where = defaultdict(list)
        self.by_file = {}
        self.book_authors = defaultdict(set)
        for work in works:
            self.book_authors[work.file].update(surname_of(a) for a in work.authors)
        for source in cfg.sources:
            if source.kind == "reference" or source.format != "txt":
                continue
            for folder, _, names in os.walk(source.path):
                for name in sorted(names):
                    full = os.path.join(folder, name)
                    rel = os.path.relpath(full, source.path).replace(os.sep, "/")
                    if name.startswith(".") or not source.pattern.match(rel):
                        continue
                    try:
                        if os.path.getsize(full) < self.c.container_min_bytes:
                            continue
                    except OSError:
                        continue
                    self.scan((source.name, rel))

    def scan(self, file):
        lines = self.corpus.lines(file)
        mine = {}
        for i, line in enumerate(lines):
            parts = heading_parts(line, self.c.heading_max_words)
            if parts:
                mine[i] = parts
                for part in parts:
                    self.where[part].append((file, i))
        self.by_file[file] = mine

    def near(self, file, line, reach):
        out = set()
        mine = self.by_file[file]
        for j in range(line - reach, line + reach + 1):
            out.update(mine.get(j, ()))
        return out

    def window_text(self, file, line, before, after, chars):
        lines = self.corpus.lines(file)
        chunk = [l[:chars] for l in lines[max(0, line - before):line + after + 1]]
        return " " + norm(" ".join(chunk)) + " "


def candidate_pairs(cfg, corpus, works, headings):
    c = cfg.crosscheck
    places = defaultdict(dict)
    names = {}

    def add(key, place, surnames=()):
        places[key].setdefault((place.file, place.line), place)
        names.setdefault((key, place.file, place.line), set()).update(surnames)

    for work in works:
        title = norm_title(work.title, work.source)
        if not title or title in GENERIC:
            continue
        surnames = sorted({surname_of(a) for a in work.authors} - {""})
        key = (title, "")
        add(key, work, surnames)
        for file, line in headings.where.get(title, ()):
            if file == work.file:
                continue
            if surnames:
                text = headings.window_text(file, line, c.author_reach_lines, c.author_reach_lines, 400)
                ok = any(f" {s} " in text for s in surnames) or bool(set(surnames) & headings.book_authors[file])
            else:
                ok = len(title.split()) >= c.title_only_min_words
            if ok:
                add(key, Place(file[0], file[1], line, work.title, work.authors, "heading"), surnames)
        if len(title.split()) >= 2 or len(title) >= 8:
            for author in work.authors:
                for file, line in headings.where.get(author, ()):
                    if file == work.file:
                        continue
                    text = headings.window_text(file, line, 0, c.title_reach_lines, 1500)
                    if f" {title} " in text:
                        add(key, Place(file[0], file[1], line, work.title, work.authors, "author line"), surnames)

    shared = {part: spots for part, spots in headings.where.items()
              if len({file for file, _ in spots}) >= 2 and len(spots) <= c.shared_heading_max_spots
              and (len(part.split()) >= 2 or len(part) >= 5)}
    for part, spots in shared.items():
        for i, (file_a, line_a) in enumerate(spots):
            near_a = headings.near(file_a, line_a, c.pair_reach_lines) - {part}
            for file_b, line_b in spots[i + 1:]:
                if file_a == file_b:
                    continue
                near_b = headings.near(file_b, line_b, c.pair_reach_lines) - {part}
                both = {p for p in near_a & near_b if len(p.split()) >= 2 or len(p) >= 5}
                if not both:
                    text_a = headings.window_text(file_a, line_a, 0, c.title_reach_lines, 1500)
                    text_b = headings.window_text(file_b, line_b, 0, c.title_reach_lines, 1500)
                    both = {p for p in near_b if len(p.split()) >= 2 and f" {p} " in text_a} | \
                           {p for p in near_a if len(p.split()) >= 2 and f" {p} " in text_b}
                for other in both:
                    key = ("|".join(sorted((part, other))), "headings")
                    add(key, Place(file_a[0], file_a[1], line_a, f"{part} / {other}", [], "shared headings"))
                    add(key, Place(file_b[0], file_b[1], line_b, f"{part} / {other}", [], "shared headings"))

    def agree(key, a, b):
        if key[1] == "headings":
            return True
        mine, theirs = names[(key, a.file, a.line)], names[(key, b.file, b.line)]
        if mine and theirs:
            return bool(mine & theirs)
        return len(key[0].split()) >= c.title_only_min_words or (a.line is None and b.line is None)

    pairs = []
    titled = set()
    for key, slot in sorted(places.items(), key=lambda item: (item[0][1], item[0][0])):
        by_file = defaultdict(list)
        for place in slot.values():
            by_file[place.file].append(place)
        files = sorted(by_file)
        for i, a in enumerate(files):
            for b in files[i + 1:]:
                if key[1] == "headings" and (a, b) in titled:
                    continue
                left = [x for x in by_file[a] if any(agree(key, x, y) for y in by_file[b])]
                right = [y for y in by_file[b] if any(agree(key, x, y) for x in by_file[a])]
                if left and right:
                    pairs.append((a, b, left, right))
                    if key[1] == "":
                        titled.add((a, b))
    return pairs


def judge(cfg, corpus, a_places, b_places):
    c = cfg.crosscheck
    best = None
    for a in a_places:
        for b in b_places:
            side_a, side_b = corpus.region(a), corpus.region(b)
            whole_a, whole_b = corpus.sentence_set(a.file), corpus.sentence_set(b.file)
            in_b = side_a & whole_b
            in_a = side_b & whole_a
            if a.line is None and b.line is None:
                shared = in_b
                share = len(shared) / max(1, min(len(side_a), len(side_b)))
            elif a.line is None:
                shared, share = in_b, len(in_b) / max(1, len(side_a))
            elif b.line is None:
                shared, share = in_a, len(in_a) / max(1, len(side_b))
            else:
                shared = in_b if len(in_b) >= len(in_a) else in_a
                share = len(shared) / max(1, min(len(side_a), len(side_b)))
            if best is None or len(shared) > len(best[0]):
                best = (shared, share, a, b)
    shared, share, a, b = best
    regional = a.line is not None and b.line is not None
    if len(shared) >= c.same_min_sentences and (share >= c.same_min_share or regional
                                                or len(shared) >= c.same_sure_sentences):
        verdict = "same text"
    elif len(shared) >= c.partial_min_sentences:
        verdict = "partial"
    else:
        verdict = "different"
    return verdict, shared, share, a, b


def residue(corpus, file_a, file_b, shared):
    kept_a, kept_b = corpus.out_set(file_a), corpus.out_set(file_b)
    if kept_a is None or kept_b is None or not shared:
        return 0.0
    return len(shared & kept_a & kept_b) / len(shared)


def outcome_of(cfg, file_a, file_b, left):
    c = cfg.crosscheck
    kinds = {cfg.by_name[file_a[0]].kind, cfg.by_name[file_b[0]].kind}
    if left <= c.caught_max_survival:
        return "caught"
    if kinds == {"read"}:
        return "read-read"
    if left >= c.missed_min_survival:
        return "missed"
    return "partly cut"


def summary(rows, say, what):
    table = defaultdict(lambda: defaultdict(int))
    for row in rows:
        pair = " ↔ ".join(sorted((row["source_a"], row["source_b"])))
        for name in (pair, "all"):
            table[name]["pairs"] += 1
            table[name][row["outcome"]] += 1
    columns = ["pairs", "caught", "partly cut", "missed", "read-read", "partial", "different"]
    columns = [k for k in columns if k == "pairs" or table["all"][k]]
    say("")
    say("| sources | " + " | ".join(columns) + " |")
    say("|---|" + "---:|" * len(columns))
    for pair in sorted(table, key=lambda p: (p == "all", p)):
        say(f"| {pair} | " + " | ".join(str(table[pair][k]) for k in columns) + " |")
    same = sum(table["all"][k] for k in ("caught", "partly cut", "missed"))
    if same:
        say("")
        say(f"{what} where the rule acts: {same}; caught {table['all']['caught']}, "
            f"partly cut {table['all']['partly cut']}, missed {table['all']['missed']} "
            f"({table['all']['missed'] / same:.1%} missed)")
    for outcome in ("missed", "partly cut"):
        chosen = [r for r in rows if r["outcome"] == outcome]
        if chosen:
            say("")
            say(f"{outcome}:")
        for r in chosen:
            say(f"- {r.get('title') or ''} {r['a']} [{r['action_a']}] ↔ {r['b']} [{r['action_b']}]: "
                f"{r['shared_sentences']} sentences shared, {r['left']:.0%} of them still in both outputs")


def by_text(cfg, say=print):
    import numpy as np
    c = cfg.crosscheck
    plan = {(r["source"], r["path"]): r for r in read_jsonl(cfg.state / "plan.jsonl")}
    corpus = Corpus(cfg)
    files = sorted(plan)
    hashes, owners = [], []
    for i, file in enumerate(files):
        if cfg.by_name[file[0]].format != "txt":
            continue
        keys = sentence_keys(corpus.text(file), c.text_sentence_words)
        corpus.texts.clear()
        hashes.append(np.fromiter((k & 0xFFFFFFFFFFFFFFFF for k in keys), dtype=np.uint64, count=len(keys)))
        owners.append(np.full(len(keys), i, dtype=np.int32))
    hashes, owners = np.concatenate(hashes), np.concatenate(owners)
    order = np.argsort(hashes, kind="stable")
    hashes, owners = hashes[order], owners[order]
    edge = np.flatnonzero(np.concatenate([[True], hashes[1:] != hashes[:-1], [True]]))
    sizes = np.diff(edge)
    shared = defaultdict(list)
    for start, size in zip(edge[:-1][(sizes >= 2) & (sizes <= c.text_max_files)].tolist(),
                           sizes[(sizes >= 2) & (sizes <= c.text_max_files)].tolist()):
        group = owners[start:start + size].tolist()
        key = int(hashes[start])
        for x in range(size):
            for y in range(x + 1, size):
                shared[(group[x], group[y])].append(key)
    rows = []
    for (i, j), keys in sorted(shared.items()):
        if len(keys) < c.text_min_sentences:
            continue
        file_a, file_b = files[i], files[j]
        wanted = set(keys)
        outs = []
        for file in (file_a, file_b):
            try:
                with open(cfg.out / file[0] / file[1], encoding="utf-8-sig", errors="replace") as f:
                    outs.append({k & 0xFFFFFFFFFFFFFFFF for k in sentence_keys(f.read(), c.text_sentence_words)})
            except OSError:
                outs.append(set())
        left = len(wanted & outs[0] & outs[1]) / len(wanted)
        rows.append({"a": f"{file_a[0]}:{file_a[1]}", "b": f"{file_b[0]}:{file_b[1]}", "source_a": file_a[0],
                     "source_b": file_b[0], "shared_sentences": len(keys), "left": round(left, 3),
                     "action_a": plan[file_a]["action"], "action_b": plan[file_b]["action"],
                     "outcome": outcome_of(cfg, file_a, file_b, left)})
    write_jsonl(cfg.state / "crosscheck-text.jsonl", rows)
    say(f"crosscheck by text: {len(files)} files, {len(hashes):,} sentences of {c.text_sentence_words}+ words, "
        f"{len(rows)} file pairs sharing {c.text_min_sentences}+ of them")
    summary(rows, say, "file pairs sharing text")
    return rows


def run(cfg, say=print):
    corpus = Corpus(cfg)
    works = metadata_works(cfg)
    headings = Headings(cfg, corpus, works)
    pairs = candidate_pairs(cfg, corpus, works, headings)
    plan = {(r["source"], r["path"]): r for r in read_jsonl(cfg.state / "plan.jsonl")}
    c = cfg.crosscheck
    rows = []
    seen = defaultdict(list)
    for file_a, file_b, a_places, b_places in pairs:
        if file_a not in plan or file_b not in plan:
            continue
        verdict, shared, share, a, b = judge(cfg, corpus, a_places, b_places)
        spot = (a.line if a.line is not None else -1, b.line if b.line is not None else -1)
        if any(abs(spot[0] - s[0]) <= c.same_spot_lines and abs(spot[1] - s[1]) <= c.same_spot_lines
               for s in seen[(file_a, file_b)]):
            continue
        seen[(file_a, file_b)].append(spot)
        row = {"a": a.label(), "b": b.label(), "source_a": file_a[0], "source_b": file_b[0],
               "title": a.title if a.how != "shared headings" else b.title,
               "authors": a.authors or b.authors, "how": sorted({a.how, b.how}), "verdict": verdict,
               "shared_sentences": len(shared), "share": round(share, 3),
               "action_a": plan[file_a]["action"], "action_b": plan[file_b]["action"]}
        if verdict == "same text":
            row["left"] = round(residue(corpus, file_a, file_b, shared), 3)
            row["outcome"] = outcome_of(cfg, file_a, file_b, row["left"])
        else:
            row["outcome"] = verdict
        rows.append(row)
    write_jsonl(cfg.state / "crosscheck.jsonl", rows)

    say(f"crosscheck by title: {len(works)} works with a title, {len(headings.by_file)} files read for headings, "
        f"{len(rows)} title+author pairs in two places")
    summary(rows, say, "same text in two places")
    return rows


def losses(cfg, say=print):
    import words
    c = cfg.crosscheck
    plan = read_jsonl(cfg.state / "plan.jsonl")
    everything = set()
    for folder, subfolders, names in os.walk(cfg.out):
        subfolders[:] = sorted(d for d in subfolders if d != ".trash")
        for name in sorted(names):
            if name == "ledger.jsonl" or name.startswith("."):
                continue
            try:
                with open(os.path.join(folder, name), encoding="utf-8-sig", errors="replace") as f:
                    everything |= sentence_keys(f.read())
            except OSError:
                continue
    rows = []
    for r in plan:
        source = cfg.by_name.get(r["source"])
        if source is None or source.format != "txt" or r["action"] == "keep":
            continue
        try:
            with open(source.path / r["path"], encoding="utf-8-sig", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        units = [u[0] for u in words.units(text, cfg.structure.long_paragraph_words)]
        if len(units) != r["units"]:
            continue
        meant = set()
        strip = r.get("strip") or {}
        for u in list(range(strip.get("head_units", 0))) + list(range(len(units) - strip.get("tail_units", 0),
                                                                    len(units))):
            meant |= sentence_keys(units[u])
        for cut in r.get("cuts", []):
            if not cut.get("counterpart"):
                meant |= sentence_keys("\n\n".join(units[cut["units"][0]:cut["units"][1]]))
        ordered = sentence_list(text)
        gone = sum(1 for k, _ in ordered if k not in everything)
        passages, run = [], []
        for key, tokens in ordered + [(None, None)]:
            if key is not None and key not in everything and key not in meant:
                run.append(tokens)
                continue
            if len(run) >= c.loss_run_sentences:
                passages.append(run)
            run = []
        lost = sum(1 for k, _ in ordered if k not in everything and k not in meant)
        if gone:
            passages.sort(key=lambda p: -sum(len(s) for s in p))
            rows.append({"source": r["source"], "path": r["path"], "action": r["action"],
                         "reason": r.get("reason"), "sentences": len(ordered), "removed_on_purpose": gone - lost,
                         "lost": lost, "passages": len(passages),
                         "passage_words": sum(len(s) for p in passages for s in p),
                         "examples": [{"sentences": len(p), "words": sum(len(s) for s in p),
                                       "opens": " ".join(p[0])[:240], "closes": " ".join(p[-1])[:160]}
                                      for p in passages[:c.loss_examples]]})
    write_jsonl(cfg.state / "crosscheck-losses.jsonl", rows)
    table = defaultdict(lambda: defaultdict(int))
    for row in rows:
        for name in (row["source"], "all"):
            table[name]["files"] += row["passages"] > 0
            table[name]["lost"] += row["lost"]
            table[name]["passages"] += row["passages"]
            table[name]["passage_words"] += row["passage_words"]
            table[name]["meant"] += row["removed_on_purpose"]
    say(f"crosscheck of losses: {len(everything):,} distinct sentences of 8+ words in the output. A sentence of a "
        "cut or dropped file that is in no output file is lost; one alone is a reworded line of another edition, "
        f"{c.loss_run_sentences} or more in a row are a passage nobody kept")
    say("")
    say("| source | sentences lost | passages lost | files with one | words in the passages | "
        "sentences removed as boilerplate, heading or introduction |")
    say("|---|---:|---:|---:|---:|---:|")
    for name in sorted(table, key=lambda s: (s == "all", s)):
        row = table[name]
        say(f"| {name} | {row['lost']} | {row['passages']} | {row['files']} | {row['passage_words']} | "
            f"{row['meant']} |")
    worst = sorted((r for r in rows if r["passages"]), key=lambda r: -r["passage_words"])[:c.loss_rows]
    if worst:
        say("")
    for r in worst:
        say(f"- {r['source']}:{r['path']} [{r['action']}: {r['reason']}]: {r['passages']} passages, "
            f"{r['passage_words']} words")
        for e in r["examples"]:
            say(f"  - {e['sentences']} sentences, {e['words']} words: “{e['opens']}” … “{e['closes']}”")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(prog="crosscheck.py",
                                     description="an audit of the plan by titles and authors, not by shingles")
    parser.add_argument("--config", default=str(HERE / "sources.toml"))
    parser.add_argument("mode", nargs="?", default="titles", choices=("titles", "text", "losses", "all"))
    args = parser.parse_args(argv)
    try:
        cfg = Config(args.config)
        if args.mode in ("titles", "all"):
            run(cfg)
        if args.mode in ("text", "all"):
            by_text(cfg)
        if args.mode in ("losses", "all"):
            losses(cfg)
    except (ConfigError, FileNotFoundError) as error:
        print(f"crosscheck: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
