import json, os, random, re, sys, time, urllib.request

U = "http://127.0.0.1:8083/completion"
PULL, PULLS, FLOOR = 40, 10, 8
BOUND = re.compile(r"(?<=[.!?])[\"”’')]*\s+")
WORD = re.compile(r"[^\W\d_]+(?:[’'][^\W\d_]+)*")


def cut(text):
    starts = [0] + [m.end() for m in BOUND.finditer(text)]
    for s in reversed(starts):
        if len(text[s:].split()) >= FLOOR:
            return s
    return 0


def seen(text, rng):
    c = cut(text)
    words = [w.lower() for w in WORD.findall(text[:c])]
    rng.shuffle(words)
    tail = text[c:].rstrip(" \t")
    return (" ".join(words) + " " + tail) if words else tail


def pull(prompt, seed):
    body = {"prompt": prompt, "n_predict": PULL, "temperature": 2.2, "min_p": 0.08, "top_k": 0, "top_p": 1.0,
            "repeat_penalty": 1.05, "repeat_last_n": 512, "dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 2,
            "seed": seed, "cache_prompt": False, "ignore_eos": True}
    req = urllib.request.Request(U, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=1800))


if __name__ == "__main__":
    out, path, draws = sys.argv[1], sys.argv[2], int(sys.argv[3])
    os.makedirs(out, exist_ok=True)
    name = os.path.basename(path)[:-4]
    start = open(path).read().rstrip(" \t")
    if out == "-":
        print(seen(start, random.Random(1)))
        sys.exit()
    for d in range(1, draws + 1):
        rng = random.Random(d)
        text, t = start, time.time()
        saw = open(f"{out}/{name}-draw{d}.saw.jsonl", "w")
        for p in range(PULLS):
            prompt = seen(text, rng)
            r = pull(prompt, d * 1000 + p)
            saw.write(json.dumps({"pull": p, "prompt": prompt, "wrote": r["content"]}, ensure_ascii=False) + "\n")
            saw.flush()
            text += r["content"]
            open(f"{out}/{name}-draw{d}.txt", "w").write(text[len(start):])
            tm = r["timings"]
            print("draw", d, "pull", p, "| wall", round(time.time() - t), "s | read", tm["prompt_n"], "tok at", round(tm["prompt_per_second"], 1),
                  "/s | wrote", tm["predicted_n"], "at", round(tm["predicted_per_second"], 2), "/s", flush=True)
    print("SHUFFLE-DONE", flush=True)
