import json
import re
import sys
import time
from collections import defaultdict

import numpy as np

import words
from config import KIND_RANK
from scan import source_text
from store import Index

SENTENCE_STOP = re.compile(r"[.!?…][\"'”’)\]]*\s")


def tokenise(text, long_paragraph_words):
    codes, places = [], []
    all_units = words.units(text, long_paragraph_words)
    for u, (unit_text, _) in enumerate(all_units):
        for m in words.WORD.finditer(unit_text):
            for code in words.word_codes(m.group()):
                codes.append(code)
                places.append((u, m.start(), m.end()))
    return np.asarray(codes, dtype="<u4"), places, all_units


def hits(index, query_shingles):
    positions, docs = [], []
    for seg_hashes, seg_docs in index.open_segments():
        lo = np.searchsorted(seg_hashes, query_shingles, "left")
        hi = np.searchsorted(seg_hashes, query_shingles, "right")
        counts = hi - lo
        which = np.flatnonzero(counts)
        if len(which) == 0:
            continue
        total = int(counts[which].sum())
        offsets = np.repeat(lo[which] - np.concatenate([[0], np.cumsum(counts[which])[:-1]]), counts[which])
        take = np.arange(total) + offsets
        positions.append(np.repeat(which, counts[which]))
        docs.append(np.asarray(seg_docs[take]))
    if not positions:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.uint32)
    return np.concatenate(positions), np.concatenate(docs)


def sentence_around(unit_text, start, stop, reach):
    left = max(0, start - reach)
    before = unit_text[left:start]
    stops = [m.end() for m in SENTENCE_STOP.finditer(before)]
    begin = left + stops[-1] if stops else left
    after = unit_text[stop:stop + reach]
    m = SENTENCE_STOP.search(after + " ")
    end = stop + (m.start() + 1 if m else len(after))
    lead = "…" if begin > 0 and not stops else ""
    trail = "…" if not m and stop + reach < len(unit_text) else ""
    return lead + " ".join(unit_text[begin:end].split()) + trail


def longest_match(doc_codes, doc_shingles, query_codes, query_shingles, p0, p1, size):
    best = (0, 0, 0)
    for p in range(p0, p1 + 1):
        if best[0] >= (p1 + size) - p:
            break
        for i in np.flatnonzero(doc_shingles == query_shingles[p]).tolist():
            limit = min(len(doc_codes) - i, len(query_codes) - p)
            same = doc_codes[i:i + limit] == query_codes[p:p + limit]
            length = limit if same.all() else int(np.argmin(same))
            if length > best[0]:
                best = (length, p, i)
    return best


def token_at(all_units, places, i):
    unit, start, stop = places[i]
    earlier = 0
    while i - earlier - 1 >= 0 and places[i - earlier - 1] == places[i]:
        earlier += 1
    return words.normalise_word(all_units[unit][0][start:stop])[earlier]


def run(cfg, path, as_json=False, out=sys.stdout):
    started = time.time()
    size = cfg.structure.shingle_words
    if path == "-":
        text = sys.stdin.read()
    else:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
    query_codes, places, query_units = tokenise(text, cfg.structure.long_paragraph_words)
    query_shingles = words.shingles(query_codes, size)
    index = Index(cfg, readonly=True)
    try:
        result = search(cfg, index, query_codes, query_shingles, places, query_units, size)
    finally:
        index.close()
    result["seconds"] = round(time.time() - started, 2)
    if as_json:
        json.dump(result, out, ensure_ascii=False, indent=1)
        out.write("\n")
        return result
    out.write(f"score {result['score']:.4f}: {result['words_in_runs']} of {result['words']} words sit inside "
              f"{len(result['runs'])} verbatim runs of {size}+ words ({result['seconds']}s)\n")
    for found in result["runs"]:
        out.write(f"\n[{found['words']} words] {found['text']}\n")
        for source in found["sources"]:
            mark = "verified" if source["verified"] else "unverified: " + source["note"]
            out.write(f"  {source['source']}:{source['path']} ({source['words']} words, {mark})\n")
            if source.get("sentence"):
                out.write(f"    {source['sentence']}\n")
        if found["more_documents"]:
            out.write(f"  and {found['more_documents']} more documents\n")
    return result


