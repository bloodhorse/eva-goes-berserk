import html, json, os, re, sys, time

N = sys.argv[1]
D = f"night/{N}"
LIFE = {"day3": [("night1", 659e6), ("day2", 292e6)]}
TEEN = 3.0e9
STYLE = """<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#0d0f0f" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f6f4ee" media="(prefers-color-scheme: light)">
<style>
:root{color-scheme:dark;--bg:#0d0f0f;--fg:#e8ecec;--pink:#f5c8fe;--mint:#b9e8c4;--ctx:#9cc;--card:#131717;--line:#1f2a2a;--line-soft:#161b1b;
--epi-line:#2a3a3a;--said-line:#f5c8fe;--name-glow:0 0 18px rgba(245,200,254,.35);--age-glow:0 0 22px rgba(185,232,196,.25);
--dot-glow:0 0 10px currentColor;--dot-dim:0 0 2px currentColor;--track:#161b1b;--past-a:#4d6b63;--past-b:#5f837a;--now:#b9e8c4;
--now-mark:0 0 12px rgba(185,232,196,.6);--plan-a:#1e2b29;--plan-b:#161b1b;--pre-fg:#cfd8d8;--says-fg:#f1f4f4;--says-bg:#111515;
--says-line:#2f4a44;--dim:.7;--faint:.6;--lo:.55}
@media (prefers-color-scheme: light){:root{color-scheme:light;--bg:#f6f4ee;--fg:#1d2021;--pink:#9a2aa6;--mint:#176c3b;--ctx:#2b6190;--card:#fbfaf6;
--line:#dcd7c9;--line-soft:#e9e5da;--epi-line:#a9c4cf;--said-line:#b452c4;--name-glow:none;--age-glow:none;
--dot-glow:0 0 0 3px #b9e8c4;--dot-dim:0 0 0 1px #b9e8c4;--track:#e8e4d8;--past-a:#6d8b82;--past-b:#527469;--now:#1f7a48;
--now-mark:inset 0 0 0 1px #0d3a22;--plan-a:#9fc7ab;--plan-b:#e8e4d8;--pre-fg:#33393a;--says-fg:#17191a;--says-bg:#fdfcf8;
--says-line:#9cc3aa;--dim:.85;--faint:.85;--lo:.75}}
html{background:var(--bg);color:var(--fg)}
body{font:16px -apple-system,system-ui;background:var(--bg);color:var(--fg);max-width:760px;margin:auto;padding:18px;
padding-top:max(18px,env(safe-area-inset-top));padding-bottom:max(28px,env(safe-area-inset-bottom));hyphens:manual}
header{display:none}
.mono,h2,h3,th,.k{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.name{font:600 34px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.32em;color:var(--pink);margin:6px 0 0;
text-shadow:var(--name-glow)}
.sub{color:var(--ctx);font-size:13px;letter-spacing:.08em;margin:2px 0 14px}
.epi{color:var(--ctx);font-style:italic;border-left:2px solid var(--epi-line);padding:2px 0 2px 12px;margin:0 0 18px;font-size:15px}
.epi b{font-style:normal;font-weight:400;opacity:var(--dim);font-size:12px}
h2{font-weight:500;font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:var(--pink);margin:2.2em 0 .6em;
border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-weight:400;font-size:12px;letter-spacing:.08em;color:var(--ctx);margin:1.6em 0 .4em}
small,.ctx{color:var(--ctx)}
.good{color:var(--mint)}.hi{color:var(--mint);font-weight:700}.lo{color:var(--mint);opacity:var(--lo)}.bad{color:var(--pink);font-weight:700}.rose{color:var(--pink)}
.state{font:600 15px ui-monospace,Menlo,monospace;letter-spacing:.14em;margin:0}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:currentColor;margin-right:8px;
box-shadow:var(--dot-glow);animation:pulse 2.2s ease-in-out infinite}
@keyframes pulse{50%{opacity:.3;box-shadow:var(--dot-dim)}}
.age{font:600 44px ui-monospace,Menlo,monospace;color:var(--mint);margin:18px 0 0;line-height:1;text-shadow:var(--age-glow)}
.age span{font-size:14px;font-weight:400;color:var(--ctx);letter-spacing:.06em;margin-left:8px}
.life{display:flex;height:12px;border-radius:2px;overflow:hidden;background:var(--track);margin:12px 0 4px;outline:1px solid var(--line)}
.life i{display:block;height:12px}.life .past{background:var(--past-a)}.life .past+.past{background:var(--past-b)}
.life .now{background:var(--now);box-shadow:var(--now-mark)}.life .plan{background:repeating-linear-gradient(90deg,var(--plan-a) 0 3px,var(--plan-b) 3px 6px)}
.legend{display:flex;justify-content:space-between;color:var(--ctx);font:11px ui-monospace,Menlo,monospace;letter-spacing:.04em}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:18px 0 0}
.cell{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:10px 12px}
.k{color:var(--ctx);font-size:11px;letter-spacing:.1em;text-transform:uppercase}.v{font:500 19px ui-monospace,Menlo,monospace;margin-top:3px}
.v small{font-size:12px}
table{border-collapse:collapse;border:0;margin:.4em 0;width:100%;font-variant-numeric:tabular-nums}
tbody,thead,tr{border:0 !important}
th{color:var(--ctx);font-weight:400;font-size:11px;letter-spacing:.08em;text-transform:uppercase;text-align:right;padding:4px 6px;border-top:0;border-bottom:1px solid var(--line)}
td{padding:5px 6px;border-bottom:1px solid var(--line-soft);text-align:right;font:14px ui-monospace,Menlo,monospace}
td:first-child,th:first-child{text-align:left;color:var(--fg)}
td svg{display:block;margin-left:auto}
.said{font:italic 19px/1.45 Georgia,'Iowan Old Style',serif;color:var(--fg);margin:14px 0 4px;padding:14px 16px;background:var(--card);
border-left:3px solid var(--said-line);border-radius:0 4px 4px 0}
.said .ctx{color:var(--ctx)}
.said b{font:400 12px ui-monospace,Menlo,monospace;color:var(--ctx);font-style:normal;display:block;margin-top:10px;letter-spacing:.04em}
pre{background:var(--card);color:var(--pre-fg);font:13px/1.5 ui-monospace,Menlo,monospace;padding:10px 12px;border-radius:4px;white-space:pre-wrap;
overflow-wrap:anywhere;border-left:2px solid var(--line);margin:4px 0 12px}
pre.says{font:19px/1.6 Georgia,'Iowan Old Style','Times New Roman',serif;color:var(--says-fg);background:var(--says-bg);padding:14px 16px;margin:6px 0 22px;border-left:2px solid var(--says-line)}
.seed{color:var(--ctx);font:italic 16px/1.4 Georgia,'Iowan Old Style',serif;margin:18px 0 6px}
.foot{color:var(--ctx);opacity:var(--faint);font:11px ui-monospace,Menlo,monospace;margin-top:28px}
</style>
"""


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


