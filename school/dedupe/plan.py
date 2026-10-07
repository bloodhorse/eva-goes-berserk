import math
import time
from collections import OrderedDict, defaultdict

import numpy as np

import words
from config import KIND_RANK
from scan import source_text
from store import Index, lock, peak_memory_mb, write_jsonl

CACHE_BYTES = 400 * 1024 * 1024


class Doc:
    __slots__ = ("num", "id", "words", "ends", "unit_words", "hashes", "prefixes", "flags", "sample", "files",
                 "rep", "reference", "kind_rank", "priority", "b0", "b1", "body_words", "body_key", "leader",
                 "container", "position", "fate", "common")

    def unit_codes(self):
        return np.diff(self.ends.astype(np.int64), prepend=0)

    def code_range(self):
        start = int(self.ends[self.b0 - 1]) if self.b0 > 0 else 0
        stop = int(self.ends[self.b1 - 1]) if self.b1 > 0 else 0
        return start, max(start, stop)


def load_docs(cfg, index):
    docs = {}
    query = ("select f.source, f.path, d.num, d.id, d.words, d.ends, d.unit_words, d.hashes, d.prefixes, "
             "d.flags, d.sample from files f join docs d on d.num = f.doc")
    for source, path, num, doc_id, word_count, ends, unit_words, hashes, prefixes, flags, sample in index.db.execute(query):
        if source not in cfg.by_name:
            continue
        doc = docs.get(doc_id)
        if doc is None:
            doc = Doc()
            doc.num, doc.id, doc.words = num, doc_id, word_count
            doc.ends = np.frombuffer(ends, dtype="<u4")
            doc.unit_words = np.frombuffer(unit_words, dtype="<u4")
            doc.hashes = np.frombuffer(hashes, dtype="<u8")
            doc.prefixes = np.frombuffer(prefixes, dtype="<u8")
            doc.flags = np.frombuffer(flags, dtype="u1")
            doc.sample = np.frombuffer(sample, dtype="<u8")
            doc.files = []
            doc.container = False
            doc.fate = None
            doc.common = 0.0
            docs[doc_id] = doc
        doc.files.append((source, path))
    for doc in docs.values():
        doc.files.sort()
        real = [f for f in doc.files if cfg.by_name[f[0]].kind != "reference"]
        doc.reference = not real
        pool = real or doc.files
        best = max(cfg.by_name[f[0]].rank for f in pool)
        doc.rep = min(f for f in pool if cfg.by_name[f[0]].rank == best)
        doc.kind_rank, doc.priority = best
        doc.b0, doc.b1 = 0, len(doc.ends)
    return docs