def search(cfg, index, query_codes, query_shingles, places, query_units, size):
    total = len(query_codes)
    empty = {"score": 0.0, "words": total, "words_in_runs": 0, "runs": []}
    if len(query_shingles) == 0:
        return empty
    positions, doc_nums = hits(index, query_shingles)
    if len(positions) == 0:
        return empty
    owners = defaultdict(list)
    wanted = sorted(set(doc_nums.tolist()))
    for start in range(0, len(wanted), 500):
        chunk = wanted[start:start + 500]
        marks = ",".join("?" * len(chunk))
        for num, source, path in index.db.execute(
                f"select doc, source, path from files where doc in ({marks})", chunk):
            if source in cfg.by_name:
                owners[num].append((source, path))
    by_doc = defaultdict(list)
    for position, num in zip(positions.tolist(), doc_nums.tolist()):
        if num in owners:
            by_doc[num].append(position)
    covered = np.zeros(len(query_shingles), dtype=bool)
    for found in by_doc.values():
        covered[found] = True
    edges = np.flatnonzero(np.diff(np.concatenate([[0], covered.view(np.int8), [0]])))
    spans = list(zip(edges[::2].tolist(), (edges[1::2] - 1).tolist()))
    in_runs = np.zeros(total, dtype=bool)
    runs = []
    for p0, p1 in spans:
        claims = []
        for num, found in by_doc.items():
            inside = sum(1 for p in found if p0 <= p <= p1)
            if inside:
                source, path = min(owners[num], key=lambda f: (-KIND_RANK[cfg.by_name[f[0]].kind],
                                                               -cfg.by_name[f[0]].priority, f))
                claims.append((-inside, -KIND_RANK[cfg.by_name[source].kind], -cfg.by_name[source].priority,
                               source, path, num))
        claims.sort()
        sources = []
        for _, _, _, source, path, num in claims[:cfg.lookup.max_docs_per_run]:
            sources.append(verify(cfg, index, source, path, num, query_codes, query_shingles, places,
                                  query_units, p0, p1, size))
        first, last = p0, p1 + size - 1
        for s in sources:
            if s["verified"]:
                in_runs[s["query_from"]:s["query_from"] + s["words"]] = True
        if not any(s["verified"] for s in sources):
            continue
        unit0, start, _ = places[first]
        unit1, _, stop = places[last]
        if unit0 == unit1:
            shown = query_units[unit0][0][start:stop]
        else:
            shown = " ".join([query_units[unit0][0][start:]] + [query_units[u][0] for u in range(unit0 + 1, unit1)]
                             + [query_units[unit1][0][:stop]])
        runs.append({"words": last - first + 1, "from_word": first, "text": " ".join(shown.split()),
                     "sources": [{k: v for k, v in s.items() if k != "query_from"} for s in sources],
                     "more_documents": max(0, len(claims) - len(sources))})
    count = int(in_runs.sum())
    return {"score": round(count / total, 4) if total else 0.0, "words": total, "words_in_runs": count, "runs": runs}


def verify(cfg, index, source, path, num, query_codes, query_shingles, places, query_units, p0, p1, size):
    out = {"source": source, "path": path, "verified": False, "words": 0, "note": "", "query_from": p0}
    doc_codes = index.doc_codes(num)
    doc_shingles = words.shingles(doc_codes, size)
    length, at_query, at_doc = longest_match(doc_codes, doc_shingles, query_codes, query_shingles, p0, p1, size)
    if length < size:
        out["note"] = "the index match did not hold word for word"
        return out
    out["words"], out["query_from"] = length, at_query
    try:
        text, _ = source_text(cfg.by_name[source], path)
    except (OSError, UnicodeDecodeError):
        out["note"] = "the source file is gone or unreadable"
        return out
    file_codes, file_places, file_units = tokenise(text, cfg.structure.long_paragraph_words)
    spot = at_doc if np.array_equal(file_codes[at_doc:at_doc + length], query_codes[at_query:at_query + length]) else -1
    if spot < 0:
        file_shingles = words.shingles(file_codes, size)
        for i in np.flatnonzero(file_shingles == query_shingles[at_query]).tolist():
            if np.array_equal(file_codes[i:i + length], query_codes[at_query:at_query + length]):
                spot = i
                break
    if spot < 0:
        out["note"] = "the source file changed after the scan and no longer holds the run"
        return out
    want = [token_at(query_units, places, q) for q in range(at_query, at_query + length)]
    got = [token_at(file_units, file_places, i) for i in range(spot, spot + length)]
    if want != got:
        out["note"] = "hashes agree but the words differ"
        return out
    unit0, start, _ = file_places[spot]
    unit1, _, stop = file_places[spot + length - 1]
    reach = cfg.lookup.context_chars
    if unit0 == unit1:
        out["sentence"] = sentence_around(file_units[unit0][0], start, stop, reach)
    else:
        head = sentence_around(file_units[unit0][0], start, len(file_units[unit0][0]), reach)
        tail = sentence_around(file_units[unit1][0], 0, stop, reach)
        middle = [" ".join(file_units[u][0].split()) for u in range(unit0 + 1, unit1)]
        out["sentence"] = " / ".join([head] + middle[:3] + [tail])
    out["verified"] = True
    return out