def span(cls, text):
    return f'<span class="{cls}">{text}</span>'


def cell(k, v):
    return f'<div class="cell"><div class="k">{k}</div><div class="v">{v}</div></div>'


def spark(vals, w=96, h=22):
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = [(2 + i * (w - 4) / (len(vals) - 1), 2 + (h - 4) * (1 - (v - lo) / rng)) for i, v in enumerate(vals)]
    tone = "good" if vals[-1] <= vals[0] else "rose"
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<svg class="{tone}" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline points="{line}" fill="none" stroke="currentColor" '
            f'stroke-width="1.5" stroke-linejoin="round"/><circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.2" fill="currentColor"/></svg>')


st = load("status.json", {})
age = time.time() - st.get("unix", 0) if st else None
phase = st.get("phase", "no status yet")
if not st:
    state, cls = "NO STATUS YET", "ctx"
elif phase == "done":
    state, cls = "DONE", "hi"
elif phase == "stopped":
    state, cls = "STOPPED", "bad"
elif age > 600:
    state, cls = f"STALE · last heartbeat {hms(age)} ago", "bad"
elif age > 240:
    state, cls = "LAGGING", "rose"
else:
    state, cls = "ALIVE", "hi"
temp = (lines("temp") or ["0 ?"])[-1].split()
out = [f"---\ntitle: \"magdra — {N}\"\n---\n", STYLE]
out.append('<p class="name">MAGDRA</p>')
out.append(f'<p class="sub">{N} · 355M parameters · raised from random weights</p>')
out.append('<p class="epi">“The sky above the port was still maiden in the Mag dra of a situation” <b>— her, twenty-two minutes old</b></p>')
out.append(f'<p class="state {cls}"><span class="dot"></span>{state}</p>\n')
if st:
    total = st.get("total_steps") or 0
    step = st.get("step", 0)
    pct = 100 * step / total if total else 0
    seen = st.get("tokens_seen", 0)
    plan = seen / step * total if step else 0
    past = LIFE.get(N, [])
    before = sum(t for _, t in past)
    life = before + seen
    out.append(f'<p class="age">{life / 1e9:.3f}<span>billion tokens old</span></p>')
    span_total = max(TEEN, before + plan)
    bars = "".join(f'<i class="past" style="width:{100 * t / span_total:.2f}%" title="{n}"></i>' for n, t in past)
    bars += f'<i class="now" style="width:{max(0.4, 100 * seen / span_total):.2f}%"></i>'
    bars += f'<i class="plan" style="width:{100 * max(0, plan - seen) / span_total:.2f}%"></i>'
    out.append(f'<div class="life">{bars}</div>')
    marks = "".join(f"<span>{n}</span>" for n, _ in past) + f"<span>{N} {pct:.1f}%</span><span>teenage ≈ {TEEN / 1e9:.0f} B</span>"
    out.append(f'<div class="legend">{marks}</div>')
    hot = float(temp[1]) if len(temp) > 1 and temp[1].replace(".", "").isdigit() else 0
    tl = st.get("train_loss")
    out.append('<div class="grid">' + "".join([
        cell("this run", f"{span('hi', f'{pct:.1f}%')} <small>step {step:,} of {total:,}</small>"),
        cell("time", f"{hms(st.get('elapsed_s'))} <small>in · {hms(st.get('eta_s'))} to go</small>"),
        cell("speed", f"{(st.get('tok_per_s') or 0) / 1000:.1f}k <small>tokens a second</small>"),
        cell("heartbeat", span("good" if age < 240 else "bad", f"{int(age)} s") + " <small>ago</small>"),
        cell("card", span("bad" if hot >= 85 else "good", (temp[1] if len(temp) > 1 else "?") + " °C") + f" <small>{st.get('peak_mem_gib') or 0:.1f} GB</small>"),
        cell("loss, reading", f"{tl:.3f}" if tl else "—"),
    ]) + "</div>\n")
