import json, os, subprocess, sys, threading, time

N = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "night1"
ONCE = "--once" in sys.argv
BOX = os.environ.get("BOX", "BekmemetevVO@ds-dev2.x340.org")
BOXDIR = os.environ.get("BOXDIR", "/opt/llama/magdra")
KEY = ["-i", os.environ["KEY"]] if os.environ.get("KEY") else []
R, BOLD = "\033[0m", "\033[1m"
MINT, MINT_HI, MINT_LO = "\033[36m", "\033[1;36m", "\033[2;36m"
PINK, LBLUE = "\033[95m", "\033[94m"
CLEAR, HIDE, SHOW = "\033[H\033[J", "\033[?25l", "\033[?25h"
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
CMD = (f"cd {BOXDIR} && echo @@status && cat runs/{N}/status.json 2>/dev/null; echo; echo @@temp && "
       f"nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw,memory.used --format=csv,noheader,nounits; "
       f"echo @@guard && tail -n 4 runs/{N}.guard.log 2>/dev/null; echo @@log && tail -n 1 runs/{N}.log 2>/dev/null; "
       f"echo @@disk && df --output=avail -BG / | tail -1; echo @@now && date +%s")
S = {"st": {}, "temp": "", "guard": [], "log": "", "disk": "", "skew": 0.0, "ok": None, "polled": 0.0, "err": "",
     "moved": time.time(), "step": None, "evals": {}, "prev": {}}


def poll():
    try:
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", *KEY, BOX, CMD], capture_output=True, text=True,
                           timeout=25, stdin=subprocess.DEVNULL)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.strip().splitlines()[-1] if p.stderr.strip() else f"ssh exit {p.returncode}")
        parts, key = {}, None
        for line in p.stdout.splitlines():
            if line.startswith("@@"):
                key = line[2:]
                parts[key] = []
            elif key:
                parts[key].append(line)
        raw = "\n".join(parts.get("status", [])).strip()
        st = json.loads(raw) if raw else {}
        if st.get("step") != S["step"]:
            S["step"], S["moved"] = st.get("step"), time.time()
        ev = st.get("eval_per_file") or {}
        if ev and ev != S["evals"]:
            S["prev"], S["evals"] = S["evals"], ev
        S.update(st=st, temp=(parts.get("temp") or [""])[0], guard=parts.get("guard", []), log=(parts.get("log") or [""])[-1],
                 disk=(parts.get("disk") or [""])[0].strip(), ok=True, err="", polled=time.time())
        now = (parts.get("now") or [""])[0].strip()
        if now.isdigit():
            S["skew"] = time.time() - int(now)
    except Exception as e:
        S.update(ok=False, err=str(e)[:70], polled=time.time())


def loop():
    while True:
        poll()
        time.sleep(15)


def hms(s):
    s = int(s or 0)
    return f"{s // 3600}h {s % 3600 // 60:02d}m {s % 60:02d}s"


def render(spin):
    st, w, out = S["st"], 62, []
    out.append(f"{BOLD}{MINT}SCHOOL{R} {MINT}{spin}{R}  {N}   {LBLUE}{time.strftime('%H:%M:%S')}{R}")
    out.append(LBLUE + "─" * w + R)
    if S["ok"] is None:
        out.append(f"{LBLUE}● probing the box…{R}")
    elif not S["ok"]:
        out.append(f"{PINK}● PROBE FAILED{R}   {LBLUE}{S['err']} · {int(time.time() - S['polled'])} s ago (vpn?){R}")
    else:
        out.append(f"{MINT_LO}● probe ok{R}   {LBLUE}{int(time.time() - S['polled'])} s ago{R}")
    if not st:
        out.append(f"{LBLUE}● NO HEARTBEAT{R}   {LBLUE}no status file yet — not started?{R}")
        return "\n".join(out)
    age = time.time() - S["skew"] - st.get("unix", 0)
    phase = st.get("phase", "?")
    if phase == "done":
        out.append(f"{MINT_HI}● DONE{R}   {LBLUE}finished {hms(age)} ago{R}")
    elif phase == "stopped":
        out.append(f"{PINK}● STOPPED{R}   {LBLUE}{hms(age)} ago — the wrapper restarts it unless it was told to stop{R}")
    elif age < 90:
        out.append(f"{MINT_HI}● ALIVE{R}   {LBLUE}heartbeat {int(age)} s ago · stage: {phase}{R}")
    elif age < 600:
        out.append(f"{PINK}● LAGGING{R}   {LBLUE}heartbeat {int(age)} s ago · stage: {phase} (saving, evaluating or paused by the guard){R}")
    else:
        out.append(f"{BOLD}{PINK}● STALE — maybe dead{R}   {LBLUE}heartbeat {hms(age)} ago{R}")
    still = time.time() - S["moved"]
    if phase in ("done", "stopped"):
        pass
    elif still < 120:
        out.append(f"{MINT_HI}● MOVING{R}   {LBLUE}step changed {int(still)} s ago{R}")
    else:
        out.append(f"{PINK}● NOT MOVING{R}   {LBLUE}same step for {hms(still)}{R}")
    total, step = st.get("total_steps") or 0, st.get("step") or 0
    frac = step / total if total else 0
    fill = int(frac * (w - 12))
    out.append("")
    out.append(f"  [{MINT_HI}{'█' * fill}{LBLUE}{'░' * (w - 12 - fill)}{R}] {MINT_HI}{frac * 100:5.1f}%{R}")
    out.append(f"  step {step:,} of {total:,}   {LBLUE}·  {st.get('tokens_seen', 0) / 1e6:,.0f} M tokens read{R}")
    out.append(f"  {MINT}{st.get('tok_per_s') or 0:,.0f} tok/s{R}   {LBLUE}{hms(st.get('elapsed_s'))} done · {hms(st.get('eta_s'))} to go{R}")
    out.append("")
    tl = st.get("train_loss")
    out.append(f"  loss, reading    {MINT_HI}{tl:.3f}{R}" if tl else f"  loss, reading    {LBLUE}—{R}")
    for k, v in (st.get("eval_per_file") or {}).items():
        p = S["prev"].get(k)
        mark = f"{LBLUE}·{R}" if p is None else (f"{MINT_HI}↓{R}" if v < p else f"{PINK}↑{R}")
        out.append(f"  held-out {k:<8} {MINT if p is None or v < p else PINK}{v:.3f}{R} {mark}   {LBLUE}at step {st.get('eval_step') or 0:,}{R}")
    out.append("")
    t = [x.strip() for x in S["temp"].split(",")]
    if len(t) == 4:
        hot = t[0].isdigit() and int(t[0]) >= 85
        out.append(f"  card  {PINK if hot else MINT}{t[0]} °C{R}   {LBLUE}{t[1]}% busy · {float(t[2]):.0f} W · {int(t[3]) / 1024:.1f} GB · disk {S['disk']} free{R}")
    for g in S["guard"][-3:]:
        bad = any(x in g for x in ("paused", "restart", "skipped", "failed", "gave up"))
        out.append(f"  {PINK if bad else LBLUE}{g[:w]}{R}")
    return "\n".join(out)


if ONCE:
    poll()
    print(render(SPIN[0]))
    sys.exit()
threading.Thread(target=loop, daemon=True).start()
sys.stdout.write(HIDE)
try:
    i = 0
    while True:
        sys.stdout.write(CLEAR + render(SPIN[i % len(SPIN)]) + "\n")
        sys.stdout.flush()
        i += 1
        time.sleep(0.25)
except KeyboardInterrupt:
    pass
finally:
    sys.stdout.write(SHOW)
