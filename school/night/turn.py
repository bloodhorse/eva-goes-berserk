import json
import statistics
import sys

N = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "day3"
AS_JSON = "--json" in sys.argv
W = 3


def evals(path):
    seen, out = set(), []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        ev, step = r.get("eval_per_file"), r.get("eval_step")
        if ev and step and step not in seen:
            seen.add(step)
            out.append((step, ev))
    return out


def verdicts(rows):
    keys = sorted({k for _, ev in rows for k in ev})
    out = {}
    for k in keys:
        series = [(s, ev[k]) for s, ev in rows if ev.get(k) is not None]
        vals = [v for _, v in series]
        if len(vals) < 2:
            out[k] = {"verdict": "new", "now": vals[-1] if vals else None}
            continue
        deltas = [abs(b - a) for a, b in zip(vals, vals[1:])]
        band = max(0.004, 1.5 * statistics.median(deltas))
        lo = min(range(len(vals)), key=lambda i: vals[i])
        v = {"now": vals[-1], "first": vals[0], "min": vals[lo], "min_step": series[lo][0], "band": round(band, 4), "evals": len(vals)}
        if len(vals) < 2 * W:
            v["verdict"] = "learning" if vals[-1] < vals[0] - band else "flat"
        else:
            last = statistics.mean(vals[-W:])
            prev = statistics.mean(vals[-2 * W:-W])
            before = statistics.mean(vals[-3 * W:-2 * W]) if len(vals) >= 3 * W else None
            if last < prev - band:
                v["verdict"] = "learning"
            elif last > prev + band:
                v["verdict"] = "turned" if before is not None and prev > before + band else "rising"
            else:
                v["verdict"] = "flat"
            v["last3"], v["prev3"] = round(last, 4), round(prev, 4)
        out[k] = v
    return out


rows = evals(f"night/{N}/ledger.jsonl")
res = verdicts(rows)
if AS_JSON:
    print(json.dumps({"evals": len(rows), "last_step": rows[-1][0] if rows else None, "shelves": res}))
else:
    print(f"{N}: {len(rows)} evals, last at step {rows[-1][0] if rows else '-'}")
    order = {"turned": 0, "rising": 1, "flat": 2, "learning": 3, "new": 4}
    for k, v in sorted(res.items(), key=lambda kv: (order[kv[1]["verdict"]], kv[0])):
        if "band" in v:
            print(f"  {k:16} {v['now']:.3f}  min {v['min']:.3f}@{v['min_step']}  band ±{v['band']:.3f}  "
                  f"{v.get('prev3', '-')} -> {v.get('last3', '-')}  {v['verdict'].upper() if v['verdict'] in ('turned', 'rising') else v['verdict']}")
        else:
            print(f"  {k:16} {v['verdict']}")
    sys.exit(2 if any(v["verdict"] == "turned" for v in res.values()) else 0)