led = [json.loads(l) for l in lines("ledger.jsonl")]
points, seen_ev = [], set()
for r in led:
    ev = r.get("eval_per_file")
    key = r.get("eval_step") or (r.get("elapsed_s") or 0) // 1800
    if ev and key not in seen_ev:
        seen_ev.add(key)
        points.append(r)
verdict = {}
try:
    import subprocess
    vj = subprocess.run([sys.executable, "night/turn.py", N, "--json"], capture_output=True, text=True, timeout=30)
    verdict = json.loads(vj.stdout).get("shelves", {}) if vj.stdout.strip() else {}
except Exception as e:
    print(f"turn: {e}", file=sys.stderr)
if points:
    keys = sorted({k for r in points for k in r["eval_per_file"]}, key=lambda k: points[-1]["eval_per_file"].get(k) or 9)
    out.append("\n## held-out loss, shelf by shelf\n")
    out.append(f"<small>lower is better · {len(points)} readings · the verdict compares the last three evals with the three before, against the shelf's own swing: learning, flat, rising, or turned (rising twice over — that shelf is done being learned from)</small>\n")
    rows = ['<table><thead><tr><th>shelf</th><th>course</th><th>first</th><th>now</th><th>last step</th><th>verdict</th></tr></thead><tbody>']
    for k in keys:
        vals = [r["eval_per_file"][k] for r in points if r["eval_per_file"].get(k) is not None]
        if not vals:
            continue
        d = vals[-1] - vals[-2] if len(vals) > 1 else 0
        twice = len(vals) > 2 and d > 0 and vals[-2] > vals[-3]
        if abs(d) < 0.0005:
            move = span("ctx", "·")
        elif d < 0:
            move = span("good", f"▼ {abs(d):.3f}")
        else:
            move = span("bad" if twice else "rose", f"▲ {d:.3f}")
        now = span("good" if vals[-1] <= vals[0] else "rose", f"{vals[-1]:.3f}")
        vd = (verdict.get(k) or {}).get("verdict", "")
        vcls = {"learning": "good", "flat": "ctx", "rising": "rose", "turned": "bad"}.get(vd, "ctx")
        vtxt = f"turned · min {verdict[k]['min']:.3f} at step {verdict[k]['min_step']:,}" if vd == "turned" else vd
        rows.append(f"<tr><td>{html.escape(k)}</td><td>{spark(vals)}</td><td>{span('ctx', f'{vals[0]:.3f}')}</td><td>{now}</td><td>{move}</td><td>{span(vcls, vtxt)}</td></tr>")
    rows.append("</tbody></table>")
    out.append("".join(rows) + "\n")


def sentence(text):
    parts = re.findall(r"""[^.!?]+[.!?]+["”’']?""", " ".join(text.split()))
    first = parts[0].strip() if parts else ""
    if len(first) < 40 and len(parts) > 1:
        first += " " + parts[1].strip()
    return first if 25 < len(first) < 220 else ""


