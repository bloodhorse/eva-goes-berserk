import random

import shape
from settings import KINDS
from writer import load_plan

from store import write_atomic


def some(words, count, tail=False):
    tokens = words.split()
    if len(tokens) <= count:
        return " ".join(tokens)
    return "… " + " ".join(tokens[-count:]) if tail else " ".join(tokens[:count]) + " …"


def read_paragraphs(cfg, record):
    try:
        with open(cfg.dedupe.out / record["source"] / record["path"], "rb") as f:
            return shape.paragraphs(f.read().decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError):
        return None


def evidence_line(record):
    said = "; ".join(f"{e['signal']} = {e['value']}" + (f" ({e['weight']:+g})" if e.get("weight") else "")
                     for e in record["evidence"])
    return said or "no signal fired"


def file_block(cfg, record):
    R = cfg.review
    paras = read_paragraphs(cfg, record)
    out = [f"### `{record['source']}/{record['path']}`", "",
           f"- **{record['kind']}** — {record['why']}",
           f"- title: {record['title']} · author: {', '.join(record['authors']) or '—'} · {record['words']:,} words "
           f"in {record['paragraphs']:,} paragraphs",
           f"- evidence: {evidence_line(record)}"]
    for note in record.get("overrides", []):
        out.append(f"- override {note['number']}: {note.get('reason', '')}")
    if paras is None:
        out += ["- the file has changed or gone since the plan", ""]
        return out
    text = " ".join(shape.squash(p) for p in paras)
    out += [f"- head: {some(text, R.head_words)}", f"- tail: {some(text, R.tail_words, tail=True)}"]
    for cut in record["cuts"][:6]:
        out.append(f"- cut {cut['paragraphs'][0]}–{cut['paragraphs'][1]} ({cut['reason']}, {cut['words']} words)")
    out.append("")
    return out


def cut_block(cfg, record, cut, paras):
    R = cfg.review
    a, b = cut["paragraphs"]
    inside = " ".join(shape.squash(p) for p in paras[a:b])
    return [f"### `{record['source']}/{record['path']}` paragraphs {a}–{b}: {cut['reason']}, {cut['words']:,} words", "",
            f"- before: {some(shape.squash(paras[a - 1]), R.context_words, tail=True) if a else '(start of file)'}",
            f"- cut opens: {some(inside, R.cut_edge_words)}",
            f"- cut closes: {some(inside, R.cut_edge_words, tail=True)}",
            f"- after: {some(shape.squash(paras[b]), R.context_words) if b < len(paras) else '(end of file)'}", ""]


def run(cfg, say=print):
    R = cfg.review
    plan = load_plan(cfg)
    lines = ["# sieve review", "",
             "The unsure band in full, then a sample of every other decision by source and kind, then a sample of "
             "cuts by source and reason. A wrong one goes into `overrides.toml`.", ""]
    unsure = [r for r in plan if r["kind"] == "unsure"]
    lines += [f"## Unsure: {len(unsure)}", ""]
    for record in unsure:
        lines += file_block(cfg, record)

    strata = {}
    for record in plan:
        if record["kind"] != "unsure":
            strata.setdefault((record["source"], record["kind"]), []).append(record)
    lines += ["## Sample of decisions", ""]
    shown = 0
    for source, kind in sorted(strata, key=lambda key: (key[0], KINDS.index(key[1]))):
        group = sorted(strata[(source, kind)], key=lambda r: r["path"])
        rng = random.Random(f"{R.seed}:{source}:{kind}")
        picked = rng.sample(group, min(R.sample_per_stratum, len(group)))
        lines += [f"## {source}: {kind} ({len(group)} files, {len(picked)} shown)", ""]
        for record in sorted(picked, key=lambda r: r["path"]):
            lines += file_block(cfg, record)
            shown += 1

    cuts = {}
    for record in plan:
        for cut in record["cuts"]:
            cuts.setdefault((record["source"], cut["reason"]), []).append((record, cut))
    lines += ["## Sample of cuts", ""]
    cut_shown = 0
    for source, reason in sorted(cuts):
        group = sorted(cuts[(source, reason)], key=lambda rc: (rc[0]["path"], rc[1]["paragraphs"][0]))
        rng = random.Random(f"{R.seed}:{source}:{reason}")
        picked = rng.sample(group, min(R.cut_samples_per_reason, len(group)))
        lines += [f"## {source}: {reason} ({len(group)} cuts, {sum(c['words'] for _, c in group):,} words, {len(picked)} shown)", ""]
        cache = {}
        for record, cut in sorted(picked, key=lambda rc: (rc[0]["path"], rc[1]["paragraphs"][0])):
            if record["path"] not in cache:
                cache[record["path"]] = read_paragraphs(cfg, record)
            paras = cache[record["path"]]
            if paras is None or len(paras) != record["paragraphs"]:
                lines += [f"### `{record['source']}/{record['path']}`: the file has changed since the plan", ""]
                continue
            lines += cut_block(cfg, record, cut, paras)
            cut_shown += 1
    write_atomic(cfg.review_file, "\n".join(lines) + "\n")
    say(f"review: {cfg.review_file} — {len(unsure)} unsure, {shown} sampled decisions, {cut_shown} sampled cuts")
