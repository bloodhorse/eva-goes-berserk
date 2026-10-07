import json
import os
import re
import time
from collections import defaultdict

import ledgers
import words
from store import read_jsonl, write_atomic


def shape_of(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def long_sections(cfg, source, path):
    try:
        with open(source.path / path, encoding="utf-8-sig", errors="replace") as f:
            units = [u[0] for u in words.units(f.read(), cfg.structure.long_paragraph_words)]
    except OSError:
        return []
    wanted = [shape_of(name) for name in cfg.report.long_apparatus]
    found = []
    u = 0
    while u < len(units):
        first = units[u].strip().split("\n")[0]
        shape = shape_of(first)
        listed = u + 1 < len(units) and words.heading_shaped(units[u + 1], len(units[u + 1].split()),
                                                             cfg.structure.heading_max_words)
        if listed or not (len(shape.split()) <= 6 and any(shape == w or shape.startswith(w + " ") for w in wanted)):
            u += 1
            continue
        count = 0
        v = u + 1
        while v < len(units):
            size = len(units[v].split())
            if count >= cfg.report.long_apparatus_min_words and words.heading_shaped(
                    units[v], size, cfg.structure.heading_max_words):
                break
            count += size
            v += 1
        if count >= cfg.report.long_apparatus_min_words:
            found.append((" ".join(units[u].split())[:60], count))
        u = v
    return found


class Titles:
    def __init__(self, cfg):
        self.cfg = cfg
        self.ledgers = {}

    def ledger(self, source):
        if source.name not in self.ledgers:
            self.ledgers[source.name] = ledgers.table(source)
        return self.ledgers[source.name]

    def record(self, name):
        source = self.cfg.by_name.get(name["source"])
        if source is None or not source.ledger:
            return None
        return ledgers.find(self.ledger(source), name["path"])

    def of(self, name):
        source = self.cfg.by_name.get(name["source"])
        if source is None:
            return None
        stem = os.path.splitext(os.path.basename(name["path"]))[0]
        if source.metadata:
            try:
                with open(source.metadata / os.path.dirname(name["path"]) / (stem + ".json"), encoding="utf-8") as f:
                    record = json.load(f)
                author = record.get("author") or ", ".join(record.get("authors") or [])
                if record.get("title"):
                    return record["title"], author
            except (OSError, ValueError):
                pass
        record = self.record(name)
        if record and record.get("title"):
            return record["title"], record.get("author") or ", ".join(record.get("authors") or [])
        return None

    def show(self, name):
        found = self.of(name)
        where = f"`{name['source']}:{name['path']}`"
        if not found:
            return where
        title, author = found
        return f"*{title}*{' — ' + author if author else ''} {where}"


def n(value):
    return f"{int(round(value)):,}"


def key_of(name):
    return (name["source"], name["path"])


def run(cfg, say=print):
    started = time.time()
    plan = read_jsonl(cfg.state / "plan.jsonl")
    pairs = read_jsonl(cfg.state / "pairs.jsonl")
    boiler = read_jsonl(cfg.state / "boilerplate.jsonl")
    skipped = read_jsonl(cfg.state / "skipped.jsonl")
    titles = Titles(cfg)
    rate = cfg.report.tokens_per_word
    kind = {s.name: s.kind for s in cfg.sources}
    lines = []
    add = lines.append

    per = defaultdict(lambda: defaultdict(int))
    for r in plan:
        row = per[r["source"]]
        row["files"] += 1
        row["in"] += r["words"]
        row["out"] += r["words_out"]
        stripped = r.get("strip", {}).get("words", 0)
        if r["action"] == "drop":
            row["dropped_files"] += 1
            if r["reason"] == "nothing but boilerplate":
                row["boiler"] += r["words"]
            elif r["reason"] == "nothing left after cuts":
                row["boiler"] += stripped
                row["cut"] += r["words"] - stripped
            else:
                row["dup"] += r["words"]
        else:
            row["boiler"] += stripped
            row["cut"] += r["words"] - stripped - r["words_out"]
            row["edited_files"] += r["action"] == "edit"
    total = defaultdict(int)
    for row in per.values():
        for k, v in row.items():
            total[k] += v

    add("# dedupe report")
    add("")
    add(f"Written {time.strftime('%Y-%m-%d %H:%M')} from `state/plan.jsonl`. Words are whitespace words; "
        f"tokens are words × {rate}.")
    add("")
    add("## Totals")
    add("")
    add(f"- files: {n(total['files'])}, of which {n(total['dropped_files'])} dropped whole and "
        f"{n(total['edited_files'])} edited")
    add(f"- words in: {n(total['in'])} ({n(total['in'] * rate)} tokens)")
    add(f"- dropped as duplicate: {n(total['dup'])} words")
    add(f"- cut as contained or shared: {n(total['cut'])} words")
    add(f"- stripped as boilerplate: {n(total['boiler'])} words")
    add(f"- surviving: {n(total['out'])} words ({n(total['out'] * rate)} tokens)")
    for label in ("read", "incoming"):
        words_in = sum(row["in"] for s, row in per.items() if kind.get(s) == label)
        words_out = sum(row["out"] for s, row in per.items() if kind.get(s) == label)
        add(f"- {label}: {n(words_in)} words in, {n(words_out)} surviving ({n(words_out * rate)} tokens)")
    add("")
    add("## Per source")
    add("")
    add("| source | kind | files | words in | dropped as duplicate | cut as contained | boilerplate | surviving | tokens |")
    add("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for source in sorted(per):
        row = per[source]
        add(f"| {source} | {kind.get(source, '?')} | {n(row['files'])} | {n(row['in'])} | {n(row['dup'])} | "
            f"{n(row['cut'])} | {n(row['boiler'])} | {n(row['out'])} | {n(row['out'] * rate)} |")
    add(f"| **all** | | {n(total['files'])} | {n(total['in'])} | {n(total['dup'])} | {n(total['cut'])} | "
        f"{n(total['boiler'])} | {n(total['out'])} | {n(total['out'] * rate)} |")
    add("")

    matrix = defaultdict(int)
    for p in pairs:
        a, b = sorted((p["a"]["source"], p["b"]["source"]))
        matrix[(a, b)] += p["matched_words"]
    names = sorted({s for pair in matrix for s in pair})
    add("## Overlap between sources")
    add("")
    add("Thousands of matched words between every two sources, over all related pairs (acted on or not); "
        "the diagonal is overlap inside one source.")
    add("")
    if names:
        add("| | " + " | ".join(str(i + 1) for i in range(len(names))) + " |")
        add("|---|" + "---:|" * len(names))
        for i, a in enumerate(names):
            cells = []
            for b in names:
                value = matrix.get(tuple(sorted((a, b))), 0)
                cells.append(f"{value / 1000:.0f}" if value >= 500 else ("·" if value == 0 else "<1"))
            add(f"| {i + 1} {a} | " + " | ".join(cells) + " |")
    else:
        add("No overlap found.")
    add("")

    fate = {key_of(r): r for r in plan}

    def outcome(name):
        r = fate.get(key_of(name))
        if r is None:
            return "reference"
        if r["action"] == "drop":
            return "dropped"
        return "edited" if r["action"] == "edit" else "kept"

    def pair_line(p):
        return (f"- {p['relation']}{' (no action)' if not p['acted'] and not p.get('both_read') else ''}: "
                f"{titles.show(p['a'])} "
                f"[{outcome(p['a'])}, {n(p['words_a'])} w] ↔ {titles.show(p['b'])} "
                f"[{outcome(p['b'])}, {n(p['words_b'])} w] — {n(p['matched_words'])} words matched, "
                f"{p['of_a']:.0%} of the first, {p['of_b']:.0%} of the second")

    settled = [p for p in pairs if p.get("both_read")]
    settled.sort(key=lambda p: (-p["matched_words"], key_of(p["a"]), key_of(p["b"])))
    add("## Read against read (left alone)")
    add("")
    add(f"{len(settled)} pairs, {n(sum(p['matched_words'] for p in settled))} matched words. Both texts are on "
        "shelves she has read, with held-out splits cut from them: neither is dropped, cut or stripped for the "
        "other. The largest:")
    add("")
    for p in settled[:cfg.report.read_pairs]:
        add(pair_line(p))
    if len(settled) > cfg.report.read_pairs:
        add(f"- and {len(settled) - cfg.report.read_pairs} smaller pairs, in `state/pairs.jsonl` with `both_read`")
    add("")

    crossing = [p for p in pairs if {kind.get(p["a"]["source"]), kind.get(p["b"]["source"])} == {"read", "incoming"}]
    crossing.sort(key=lambda p: (-p["matched_words"], key_of(p["a"]), key_of(p["b"])))
    add("## Incoming against read (the held-out contamination check)")
    add("")
    add(f"{len(crossing)} pairs, {n(sum(p['matched_words'] for p in crossing))} matched words. A read shelf "
        "always wins: the incoming copy is dropped, or the shared span is cut out of the incoming file.")
    add("")
    for p in crossing:
        add(pair_line(p))
    add("")

    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    names_of = {}
    holders = defaultdict(set)
    for p in pairs:
        if p["relation"] == "partial":
            continue
        a, b = key_of(p["a"]), key_of(p["b"])
        names_of[a], names_of[b] = p["a"], p["b"]
        if p["relation"] == "contained":
            small, large = (a, b) if p["words_a"] <= p["words_b"] else (b, a)
            holders[small].add(large)
            find(small)
        else:
            parent[find(a)] = find(b)
    clusters = defaultdict(list)
    for member in parent:
        clusters[find(member)].append(member)
    inside = {root: sorted({h for m in members for h in holders.get(m, ())} - set(members))
              for root, members in clusters.items()}
    ranked = sorted(clusters, key=lambda c: (-(len(clusters[c]) + len(inside[c])),
                                             -sum(fate[m]["words"] for m in clusters[c] if m in fate),
                                             sorted(clusters[c])[0]))
    ranked = [c for c in ranked if len(clusters[c]) + len(inside[c]) > 1]
    add(f"## The {min(cfg.report.clusters, len(ranked))} largest duplicate clusters")
    add("")
    add(f"{len(ranked)} clusters in all. A cluster is one work: its copies (identical, same work, or a block two "
        "files share), and the containers a copy was found inside.")
    add("")
    for i, root in enumerate(ranked[:cfg.report.clusters], 1):
        cluster = clusters[root]
        add(f"{i}. {len(cluster)} {'copies' if len(cluster) > 1 else 'copy'}, inside {len(inside[root])} "
            f"container{'' if len(inside[root]) == 1 else 's'}")
        for member in sorted(cluster, key=lambda m: (outcome(names_of[m]) != "kept", m))[:12]:
            r = fate.get(member)
            detail = f"{n(r['words'])} → {n(r['words_out'])} w" if r else "reference"
            add(f"   - {outcome(names_of[member])}: {titles.show(names_of[member])} ({detail})")
        if len(cluster) > 12:
            add(f"   - and {len(cluster) - 12} more")
        for holder in inside[root][:8]:
            add(f"   - inside: {titles.show(names_of[holder])}")
    add("")

    containers = [r for r in plan if any(c.get("counterpart") for c in r.get("cuts", []))]
    containers.sort(key=lambda r: -sum(c["words"] for c in r["cuts"]))
    add("## Containers: what was cut out of each")
    add("")
    add("| file | words in | works found inside | words cut | intros and headings removed | words kept |")
    add("|---|---:|---:|---:|---:|---:|")
    for r in containers:
        works = [c for c in r["cuts"] if c.get("counterpart")]
        extra = sum(c["words"] for c in r["cuts"] if not c.get("counterpart"))
        add(f"| {titles.show(r)} | {n(r['words'])} | {len(works)} | {n(sum(c['words'] for c in works))} | "
            f"{n(extra)} | {n(r['words_out'])} |")
    add("")
    stranded = [(r, m) for r in plan for m in r.get("remnants", []) if m["words"] <= 600]
    add("### Remnants kept beside or between cuts")
    add("")
    add(f"Unmatched text stranded next to a cut stays in the output unless it is nothing but headings; these are "
        f"the ones under 600 words ({len(stranded)}).")
    add("")
    for r, m in sorted(stranded, key=lambda item: (key_of(item[0]), item[1]["units"])):
        add(f"- `{r['source']}:{r['path']}` paragraphs {m['units'][0]}–{m['units'][1]}: {n(m['words'])} words"
            f"{', between two cuts' if m['between_cuts'] else ', at an edge'}")
    add("")

    shelves = [s for s in cfg.sources if s.container and s.ledger]
    if shelves:
        wanted = [" ".join(re.findall(r"[a-z0-9]+", name.casefold())) for name in cfg.report.apparatus]
        add("### Editorial apparatus in container books")
        add("")
        add("Sections of a book that are the editor's and not a story, by the heading the converter's ledger "
            "gives them. They are unique text, so nothing here removes them; the sizes are for deciding by hand.")
        add("")
        add("| book | section | words |")
        add("|---|---|---:|")
        for source in shelves:
            for r in sorted((r for r in plan if r["source"] == source.name), key=key_of):
                record = titles.record(r) or {}
                total = 0
                for section in record.get("sections_kept") or []:
                    start = " ".join(str(section.get("start") or "").split())
                    shape = " ".join(re.findall(r"[a-z0-9]+", start.casefold()))
                    if any(shape == w or shape.startswith(w + " ") for w in wanted) and len(shape.split()) <= 8:
                        add(f"| `{r['path']}` | {start[:60]} | {n(section.get('words', 0))} |")
                        total += section.get("words", 0)
                mine = [shape_of(row) for row in lines[-12:] if row.startswith(f"| `{r['path']}`")]
                for start, count in long_sections(cfg, source, r["path"]):
                    if any(shape_of(start).split()[0] in row.split() for row in mine):
                        continue
                    add(f"| `{r['path']}` | {start} (by its shape in the text) | {n(count)} |")
                    total += count
                if total:
                    add(f"| `{r['path']}` | **all of the above** | {n(total)} of {n(r['words'])} |")
        add("")

    band = sorted((p for p in pairs if p["ambiguous"]),
                  key=lambda p: (-p["matched_words"], key_of(p["a"]), key_of(p["b"])))
    add("## The ambiguous band (no automatic action)")
    add("")
    add(f"{len(band)} pairs, {n(sum(p['matched_words'] for p in band))} matched words: partial overlap that is "
        "neither one work nor clearly two.")
    add("")
    for p in band:
        add(pair_line(p))
    add("")

    reference = [p for p in pairs if "reference" in (kind.get(p["a"]["source"]), kind.get(p["b"]["source"]))]
    if reference:
        add("## Reference shelves (looked up, never cut)")
        add("")
        for p in sorted(reference, key=lambda p: (-p["matched_words"], key_of(p["a"]), key_of(p["b"]))):
            add(pair_line(p))
        add("")

    add("## Boilerplate stripped, per source")
    add("")
    by_source = defaultdict(list)
    for row in boiler:
        by_source[row["source"]].append(row)
    for source in sorted(by_source):
        rows = sorted(by_source[source], key=lambda row: (-row["stripped"], row["key"]))
        add(f"**{source}** — {n(sum(row['words'] for row in rows))} words in {n(sum(row['stripped'] for row in rows))} paragraphs")
        add("")
        for row in rows[:cfg.report.boilerplate_rows]:
            what = {"identical": "identical paragraph", "template": "paragraphs opening like",
                    "carried": "carried along between boilerplate and the edge, e.g."}[row["kind"]]
            add(f"- {row['stripped']}× {what}: “{row['text']}” (`{row['example_path']}`)")
        add("")
    if not by_source:
        add("Nothing stripped.")
        add("")

    add("## Skipped files")
    add("")
    reasons = defaultdict(list)
    for s in skipped:
        reasons[s["reason"]].append(s)
    if not reasons:
        add("None.")
    for reason in sorted(reasons):
        sample = ", ".join(f"`{s['source']}:{s['path']}`" for s in reasons[reason][:5])
        add(f"- {reason}: {len(reasons[reason])} ({sample}{'…' if len(reasons[reason]) > 5 else ''})")
    add("")
    write_atomic(cfg.report_file, "\n".join(lines))
    say(f"report: {cfg.report_file} ({len(lines)} lines); {time.time() - started:.1f}s")
