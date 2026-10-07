import json
import os
import statistics
import sys

N = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "day3"
AS_JSON = "--json" in sys.argv
AS_WEIGHTS = "--weights" in sys.argv
LEDGER = sys.argv[sys.argv.index("--ledger") + 1] if "--ledger" in sys.argv[:-1] else f"night/{N}/ledger.jsonl"
W = 3
FLOOR = 0.004


def evals(path):
    seen, out, weights = set(), [], {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        weights = r.get("weights") or weights
        ev, step = r.get("eval_per_file"), r.get("eval_step")
        if ev and step and step not in seen:
            seen.add(step)
            out.append((step, ev, r.get("train_per_file") or {}))
    return out, weights


def swing(vals):
    return max(FLOOR, 1.5 * statistics.median([abs(b - a) for a, b in zip(vals, vals[1:])]))


def judge(vals):
    band = swing(vals)
    if len(vals) < 2 * W:
        return ("learning" if vals[-1] < vals[0] - band else "flat"), band, None, None
    last = statistics.mean(vals[-W:])
    prev = statistics.mean(vals[-2 * W:-W])
    before = statistics.mean(vals[-3 * W:-2 * W]) if len(vals) >= 3 * W else None
    if last < prev - band:
        verdict = "learning"
    elif last > prev + band:
        verdict = "turned" if before is not None and prev > before + band else "rising"
    else:
        verdict = "flat"
    return verdict, band, last, prev


def running(vals):
    n = 0
    while len(vals) - n >= 2 and judge(vals[:len(vals) - n])[0] == "turned":
        n += 1
    return n


def gap_of(series, v):
    gaps = [(e - t) if t is not None else None for _, e, t in series]
    have = [g for g in gaps if g is not None]
    if not have or gaps[-1] is None:
        return
    v["train"] = series[-1][2]
    v["gap"] = round(gaps[-1], 4)
    last = [g for g in gaps[-W:] if g is not None]
    prev = [g for g in gaps[-2 * W:-W] if g is not None]
    if len(gaps) < 2 * W or len(last) < 2 or len(prev) < 2:
        return
    band = swing(have)
    a, b = statistics.mean(prev), statistics.mean(last)
    v["gap_prev3"], v["gap_last3"], v["gap_band"] = round(a, 4), round(b, 4), round(band, 4)
    v["gap_trend"] = "widening" if b > a + band else "narrowing" if b < a - band else "flat"


def verdicts(rows):
    keys = sorted({k for _, ev, _ in rows for k in ev})
    out = {}
    for k in keys:
        series = [(s, ev[k], tr.get(k)) for s, ev, tr in rows if ev.get(k) is not None]
        vals = [v for _, v, _ in series]
        if len(vals) < 2:
            out[k] = {"verdict": "new", "now": vals[-1] if vals else None}
            continue
        verdict, band, last, prev = judge(vals)
        lo = min(range(len(vals)), key=lambda i: vals[i])
        v = {"now": vals[-1], "first": vals[0], "min": vals[lo], "min_step": series[lo][0], "band": round(band, 4), "evals": len(vals)}
        v["verdict"] = verdict
        if last is not None:
            v["last3"], v["prev3"] = round(last, 4), round(prev, 4)
        if verdict == "turned":
            v["turned_evals"] = running(vals)
            v["confirmed"] = v["turned_evals"] >= 2
        gap_of(series, v)
        if verdict == "turned" and "gap_trend" in v:
            v["reading"] = "memorising" if v["gap_trend"] == "widening" else "drift"
        out[k] = v
    return out


def tail(v):
    s = ""
    if v["verdict"] == "turned":
        s += f" confirmed, {v['turned_evals']} evals running" if v["confirmed"] else " on this eval only"
    if "gap" in v:
        s += f"  gap {v['gap']:+.3f}"
        if "gap_trend" in v:
            s += f" ({v['gap_prev3']:+.3f} -> {v['gap_last3']:+.3f} {v['gap_trend']})"
    if "reading" in v:
        s += "  memorising: held-out up, the gap to training loss widening" if v["reading"] == "memorising" else "  drift or noise: held-out up, the gap to training loss not widening"
    return s


rows, weights = evals(LEDGER)
res = verdicts(rows)
turned = [k for k, v in res.items() if v["verdict"] == "turned"]
confirmed = [k for k in turned if res[k]["confirmed"]]
if AS_WEIGHTS:
    if not confirmed:
        print(f"{N}: no shelf has turned on two evals running; nothing to write")
        sys.exit(0)
    zero = sorted(set(confirmed) | {k for k, w in weights.items() if w == 0})
    doc = json.dumps({k: 0 for k in zero})
    box = os.environ.get("BOX", "BekmemetevVO@ds-dev2.x340.org")
    path = f"{os.environ.get('BOXDIR', '/opt/llama/magdra')}/runs/{N}/weights.json"
    print(doc)
    print(f"printf '%s\\n' '{doc}' | ssh -i \"$KEY\" {box} 'cat > {path}.new && mv {path}.new {path}'")
    for k in confirmed:
        print(f"# {k}: turned{tail(res[k])}")
    left = [k for k, w in weights.items() if w > 0 and k not in zero]
    if weights and not left:
        print("# this would leave no shelf above zero; the trainer will ignore it")
    sys.exit(0)
if AS_JSON:
    print(json.dumps({"evals": len(rows), "last_step": rows[-1][0] if rows else None, "shelves": res, "turned": turned, "confirmed": confirmed}))
else:
    print(f"{N}: {len(rows)} evals, last at step {rows[-1][0] if rows else '-'}")
    order = {"turned": 0, "rising": 1, "flat": 2, "learning": 3, "new": 4}
    for k, v in sorted(res.items(), key=lambda kv: (order[kv[1]["verdict"]], kv[0])):
        if "band" in v:
            print(f"  {k:16} {v['now']:.3f}  min {v['min']:.3f}@{v['min_step']}  band ±{v['band']:.3f}  "
                  f"{v.get('prev3', '-')} -> {v.get('last3', '-')}  {v['verdict'].upper() if v['verdict'] in ('turned', 'rising') else v['verdict']}{tail(v)}")
        else:
            print(f"  {k:16} {v['verdict']}")
    sys.exit(3 if confirmed else 2 if turned else 0)