def edge_zones(n, edge_units):
    head = min(edge_units, (n + 1) // 2)
    tail = min(edge_units, n // 2)
    return head, n - tail


def boilerplate_sets(cfg, docs):
    b = cfg.boilerplate
    by_source = defaultdict(list)
    for doc in docs.values():
        for source in sorted({f[0] for f in doc.files}):
            by_source[source].append(doc)
    found = {}
    for source, members in sorted(by_source.items()):
        members.sort(key=lambda d: d.id)
        floor_identical = max(b.min_docs, math.ceil(b.min_share * len(members)))
        floor_template = max(b.template_min_docs, math.ceil(b.template_min_share * len(members)))
        owner, head, tail, hashes, prefixes, short, weighty = [], [], [], [], [], [], []
        for i, doc in enumerate(members):
            n = len(doc.ends)
            position = np.arange(n)
            head_end, tail_start = edge_zones(n, b.edge_units)
            owner.append(np.full(n, i, dtype=np.int32))
            head.append(position < head_end)
            tail.append(position >= tail_start)
            hashes.append(doc.hashes)
            prefixes.append(doc.prefixes)
            short.append(doc.unit_words <= b.template_max_words)
            weighty.append(doc.unit_codes() >= b.min_words)
        owner, head, tail = np.concatenate(owner), np.concatenate(head), np.concatenate(tail)
        hashes, prefixes = np.concatenate(hashes), np.concatenate(prefixes)
        short, weighty = np.concatenate(short), np.concatenate(weighty)

        def spread(keys, allowed, floor, share):
            def docs_per_key(mask):
                k, o = keys[mask], owner[mask]
                order = np.lexsort((o, k))
                k, o = k[order], o[order]
                first = np.ones(len(k), dtype=bool)
                first[1:] = (k[1:] != k[:-1]) | (o[1:] != o[:-1])
                return np.unique(k[first], return_counts=True)

            def lookup(table_keys, table_counts, wanted):
                at = np.searchsorted(table_keys, wanted)
                at[at == len(table_keys)] = 0
                return np.where(table_keys[at] == wanted, table_counts[at], 0) if len(table_keys) else np.zeros(len(wanted), dtype=np.int64)

            live = keys != 0
            edge_keys, at_edge = docs_per_key(live & allowed & (head | tail))
            inner_keys, at_inner = docs_per_key(live & ~(head | tail))
            out = []
            for zone in (head, tail):
                zone_keys, at_zone = docs_per_key(live & allowed & zone)
                either = lookup(edge_keys, at_edge, zone_keys)
                inner = lookup(inner_keys, at_inner, zone_keys)
                good = (at_zone >= floor) & (either >= share * (either + inner))
                out.append({int(k): int(c) for k, c in zip(zone_keys[good], at_zone[good])})
            return out

        everything = np.ones(len(owner), dtype=bool)
        identical = spread(np.where(weighty, hashes, 0), everything, floor_identical, b.edge_share)
        templates = spread(prefixes, short, floor_template, b.template_edge_share)
        found[source] = (identical, templates)
    return found


def strip_edges(cfg, doc, sets):
    b = cfg.boilerplate
    identical, templates = sets
    n = len(doc.ends)
    if n == 0:
        return 0, n
    codes = doc.unit_codes()
    head_end, tail_start = edge_zones(n, b.edge_units)

    def recognised(u, zone):
        if codes[u] >= b.min_words and int(doc.hashes[u]) in identical[zone]:
            return True
        return bool(codes[u] > 0 and doc.unit_words[u] <= b.template_max_words
                    and int(doc.prefixes[u]) in templates[zone])

    def carried(span, marks, longest):
        loose = [int(doc.unit_words[v]) for v in span if v not in marks and codes[v] > 0]
        return sum(loose) <= b.sandwich_max_words and max(loose, default=0) <= longest

    tail_marks = {u for u in range(tail_start, n) if recognised(u, 1)}
    head_marks = {u for u in range(0, head_end) if recognised(u, 0)}
    b0, b1 = 0, n
    for u in sorted(tail_marks):
        if carried(range(u, n), tail_marks, b.sandwich_unit_max_words):
            b1 = u
            break
    for u in sorted(head_marks, reverse=True):
        if u < b1 and carried(range(0, u + 1), head_marks, b.head_sandwich_unit_max_words):
            b0 = u + 1
            break
    while b1 > b0 and b1 < n and codes[b1 - 1] == 0:
        b1 -= 1
    while b0 < b1 and b0 > 0 and codes[b0] == 0:
        b0 += 1
    if not any(codes[u] > 0 for u in range(b0, b1)):
        loose = [u for u in list(range(0, b0)) + list(range(b1, n))
                 if codes[u] > 0 and u not in head_marks and u not in tail_marks]
        if loose:
            return 0, n
    return b0, b1


class Shingled:
    __slots__ = ("ordered", "unique", "bytes")


class Comparer:
    def __init__(self, cfg, index, common):
        self.cfg = cfg
        self.index = index
        self.common = common
        self.size = cfg.structure.shingle_words
        self.modulus = np.uint64(cfg.structure.sample_modulus)
        self.cache = OrderedDict()
        self.cached_bytes = 0

    def shingled(self, doc):
        hit = self.cache.get(doc.id)
        if hit is not None:
            self.cache.move_to_end(doc.id)
            return hit
        start, stop = doc.code_range()
        s = Shingled()
        s.ordered = words.shingles(self.index.doc_codes(doc.num)[start:stop], self.size)
        s.unique = np.unique(s.ordered)
        s.bytes = s.ordered.nbytes + s.unique.nbytes
        doc.common = self.common_share(s.unique)
        self.cache[doc.id] = s
        self.cached_bytes += s.bytes
        while self.cached_bytes > CACHE_BYTES and len(self.cache) > 2:
            _, old = self.cache.popitem(last=False)
            self.cached_bytes -= old.bytes
        return s

    def common_share(self, hashes):
        if len(self.common) == 0:
            return 0.0
        mine = hashes[hashes % self.modulus == 0]
        if len(mine) == 0:
            return 0.0
        at = np.searchsorted(self.common, mine)
        at[at == len(self.common)] = 0
        return float((self.common[at] == mine).mean())

    def blocks(self, doc, ordered, shared):
        r = self.cfg.relations
        start, stop = doc.code_range()
        length = stop - start
        ends = doc.ends[doc.b0:doc.b1].astype(np.int64) - start
        starts = np.concatenate([[0], ends[:-1]])
        unit_words = doc.unit_words[doc.b0:doc.b1].astype(np.int64)
        word_sum = np.concatenate([[0], np.cumsum(unit_words)])
        if len(ordered) == 0 or len(shared) == 0:
            return [], int(word_sum[-1])
        at = np.searchsorted(shared, ordered)
        at[at == len(shared)] = 0
        hit = shared[at] == ordered
        where = np.flatnonzero(hit)
        delta = np.zeros(length + 1, dtype=np.int32)
        delta[where] += 1
        delta[where + self.size] -= 1
        covered = np.cumsum(delta[:-1]) > 0
        cover_sum = np.concatenate([[0], np.cumsum(covered)])
        unit_cover = cover_sum[ends] - cover_sum[starts]
        unit_len = ends - starts
        matched = np.flatnonzero((unit_len > 0) & (unit_cover >= r.unit_match_min * unit_len))
        if len(matched) == 0:
            return [], int(word_sum[-1])
        gaps = word_sum[matched[1:]] - word_sum[matched[:-1] + 1]
        breaks = np.flatnonzero(gaps > r.gap_max_words)
        firsts = np.concatenate([[matched[0]], matched[breaks + 1]])
        lasts = np.concatenate([matched[breaks], [matched[-1]]])
        out = []
        cursor = 0
        loose = 0
        last_unit = len(unit_len) - 1
        for u0, u1 in zip(firsts.tolist(), lasts.tolist()):
            if (u0 > cursor and 0 < unit_words[u0 - 1] <= r.edge_unit_max_words
                    and unit_cover[u0 - 1] >= r.edge_unit_min * max(1, unit_len[u0 - 1])):
                u0 -= 1
            if (u1 < last_unit and 0 < unit_words[u1 + 1] <= r.edge_unit_max_words
                    and unit_cover[u1 + 1] >= r.edge_unit_min * max(1, unit_len[u1 + 1])):
                u1 += 1
            loose = max(loose, int(word_sum[u0] - word_sum[cursor]))
            cursor = u1 + 1
            c0, c1 = int(starts[u0]), int(ends[u1])
            inside = ordered[c0:max(c0, c1 - self.size + 1)][hit[c0:max(c0, c1 - self.size + 1)]]
            out.append({
                "units": [u0 + doc.b0, u1 + 1 + doc.b0],
                "words": int(word_sum[u1 + 1] - word_sum[u0]),
                "held": int(len(np.unique(inside))),
                "purity": round(float(cover_sum[c1] - cover_sum[c0]) / max(1, c1 - c0), 4),
            })
        loose = max(loose, int(word_sum[-1] - word_sum[cursor]))
        return out, loose

    def compare(self, a, b):
        r = self.cfg.relations
        sa, sb = self.shingled(a), self.shingled(b)
        shared = np.intersect1d(sa.unique, sb.unique, assume_unique=True)
        if len(shared) == 0:
            return None
        discount = self.common_share(shared)
        effective = len(shared) * (1 - discount)
        size_a = len(sa.unique) * (1 - a.common)
        size_b = len(sb.unique) * (1 - b.common)
        matched_words = int(effective) + self.size - 1
        if matched_words < r.min_match_words or size_a < 1 or size_b < 1:
            return None
        ca, cb = min(1.0, effective / size_a), min(1.0, effective / size_b)
        blocks_a, loose_a = self.blocks(a, sa.ordered, shared)
        blocks_b, loose_b = self.blocks(b, sb.ordered, shared)

        def holder(blocks, size_other):
            best = max(blocks, key=lambda k: (k["held"], -k["units"][0]), default=None)
            if best is not None and best["held"] * (1 - discount) >= r.contained_min * size_other:
                return best
            return None

        def big(blocks):
            return [k for k in blocks
                    if k["words"] >= r.shared_block_min_words and k["purity"] >= r.shared_block_purity_min]

        big_a, big_b = big(blocks_a), big(blocks_b)
        clean = bool(big_a and big_b
                     and sum(k["held"] for k in big_a) >= r.shared_block_clean_min * len(shared)
                     and sum(k["held"] for k in big_b) >= r.shared_block_clean_min * len(shared))
        same = ca >= r.same_work_min and cb >= r.same_work_min
        a_in_b = None if same else holder(blocks_b, size_a)
        b_in_a = None if same else holder(blocks_a, size_b)
        if a_in_b and b_in_a:
            if (len(sa.unique), a.id) <= (len(sb.unique), b.id):
                b_in_a = None
            else:
                a_in_b = None
        amb = self.cfg.ambiguous
        if not (same or a_in_b or b_in_a or clean or max(ca, cb) >= amb.min_containment
                or matched_words >= amb.min_words):
            return None
        return {
            "a": a.id, "b": b.id, "matched_words": matched_words, "common": round(discount, 4),
            "ca": round(ca, 4), "cb": round(cb, 4), "same": same, "clean": clean,
            "a_in_b": a_in_b, "b_in_a": b_in_a, "big_a": big_a, "big_b": big_b,
            "loose_a": loose_a, "loose_b": loose_b,
        }


def candidate_pairs(cfg, leaders):
    c = cfg.candidates
    modulus = cfg.structure.sample_modulus
    count = len(leaders)
    if count < 2:
        return np.empty(0, dtype=np.uint64), []
    hashes = np.concatenate([d.sample for d in leaders])
    owner = np.concatenate([np.full(len(d.sample), i, dtype=np.uint32) for i, d in enumerate(leaders)])
    if len(hashes) == 0:
        return np.empty(0, dtype=np.uint64), []
    order = np.argsort(hashes, kind="stable")
    hashes, owner = hashes[order], owner[order]
    del order
    twin = hashes[1:] == hashes[:-1]
    grouped = np.zeros(len(hashes), dtype=bool)
    grouped[1:] |= twin
    grouped[:-1] |= twin
    hashes, owner = hashes[grouped], owner[grouped]
    del twin, grouped
    if len(hashes) == 0:
        return np.empty(0, dtype=np.uint64), []
    edge = np.empty(len(hashes), dtype=bool)
    edge[0] = True
    np.not_equal(hashes[1:], hashes[:-1], out=edge[1:])
    starts = np.flatnonzero(edge)
    del edge
    sizes = np.diff(np.append(starts, len(hashes)))
    common = hashes[starts[sizes >= c.common_shingle_docs]]
    keys = np.empty(0, dtype=np.uint64)
    counts = np.empty(0, dtype=np.int64)
    fresh = []
    fresh_size = 0

    def fold():
        nonlocal keys, counts, fresh, fresh_size
        if not fresh:
            return
        raw = np.concatenate(fresh)
        got, n = np.unique(raw, return_counts=True)
        merged, inverse = np.unique(np.concatenate([keys, got]), return_inverse=True)
        total = np.zeros(len(merged), dtype=np.int64)
        np.add.at(total, inverse[:len(keys)], counts)
        np.add.at(total, inverse[len(keys):], n)
        keys, counts, fresh, fresh_size = merged, total, [], 0

    for size in range(2, min(int(c.common_shingle_docs), int(sizes.max()) + 1)):
        groups = starts[sizes == size]
        if len(groups) == 0:
            continue
        table = owner[groups[:, None] + np.arange(size)].astype(np.uint64)
        for i in range(size):
            for j in range(i + 1, size):
                fresh.append(table[:, i] * np.uint64(count) + table[:, j])
                fresh_size += len(groups)
                if fresh_size > 20_000_000:
                    fold()
    fold()
    left = (keys // np.uint64(count)).astype(np.int64)
    right = (keys % np.uint64(count)).astype(np.int64)
    sample_sizes = np.array([len(d.sample) for d in leaders], dtype=np.int64)
    smaller = np.minimum(sample_sizes[left], sample_sizes[right])
    good = (counts >= c.min_shared) & ((counts * modulus >= c.min_est_words)
                                       | (counts >= c.min_est_containment * smaller))
    return common, list(zip(left[good].tolist(), right[good].tolist()))


def side(pair, doc_id):
    if pair["a"] == doc_id:
        return {"mine": pair["ca"], "theirs": pair["cb"], "inside_other": pair["a_in_b"],
                "other_inside": pair["b_in_a"], "big": pair["big_a"], "loose": pair["loose_a"]}
    return {"mine": pair["cb"], "theirs": pair["ca"], "inside_other": pair["b_in_a"],
            "other_inside": pair["a_in_b"], "big": pair["big_b"], "loose": pair["loose_b"]}


def numbers(pair, view):
    return {"matched_words": pair["matched_words"], "of_this": view["mine"], "of_other": view["theirs"],
            "common_discount": pair["common"]}


def decide(cfg, doc, neighbours):
    r = cfg.relations
    for other, pair in neighbours:
        view = side(pair, doc.id)
        whole = view["loose"] < r.unique_block_words
        if pair["same"] and whole:
            return {"action": "drop", "reason": "same work", "counterpart": other, "numbers": numbers(pair, view)}, []
        if view["inside_other"] and whole:
            return {"action": "drop", "reason": "contained in a document that outranks it", "counterpart": other,
                    "numbers": numbers(pair, view)}, []
    cuts, undecided = [], []
    for other, pair in neighbours:
        view = side(pair, doc.id)
        if pair["same"] or view["inside_other"]:
            chosen, why = view["big"], "shares a work"
        elif view["other_inside"]:
            chosen, why = [view["other_inside"]], "contains"
        elif pair["clean"] and (view["mine"] < r.shares_max_containment or view["loose"] >= r.unique_block_words):
            chosen, why = view["big"], "shares a work"
        else:
            chosen, why = [], None
        if chosen:
            for block in chosen:
                cuts.append({"units": list(block["units"]), "why": why, "counterpart": other,
                             "numbers": numbers(pair, view)})
        else:
            undecided.append((other, pair))
    return None, (cuts, undecided)


def settle_units(cfg, doc, cuts, with_intros):
    m = cfg.remnants
    n = len(doc.ends)
    codes = doc.unit_codes()
    unit_words = doc.unit_words
    gone = np.zeros(n, dtype=bool)
    notes = []
    for cut in sorted(cuts, key=lambda c: (c["units"], c["counterpart"].id)):
        u0, u1 = cut["units"]
        fresh = int(unit_words[u0:u1][~gone[u0:u1]].sum())
        gone[u0:u1] = True
        notes.append({"units": [u0, u1], "words": fresh, "why": cut["why"], "counterpart": cut["counterpart"],
                      "numbers": cut["numbers"]})
    def absorb(u0, least_headings, allow_intro):
        j = u0 - 1
        intro_words = intro_paragraphs = 0
        while j >= doc.b0 and not gone[j] and not (doc.flags[j] & words.FLAG_HEADING):
            if codes[j] > 0:
                intro_words += int(unit_words[j])
                intro_paragraphs += 0 if doc.flags[j] & words.FLAG_CONTINUES else 1
            if intro_words > m.intro_max_words or intro_paragraphs > m.intro_max_units:
                return None
            j -= 1
        if j < doc.b0 or gone[j] or (intro_words and not allow_intro):
            return None
        intro_start = j + 1
        headings = 0
        while j >= doc.b0 and not gone[j] and headings < m.heading_max_units and (
                doc.flags[j] & words.FLAG_HEADING or codes[j] == 0):
            headings += 1 if doc.flags[j] & words.FLAG_HEADING else 0
            j -= 1
        while j + 1 < intro_start and codes[j + 1] == 0:
            j += 1
        head_start = j + 1
        if headings < least_headings:
            return None
        notes.append({"units": [head_start, intro_start], "why": "heading before a cut",
                      "words": int(unit_words[head_start:intro_start].sum())})
        if int(unit_words[intro_start:u0].sum()) > 0:
            notes.append({"units": [intro_start, u0], "why": "introduction between a heading and a cut",
                          "words": int(unit_words[intro_start:u0].sum())})
        gone[head_start:u0] = True
        return head_start, intro_words > 0

    starts = [u for u in range(doc.b0, doc.b1) if gone[u] and (u == doc.b0 or not gone[u - 1])]
    for u0 in starts:
        u1 = u0
        while u1 < doc.b1 and gone[u1]:
            u1 += 1
        if int(unit_words[u0:u1].sum()) < m.heading_min_cut_words:
            continue
        first = absorb(u0, 1, with_intros)
        if first and not first[1] and with_intros:
            absorb(first[0], m.second_heading_min_units, True)
    remnants = []
    u = doc.b0
    while u < doc.b1:
        if gone[u]:
            u += 1
            continue
        v = u
        while v < doc.b1 and not gone[v]:
            v += 1
        left_cut = u > doc.b0
        right_cut = v < doc.b1
        size = int(unit_words[u:v].sum())
        if (left_cut or right_cut) and gone[doc.b0:doc.b1].any():
            if size <= m.remnant_max_words:
                gone[u:v] = True
                if size:
                    notes.append({"units": [u, v], "why": "remnant", "words": size})
            else:
                remnants.append({"units": [u, v], "words": size, "between_cuts": left_cut and right_cut})
        u = v
    keep = ~gone
    keep[:doc.b0] = False
    keep[doc.b1:] = False
    return keep, notes, remnants


def run(cfg, say=print):
    started = time.time()
    with lock(cfg.state):
        index = Index(cfg)
        try:
            records, pairs_out, boiler_out, stats = build(cfg, index, say)
        finally:
            index.close()
        write_jsonl(cfg.state / "plan.jsonl", records)
        write_jsonl(cfg.state / "pairs.jsonl", pairs_out)
        write_jsonl(cfg.state / "boilerplate.jsonl", boiler_out)
    tally = defaultdict(int)
    for record in records:
        tally[record["action"]] += 1
    say(f"plan: {len(records)} files: {tally['keep']} keep, {tally['edit']} edit, {tally['drop']} drop; "
        f"{stats['candidates']} candidate pairs compared, {stats['related']} related, "
        f"{stats['ambiguous']} ambiguous; {time.time() - started:.1f}s, peak {peak_memory_mb():.0f} MB")
    return records


def build(cfg, index, say):
    docs = load_docs(cfg, index)
    sets = boilerplate_sets(cfg, docs)
    for doc in docs.values():
        if doc.reference:
            continue
        doc.b0, doc.b1 = strip_edges(cfg, doc, sets[doc.rep[0]])
    groups = defaultdict(list)
    for doc in docs.values():
        doc.body_words = int(doc.unit_words[doc.b0:doc.b1].sum())
        live = doc.hashes[doc.b0:doc.b1]
        live = live[live != 0]
        doc.body_key = words.hash64(live.astype("<u8").tobytes()) if len(live) else None
        doc.leader = doc
        if doc.body_key is not None and not doc.reference:
            groups[doc.body_key].append(doc)
    for members in groups.values():
        best = max(members, key=lambda d: (d.kind_rank, d.priority, d.body_words, d.id))
        for doc in members:
            doc.leader = best
    leaders = sorted((d for d in docs.values() if d.leader is d and d.body_key is not None), key=lambda d: d.id)
    common, candidates = candidate_pairs(cfg, leaders)
    comparer = Comparer(cfg, index, common)
    related = defaultdict(list)
    pairs = []
    for i, j in sorted(candidates):
        pair = comparer.compare(leaders[i], leaders[j])
        if pair is None:
            continue
        pairs.append(pair)
        related[pair["a"]].append(pair)
        related[pair["b"]].append(pair)
        if pair["a_in_b"]:
            docs[pair["b"]].container = True
        if pair["b_in_a"]:
            docs[pair["a"]].container = True
    order = sorted((d for d in leaders if not d.reference),
                   key=lambda d: (d.kind_rank, d.priority, not d.container, d.body_words, d.id), reverse=True)
    for position, doc in enumerate(order):
        doc.position = position
    outcome = {}
    acted = {}
    for doc in order:
        if doc.body_words == 0:
            doc.fate = "drop"
            outcome[doc.id] = ({"action": "drop", "reason": "nothing but boilerplate"}, None, [], [])
            continue
        neighbours = []
        for pair in related.get(doc.id, []):
            other = docs[pair["b"] if pair["a"] == doc.id else pair["a"]]
            if other.reference or other.position > doc.position or other.fate == "drop":
                continue
            neighbours.append((other, pair))
        neighbours.sort(key=lambda item: item[0].position)
        verdict, rest = decide(cfg, doc, neighbours)
        if verdict:
            doc.fate = "drop"
            outcome[doc.id] = (verdict, None, [], [])
            acted[(verdict["counterpart"].id, doc.id)] = verdict["reason"]
            continue
        cuts, _ = rest
        keep, notes, remnants = settle_units(cfg, doc, cuts, cfg.by_name[doc.rep[0]].container)
        for cut in cuts:
            acted[(cut["counterpart"].id, doc.id)] = cut["why"]
        if not keep.any() or int(doc.unit_words[keep].sum()) == 0:
            doc.fate = "drop"
            outcome[doc.id] = ({"action": "drop", "reason": "nothing left after cuts",
                                "counterpart": cuts[0]["counterpart"] if cuts else None,
                                "numbers": cuts[0]["numbers"] if cuts else None}, None, notes, remnants)
            continue
        doc.fate = "keep"
        outcome[doc.id] = (None, keep, notes, remnants)

    def name(doc):
        return {"source": doc.rep[0], "path": doc.rep[1]}

    records = []
    for doc in sorted(docs.values(), key=lambda d: d.id):
        if doc.reference:
            continue
        leader = doc.leader
        verdict, keep, notes, remnants = outcome.get(leader.id, (None, None, [], []))
        n = len(doc.ends)
        head_words = int(doc.unit_words[:doc.b0].sum())
        tail_words = int(doc.unit_words[doc.b1:].sum())
        base = {"doc": doc.id, "words": doc.words, "units": n}
        if doc.body_key is None:
            mine = dict(base, action="drop", reason="nothing but boilerplate", words_out=0,
                        strip={"head_units": doc.b0, "tail_units": n - doc.b1, "words": head_words + tail_words})
        elif leader is not doc:
            if leader.fate == "drop" and verdict.get("counterpart") is not None:
                mine = dict(base, action="drop", reason=verdict["reason"], counterpart=name(verdict["counterpart"]),
                            numbers=verdict.get("numbers"), via=name(leader), words_out=0)
            else:
                mine = dict(base, action="drop", reason="identical text", counterpart=name(leader), words_out=0)
        elif verdict:
            mine = dict(base, action="drop", reason=verdict["reason"], words_out=0)
            if verdict.get("counterpart") is not None:
                mine["counterpart"] = name(verdict["counterpart"])
                mine["numbers"] = verdict.get("numbers")
        else:
            words_out = int(doc.unit_words[keep].sum())
            edited = bool(notes) or doc.b0 > 0 or doc.b1 < n
            mine = dict(base, action="edit" if edited else "keep", words_out=words_out)
            if edited:
                mine["reason"] = "; ".join(sorted({note["why"] for note in notes}
                                                  | ({"boilerplate"} if doc.b0 > 0 or doc.b1 < n else set())))
                mine["keep_units"] = runs(keep)
        if doc.b0 > 0 or doc.b1 < n:
            mine["strip"] = {"head_units": doc.b0, "tail_units": n - doc.b1, "words": head_words + tail_words}
        if leader is doc and notes:
            mine["cuts"] = [dict({k: v for k, v in note.items() if k != "counterpart"},
                                 **({"counterpart": name(note["counterpart"])} if note.get("counterpart") else {}))
                            for note in notes]
        if leader is doc and remnants and mine["action"] != "drop":
            mine["remnants"] = remnants
        for source, path in doc.files:
            if cfg.by_name[source].kind == "reference":
                continue
            record = dict(mine, source=source, path=path, kind=cfg.by_name[source].kind)
            if (source, path) != doc.rep:
                if mine["action"] != "drop":
                    record = dict(base, source=source, path=path, kind=cfg.by_name[source].kind, action="drop",
                                  reason="identical file", counterpart=name(doc), words_out=0)
                elif "counterpart" not in mine:
                    record["counterpart"] = name(doc)
            records.append(record)
    records.sort(key=lambda r: (r["source"], r["path"]))

    pairs_out = []
    ambiguous = 0
    amb = cfg.ambiguous
    for pair in sorted(pairs, key=lambda p: (p["a"], p["b"])):
        a, b = docs[pair["a"]], docs[pair["b"]]
        if pair["same"]:
            relation = "same work"
        elif pair["a_in_b"] or pair["b_in_a"]:
            relation = "contained"
        elif pair["clean"]:
            relation = "shares a work"
        else:
            relation = "partial"
        action = acted.get((a.id, b.id)) or acted.get((b.id, a.id))
        listed = (action is None and not a.reference and not b.reference and a.fate == "keep" and b.fate == "keep"
                  and (max(pair["ca"], pair["cb"]) >= amb.min_containment or pair["matched_words"] >= amb.min_words))
        ambiguous += listed
        pairs_out.append({
            "a": name(a), "b": name(b), "relation": relation, "acted": action, "ambiguous": bool(listed),
            "matched_words": pair["matched_words"], "of_a": pair["ca"], "of_b": pair["cb"],
            "words_a": a.body_words, "words_b": b.body_words, "common_discount": pair["common"],
            "fate_a": a.fate or "reference", "fate_b": b.fate or "reference",
        })
    for doc in sorted(docs.values(), key=lambda d: d.id):
        if doc.reference or doc.body_key is None:
            continue
        twins = [f for f in doc.files if f != doc.rep and cfg.by_name[f[0]].kind != "reference"]
        for source, path in twins:
            pairs_out.append(identical_pair(name(doc), {"source": source, "path": path}, doc, "identical file"))
        if doc.leader is not doc:
            pairs_out.append(identical_pair(name(doc.leader), name(doc), doc, "identical text"))

    boiler_out = []
    for source, (identical, templates) in sorted(sets.items()):
        if cfg.by_name[source].kind == "reference":
            continue
        used = defaultdict(lambda: [0, 0, None])
        for doc in docs.values():
            if doc.reference or doc.rep[0] != source:
                continue
            codes = doc.unit_codes()
            for u in list(range(0, doc.b0)) + list(range(doc.b1, len(doc.ends))):
                zone = 0 if u < doc.b0 else 1
                if codes[u] >= cfg.boilerplate.min_words and int(doc.hashes[u]) in identical[zone]:
                    key = ("identical", int(doc.hashes[u]))
                elif int(doc.prefixes[u]) in templates[zone] and codes[u] > 0:
                    key = ("template", int(doc.prefixes[u]))
                elif codes[u] > 0:
                    key = ("carried", 0)
                else:
                    continue
                slot = used[key]
                slot[0] += 1
                slot[1] += int(doc.unit_words[u])
                if slot[2] is None or (doc.rep[1], u) < slot[2]:
                    slot[2] = (doc.rep[1], u)
        for (kind, key), (count, word_count, (path, unit)) in sorted(used.items()):
            boiler_out.append({"source": source, "kind": kind, "key": f"{key:016x}", "stripped": count,
                               "words": word_count, "example_path": path,
                               "text": unit_text(cfg, source, path, unit)})
    stats = {"candidates": len(candidates), "related": len(pairs), "ambiguous": ambiguous}
    return records, pairs_out, boiler_out, stats


def identical_pair(a, b, doc, relation):
    return {"a": a, "b": b, "relation": relation, "acted": relation, "ambiguous": False,
            "matched_words": doc.body_words, "of_a": 1.0, "of_b": 1.0, "words_a": doc.body_words,
            "words_b": doc.body_words, "common_discount": 0.0, "fate_a": "keep", "fate_b": "drop"}


def runs(keep):
    out = []
    start = None
    for u, wanted in enumerate(keep.tolist()):
        if wanted and start is None:
            start = u
        if not wanted and start is not None:
            out.append([start, u])
            start = None
    if start is not None:
        out.append([start, len(keep)])
    return out


def unit_text(cfg, source, path, unit):
    try:
        text, _ = source_text(cfg.by_name[source], path)
    except (OSError, UnicodeDecodeError):
        return ""
    found = words.units(text, cfg.structure.long_paragraph_words)
    if unit >= len(found):
        return ""
    return " ".join(found[unit][0].split())[:240]
