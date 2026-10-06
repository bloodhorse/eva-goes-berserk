import json, os, re, sys, time

N = sys.argv[1]
D = f"night/{N}"


def load(name, default):
    try:
        return json.load(open(f"{D}/{name}"))
    except Exception:
        return default


def lines(name):
    try:
        return [l for l in open(f"{D}/{name}").read().splitlines() if l.strip()]
    except Exception:
        return []


def hms(s):
    s = int(s or 0)
    return f"{s // 3600}h {s % 3600 // 60:02d}m"


st = load("status.json", {})
age = time.time() - st.get("unix", 0) if st else None
phase = st.get("phase", "no status yet")
if not st:
    state = "NO STATUS YET"
elif phase in ("done", "stopped"):
    state = phase.upper()
elif age > 600:
    state = f"STALE — last heartbeat {hms(age)} ago"
else:
    state = "ALIVE"
temp = (lines("temp") or ["0 ?"])[-1].split()
out = [f"---\ntitle: \"school — {N}: {state}\"\n---\n"]
out.append(f"Page built {time.strftime('%H:%M')} (the mac's clock). It rebuilds every two minutes while the mac is awake.\n")
if st:
    total = st.get("total_steps") or 0
    pct = 100 * st.get("step", 0) / total if total else 0
    out.append("| | |\n|---|---|")
    out.append(f"| heartbeat | {int(age)} s ago |")
    out.append(f"| progress | step {st.get('step', 0):,} of {total:,} ({pct:.0f}%) |")
    out.append(f"| read so far | {st.get('tokens_seen', 0) / 1e6:,.0f} million tokens |")
    out.append(f"| speed | {st.get('tok_per_s') or 0:,.0f} tokens a second |")
    out.append(f"| time | {hms(st.get('elapsed_s'))} done, {hms(st.get('eta_s'))} to go |")
    out.append(f"| card | {temp[1] if len(temp) > 1 else '?'} °C, {st.get('peak_mem_gib') or 0:.1f} GB peak |")
    tl = st.get("train_loss")
    out.append(f"| loss on what it is reading | {tl:.3f} |" if tl else "| loss on what it is reading | — |")
    for k, v in (st.get("eval_per_file") or {}).items():
        out.append(f"| loss on held-out {k} | {v:.3f} |")
    out.append("")
led = [json.loads(l) for l in lines("ledger.jsonl")]
if led:
    out.append("## the night so far\n\nLower is better. A held-out number that turns and climbs while the others fall is that shelf being memorised.\n")
    keys = sorted({k for r in led for k in (r.get("eval_per_file") or {})})
    out.append("| hours in | read (M) | " + " | ".join(keys) + " |\n|---|---|" + "---|" * len(keys))
    seen = set()
    for r in led:
        h = int((r.get("elapsed_s") or 0) // 1800)
        if h in seen or not r.get("eval_per_file"):
            continue
        seen.add(h)
        out.append(f"| {h / 2:.1f} | {r.get('tokens_seen', 0) / 1e6:,.0f} | " + " | ".join(f"{(r['eval_per_file'].get(k) or 0):.3f}" for k in keys) + " |")
    out.append("")
g = lines("guard.log")
if g:
    out.append("## guard\n\n```\n" + "\n".join(g[-10:]) + "\n```\n")
sm = [json.loads(l) for l in lines("samples.jsonl")]
steps = sorted({s["step"] for s in sm}, reverse=True)
keep = steps[:2] + [s for i, s in enumerate(steps[2:]) if i % 3 == 0]
if steps:
    out.append("## what it writes\n\nThe same four seeds at each save, newest first. In bold is the seed's last sentence (the seeds are paragraphs); the rest is the model's, drawn raw at temperature 1 with no cut-off.\n")
for s in keep:
    rows = [x for x in sm if x["step"] == s]
    out.append(f"### after {rows[0]['tokens_seen'] / 1e6:,.0f} million tokens (step {s:,})\n")
    for x in rows:
        text = x["text"].replace("```", "'''")
        tail = re.split(r"(?<=[.!?])\s+", x["prompt"].strip())[-1]
        out.append(f"**…{tail}**\n\n```\n{text.strip()}\n```\n")
print("\n".join(out))
