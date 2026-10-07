import glob
import json
import os
import time
from collections import defaultdict

from store import read_jsonl, write_atomic


class Titles:
    def __init__(self, cfg):
        self.cfg = cfg
        self.ledgers = {}

    def ledger(self, source):
        if source.name not in self.ledgers:
            table = {}
            for path in sorted(glob.glob(str(source.ledger))) if source.ledger else []:
                for record in read_jsonl(path):
                    title = record.get("title")
                    if not title:
                        continue
                    author = record.get("author") or ", ".join(record.get("authors") or [])
                    for key in (record.get("slug"), os.path.splitext(os.path.basename(record.get("file") or ""))[0],
                                record.get("dir"), str(record.get("id", ""))):
                        if key:
                            table.setdefault(str(key), (title, author))
            self.ledgers[source.name] = table
        return self.ledgers[source.name]

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
        if source.ledger:
            return self.ledger(source).get(stem) or self.ledger(source).get(name["path"].rpartition("#")[2])
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
        return (f"- {p['relation']}{' (no action)' if not p['acted'] else ''}: {titles.show(p['a'])} "
                f"[{outcome(p['a'])}, {n(p['words_a'])} w] ↔ {titles.show(p['b'])} "
                f"[{outcome(p['b'])}, {n(p['words_b'])} w] — {n(p['matched_words'])} words matched, "
                f"{p['of_a']:.0%} of the first, {p['of_b']:.0%} of the second")

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
    add("| file | words in | works found inside | words cut | intros, headings, remnants removed | words kept |")
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
    add(f"Unmatched text stranded next to a cut and longer than {cfg.remnants.remnant_max_words} words stays in "
        f"the output; these are the ones under 600 words ({len(stranded)}).")
    add("")
    for r, m in sorted(stranded, key=lambda item: (key_of(item[0]), item[1]["units"])):
        add(f"- `{r['source']}:{r['path']}` paragraphs {m['units'][0]}–{m['units'][1]}: {n(m['words'])} words"
            f"{', between two cuts' if m['between_cuts'] else ', at an edge'}")
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