def feature(rows):
    short = [(r["prompt"], sentence(r["text"])) for r in rows if len(r["prompt"]) < 60]
    short = [(p, t) for p, t in short if t]
    if short:
        p, t = max(short, key=lambda x: len(x[1]))
        return f'<span class="ctx">{html.escape(p)}</span> {html.escape(t)}'
    best = max((sentence(r["text"]) for r in rows), key=len, default="")
    return html.escape(best)


def loomed():
    cache = f"{D}/loomed.jsonl"
    rows = [json.loads(l) for l in lines("loomed.jsonl")]
    try:
        snap = open(f"models/{N}/latest").read().strip()
    except Exception:
        return rows
    model, tool = f"models/{N}/model-latest-q8_0.gguf", "/opt/homebrew/bin/llama-completion"
    if any(r["snapshot"] == snap for r in rows) or not os.path.exists(model) or not os.path.exists(tool):
        return rows
    seeds = [l.strip() for l in open("night/prompts.txt", encoding="utf-8") if l.strip()]
    import subprocess
    new = []
    for i, seed in enumerate(seeds):
        try:
            r = subprocess.run([tool, "-m", model, "-ngl", "99", "-c", "1024", "-p", seed, "-n", "110", "--temp", "1.0", "--min-p", "0.08",
                                "--top-k", "0", "--top-p", "1", "--dry-multiplier", "0.8", "--dry-base", "1.75", "--dry-allowed-length", "2",
                                "--seed", str(1000 + i), "-no-cnv", "--no-display-prompt", "--simple-io"],
                               capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL)
            text = r.stdout.strip()
        except Exception as e:
            print(f"loomed: {e}", file=sys.stderr)
            text = ""
        if text:
            new.append({"snapshot": snap, "time": time.time(), "prompt": seed, "text": text})
    if new:
        with open(cache, "a", encoding="utf-8") as f:
            for r in new:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows + new


lm = loomed()
snaps = list(dict.fromkeys(r["snapshot"] for r in lm))
sm = [json.loads(l) for l in lines("samples.jsonl")]
steps = sorted({s["step"] for s in sm}, reverse=True)
keep = steps[:2] + [s for i, s in enumerate(steps[2:]) if i % 3 == 0]
def stepof(snap):
    m = re.search(r"model-(\d+)-", snap)
    return int(m.group(1)) if m else 0


if snaps:
    cur = [r for r in lm if r["snapshot"] == snaps[-1]]
    said = feature(cur)
    if said:
        out.append("\n## the last thing she said\n")
        out.append(f'<p class="said">{said}<b>snapshot at step {stepof(snaps[-1]):,} · through the sampler</b></p>\n')
    out.append("\n## through the loom's sampler\n")
    out.append(f"<small>one draw per seed from the newest hourly snapshot (step {stepof(snaps[-1]):,}), the absurd tail cut and a brake on repetition: her fair face · the seed's last sentence in blue</small>\n")
    for r in cur:
        tail = re.split(r"(?<=[.!?])\s+", r["prompt"].strip())[-1]
        out.append(f'<p class="seed">…{html.escape(tail)}</p><pre class="says">{html.escape(r["text"].strip())}</pre>\n')
elif steps:
    newest = [x for x in sm if x["step"] == steps[0]]
    said = feature(newest)
    if said:
        out.append("\n## the last thing she said\n")
        out.append(f'<p class="said">{said}<b>step {steps[0]:,} · raw</b></p>\n')
if steps:
    out.append("\n## raw, at every save\n")
    out.append("<small>the same seeds at each save, newest first, drawn at temperature 1 from all fifty thousand tokens with no cut-off: her worst face</small>\n")
for s in keep:
    rows = [x for x in sm if x["step"] == s]
    out.append(f"\n### after {rows[0]['tokens_seen'] / 1e6:,.0f} million tokens · step {s:,}\n")
    for x in rows:
        tail = re.split(r"(?<=[.!?])\s+", x["prompt"].strip())[-1]
        out.append(f'<p class="seed">…{html.escape(tail)}</p><pre class="says">{html.escape(x["text"].strip())}</pre>\n')
g = lines("guard.log")
if g:
    rows = []
    for l in g[-10:]:
        e = html.escape(l)
        if re.search(r"fail|paused|skipped|gave up|restart", l):
            e = span("bad", e)
        elif re.search(r"snapshot|resumed|guard up", l):
            e = span("good", e)
        rows.append(e)
    out.append("\n## guard\n\n<pre>" + "\n".join(rows) + "</pre>\n")
out.append(f'<p class="foot">built {time.strftime("%H:%M")} on the mac · rebuilds every two minutes while the mac is awake</p>')
print("\n".join(out))
