import json

from settings import KINDS
from writer import load_plan

from store import read_jsonl, write_atomic

TRAINABLE = ("fiction", "mixed", "unsure")


def n(value):
    return f"{int(round(value)):,}"


def read_run(cfg):
    try:
        with open(cfg.state / "run.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def fiction_words(record):
    if record["kind"] == "fiction":
        return record["words_out"]
    if record["kind"] == "mixed":
        return record["words_out"] - record.get("words_nonfiction_kept", 0)
    return 0


def tally(plan):
    out = {}
    for r in plan:
        s = out.setdefault(r["source"], {"files": {k: 0 for k in KINDS}, "words": {k: 0 for k in KINDS},
                                         "words_in": 0, "fiction": 0, "kept_essays": 0, "cut": {}, "unsure_out": 0})
        s["files"][r["kind"]] += 1
        s["words"][r["kind"]] += r["words"]
        s["words_in"] += r["words"]
        s["fiction"] += fiction_words(r)
        s["kept_essays"] += r.get("words_nonfiction_kept", 0) if r["kind"] == "mixed" else 0
        if r["kind"] == "unsure":
            s["unsure_out"] += r["words_out"]
        for cut in r["cuts"]:
            s["cut"][cut["reason"]] = s["cut"].get(cut["reason"], 0) + cut["words"]
    return out


def run(cfg, say=print):
    plan = load_plan(cfg)
    info = read_run(cfg)
    rate = cfg.report.tokens_per_word
    by_source = tally(plan)
    lines = ["# sieve report", ""]
    dedupe = info.get("dedupe", {})
    lines += [f"Plan made {info.get('made_at', '?')} in {info.get('seconds', '?')} s from the deduper's copy: "
              f"`{dedupe.get('plan', '?')}` of {dedupe.get('plan_mtime', '?')} with {n(dedupe.get('plan_records') or 0)} records "
              f"(its ledger: {dedupe.get('ledger_mtime', '?')}). {n(len(plan))} files read, {n(info.get('skipped', 0))} skipped."]
    if info.get("dedupe_moved_during_run"):
        lines += ["", "**The deduper's plan or ledger changed while this plan was being made. Run `plan` again.**"]
    lines += ["", f"Words are whitespace words; tokens are words × {rate}. *Fiction surviving* is what `out/fiction/` holds "
              "after the cuts, plus the fiction part of `out/mixed/` (a book that keeps its essays). "
              "*Unsure* is kept, with its cuts, in `out/unsure/` and is not in the fiction column.", ""]

    lines += ["## Totals by pile", "",
              "| pile | files | words in | fiction surviving | fiction tokens | unsure words | non-fiction | verse | stub | cut out of fiction |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    groups = list(cfg.groups) + ["other"]
    grand = {"files": 0, "in": 0, "fiction": 0, "unsure": 0, "non": 0, "verse": 0, "stub": 0, "cut": 0}
    for group in groups:
        names = [s for s in by_source if cfg.group(s) == group]
        if not names:
            continue
        row = {"files": sum(sum(by_source[s]["files"].values()) for s in names),
               "in": sum(by_source[s]["words_in"] for s in names),
               "fiction": sum(by_source[s]["fiction"] for s in names),
               "unsure": sum(by_source[s]["unsure_out"] for s in names),
               "non": sum(by_source[s]["words"]["nonfiction"] + by_source[s]["kept_essays"] for s in names),
               "verse": sum(by_source[s]["words"]["verse"] for s in names),
               "stub": sum(by_source[s]["words"]["stub"] for s in names),
               "cut": sum(sum(by_source[s]["cut"].values()) for s in names)}
        for key in grand:
            grand[key] += row[key]
        lines.append(f"| {group} | {n(row['files'])} | {n(row['in'])} | {n(row['fiction'])} | {n(row['fiction'] * rate)} | "
                     f"{n(row['unsure'])} | {n(row['non'])} | {n(row['verse'])} | {n(row['stub'])} | {n(row['cut'])} |")
    lines.append(f"| **all** | {n(grand['files'])} | {n(grand['in'])} | **{n(grand['fiction'])}** | **{n(grand['fiction'] * rate)}** | "
                 f"{n(grand['unsure'])} | {n(grand['non'])} | {n(grand['verse'])} | {n(grand['stub'])} | {n(grand['cut'])} |")

    lines += ["", "## By source", "",
              "| source | pile | files | words in | fiction files | fiction surviving | fiction tokens | non-fiction files / words | "
              "verse files / words | stub files / words | mixed files | unsure files / words | words cut |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for source in sorted(by_source):
        s = by_source[source]
        lines.append(
            f"| {source} | {cfg.group(source)} | {n(sum(s['files'].values()))} | {n(s['words_in'])} | {n(s['files']['fiction'])} | "
            f"{n(s['fiction'])} | {n(s['fiction'] * rate)} | {n(s['files']['nonfiction'])} / {n(s['words']['nonfiction'] + s['kept_essays'])} | "
            f"{n(s['files']['verse'])} / {n(s['words']['verse'])} | {n(s['files']['stub'])} / {n(s['words']['stub'])} | "
            f"{n(s['files']['mixed'])} | {n(s['files']['unsure'])} / {n(s['unsure_out'])} | {n(sum(s['cut'].values()))} |")

    lines += ["", "## Words cut, by source and reason", ""]
    reasons = sorted({reason for s in by_source.values() for reason in s["cut"]})
    if reasons:
        lines += ["| source | " + " | ".join(reasons) + " |", "|---|" + "---:|" * len(reasons)]
        for source in sorted(by_source):
            cut = by_source[source]["cut"]
            if cut:
                lines.append(f"| {source} | " + " | ".join(n(cut[r]) if r in cut else "" for r in reasons) + " |")
    else:
        lines.append("Nothing was cut.")

    lines += ["", "## Verse, for the owner to decide", "", "| source | poems | words | tokens |", "|---|---:|---:|---:|"]
    for source in sorted(by_source):
        s = by_source[source]
        if s["files"]["verse"]:
            lines.append(f"| {source} | {n(s['files']['verse'])} | {n(s['words']['verse'])} | {n(s['words']['verse'] * rate)} |")
    lines.append(f"| **all** | {n(sum(s['files']['verse'] for s in by_source.values()))} | "
                 f"{n(sum(s['words']['verse'] for s in by_source.values()))} | "
                 f"{n(sum(s['words']['verse'] for s in by_source.values()) * rate)} |")

    books = [r for r in plan if r.get("sections") is not None]
    if books:
        lines += ["", "## Anthologies", "",
                  "A story keeps its title and byline lines; a title left without its story is cut with its note. "
                  "*Stories* are sections with enough text left after their headnote; *essays kept* are "
                  "`nonfiction-kept` sections of a book whose switch is on.", "",
                  "| book | words in | sections | stories | headnotes cut | fiction surviving | essays kept | apparatus cut, words by reason |",
                  "|---|---:|---:|---:|---:|---:|---:|---|"]
        for r in sorted(books, key=lambda r: r["path"]):
            sections = r["sections"]
            by_reason = {}
            for cut in r["cuts"]:
                by_reason[cut["reason"]] = by_reason.get(cut["reason"], 0) + cut["words"]
            said = ", ".join(f"{reason} {n(words)}" for reason, words in sorted(by_reason.items(), key=lambda kv: -kv[1]))
            lines.append(
                f"| {r['path']} | {n(r['words'])} | {len(sections)} | {sum(1 for s in sections if s['kind'] == 'story')} | "
                f"{sum(1 for s in sections if s.get('headnote_words') and not s.get('headnote_kept'))} | {n(fiction_words(r))} | "
                f"{n(r.get('words_nonfiction_kept', 0))} | {said or '—'}{' (kind: ' + r['kind'] + ')' if r['kind'] not in ('fiction', 'mixed') else ''} |")
        flagged = [(r["path"], e) for r in books for e in r["evidence"]]
        if flagged:
            lines += ["", "Flags raised while cutting books:", ""]
            lines += [f"- `{path}`: {e['signal']} — {e['value']}" for path, e in flagged]

    unsure = [r for r in plan if r["kind"] == "unsure"]
    lines += ["", f"## The unsure band: {len(unsure)} files, {n(sum(r['words_out'] for r in unsure))} words", "",
              "Kept, with their edge cuts, in `out/unsure/`. Each wants a pair of eyes and a line in `overrides.toml`.", ""]
    for r in unsure[:cfg.report.unsure_rows]:
        signals = "; ".join(f"{e['signal']} {e['value']}" for e in r["evidence"])
        lines.append(f"- `{r['source']}/{r['path']}` — {r['title']} ({n(r['words'])} words): {r['why']}. {signals}")
    if len(unsure) > cfg.report.unsure_rows:
        lines.append(f"- … and {len(unsure) - cfg.report.unsure_rows} more in `state/plan.jsonl`")

    flagged = [(r, e) for r in plan if r.get("sections") is None for e in r["evidence"]
               if e["signal"] in ("long-tail-after-marker", "edge-cuts-refused")]
    if flagged:
        lines += ["", f"## Edge cuts that were not made: {len(flagged)}", "",
                  "A marker line was found but what follows it is too long to be a note, or the cuts would have left almost nothing.", ""]
        for r, e in flagged[:200]:
            lines.append(f"- `{r['source']}/{r['path']}`: {e['signal']} — {e['value']}")

    applied = [(r, note) for r in plan for note in r.get("overrides", [])]
    problems = [(r, p) for r in plan for p in r.get("override_problems", [])]
    lines += ["", f"## Overrides: {info.get('overrides', len(cfg.overrides))} entries, {len(applied)} applications", ""]
    changed = [(r, note) for r, note in applied if note.get("kind") and note.get("was") != note.get("kind")]
    confirmed = [(r, note) for r, note in applied if note.get("kind") and note.get("was") == note.get("kind")]
    spans = [(r, note) for r, note in applied if "cut" in note or "keep" in note]
    lines.append(f"{len(changed)} changed a kind, {len(confirmed)} confirm what the signals already said, "
                 f"{len(spans)} force a span.")
    moves = {}
    for r, note in changed:
        moves[(note["was"], note["kind"])] = moves.get((note["was"], note["kind"]), 0) + 1
    if moves:
        lines += ["", "| the signals said | the override says | files |", "|---|---|---:|"]
        lines += [f"| {was} | {now} | {count} |" for (was, now), count in sorted(moves.items())]
    if problems:
        lines += ["", "Overrides that could not be applied:", ""]
        lines += [f"- `{r['source']}/{r['path']}`: {p}" for r, p in problems]
    unused = info.get("overrides_unused") or []
    if unused:
        lines += ["", f"Overrides that matched no file ({len(unused)}):", ""]
        lines += [f"- {text}" for text in unused[:cfg.report.override_rows]]

    skipped = read_jsonl(cfg.state / "skipped.jsonl")
    if skipped:
        lines += ["", f"## Skipped: {len(skipped)}", ""]
        lines += [f"- `{s['source']}/{s['path']}`: {s['reason']}" for s in skipped[:200]]

    ledger = read_jsonl(cfg.out / "ledger.jsonl")
    if ledger:
        actions = {}
        for entry in ledger:
            actions[entry["action"]] = actions.get(entry["action"], 0) + 1
        said = ", ".join(f"{count} {action}" for action, count in sorted(actions.items()))
        lines += ["", "## Output", "", f"`out/ledger.jsonl`: {said}. "
                  f"Words written: {n(sum(e['words_out'] for e in ledger))}."]
        if len(ledger) != len(plan):
            lines.append("The ledger is from another plan than this report; run `apply`.")
    write_atomic(cfg.report_file, "\n".join(lines) + "\n")
    say(f"report: {cfg.report_file} — fiction surviving {n(grand['fiction'])} words, {n(grand['fiction'] * rate)} tokens; "
        f"unsure {len(unsure)} files")


def overrides(cfg, say=print):
    plan = load_plan(cfg)
    by_number = {}
    for r in plan:
        for note in r.get("overrides", []):
            by_number.setdefault(note["number"], []).append((r, note))
    for rule in cfg.overrides:
        hits = by_number.get(rule.number, [])
        say(f"{rule.number}. {rule.describe()} — {len(hits)} file(s){': ' + rule.reason if rule.reason else ''}")
        for r, note in hits[:5]:
            was = f" (signals said {note['was']})" if note.get("kind") else ""
            say(f"     {r['source']}/{r['path']}{was}")
    problems = [(r, p) for r in plan for p in r.get("override_problems", [])]
    for r, p in problems:
        say(f"problem: {r['source']}/{r['path']}: {p}")
    say(f"overrides: {len(cfg.overrides)} entries, {sum(1 for rule in cfg.overrides if rule.number not in by_number)} "
        f"matched nothing in the current plan, {len(problems)} problem(s)")
