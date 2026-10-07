import json, os, re, subprocess, sys, tempfile, time

N = sys.argv[1]
BUDGET = float(os.environ.get("METER_BUDGET", "100"))
EACH = float(os.environ.get("METER_EACH", "40"))
UV = os.environ.get("METER_UV", "/opt/homebrew/bin/uv")
D = f"night/{N}"
OUT, ERR = f"{D}/meter.jsonl", f"{D}/meter.err"
HERE = os.getcwd()


def rows(name):
    try:
        return [json.loads(l) for l in open(f"{D}/{name}", encoding="utf-8") if l.strip()]
    except OSError:
        return []


def stepof(snap):
    m = re.search(r"model-(\d+)-", snap)
    return int(m.group(1)) if m else 0


def lookup(text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as f:
        f.write(text)
    try:
        r = subprocess.run([UV, "run", "-q", "--python", "3.12", "dedupe.py", "lookup", "--json", f.name],
                           cwd=f"{HERE}/dedupe", capture_output=True, text=True, timeout=EACH, stdin=subprocess.DEVNULL)
    finally:
        os.unlink(f.name)
    if r.returncode != 0:
        raise RuntimeError((r.stderr.strip().splitlines() or [f"lookup exited {r.returncode}"])[-1])
    return json.loads(r.stdout)


def measure(prompt, text, seed_words):
    joined = prompt + text if text[:1].isspace() or not text[:1].isalnum() else prompt + " " + text
    found = lookup(joined)
    hers = max(0, found["words"] - seed_words)
    runs, inside = [], 0
    for run in found["runs"]:
        mine = run["from_word"] + run["words"] - max(run["from_word"], seed_words)
        sources = [{"source": s["source"], "path": s["path"], "words": s["words"]} for s in run["sources"] if s["verified"]]
        if mine < 1 or not sources:
            continue
        inside += mine
        runs.append({"words": run["words"], "hers": mine, "text": run["text"], "sources": sources, "more": run["more_documents"]})
    return {"words": hers, "in_runs": inside, "score": round(inside / hers, 4) if hers else 0.0, "runs": runs, "seconds": found["seconds"]}


def main():
    started = time.time()
    loomed, samples, done = rows("loomed.jsonl"), rows("samples.jsonl"), rows("meter.jsonl")
    have = {(r["snapshot"], r["kind"], r["prompt"]) for r in done}
    seeds = {r["prompt"]: r["seed_words"] for r in done}
    snaps = list(dict.fromkeys(r["snapshot"] for r in loomed))
    todo = []
    for snap in reversed(snaps):
        step = stepof(snap)
        todo += [(snap, step, "loom", r["prompt"], r["text"]) for r in loomed if r["snapshot"] == snap]
        todo += [(snap, step, "raw", r["prompt"], r["text"]) for r in samples if r["step"] == step]
    todo = [t for t in todo if (t[0], t[2], t[3]) not in have]
    made = 0
    for snap, step, kind, prompt, text in todo:
        if time.time() - started > BUDGET:
            break
        if (snap, kind, prompt) in have:
            continue
        t0 = time.time()
        if prompt not in seeds:
            seeds[prompt] = lookup(prompt)["words"]
        record = {"snapshot": snap, "step": step, "kind": kind, "prompt": prompt, "time": time.time(), "seed_words": seeds[prompt]}
        record.update(measure(prompt, text, seeds[prompt]))
        record["wall"] = round(time.time() - t0, 2)
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        have.add((snap, kind, prompt))
        made += 1
    if os.path.exists(ERR):
        os.replace(ERR, ERR + ".last")
    print(json.dumps({"made": made, "left": len(todo) - made, "seconds": round(time.time() - started, 1)}))


try:
    main()
except Exception as e:
    with open(ERR, "w") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {type(e).__name__}: {str(e)[:300]}\n")
    sys.exit(1)
