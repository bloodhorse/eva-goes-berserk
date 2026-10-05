import json, os, sys, time, urllib.request

U, out = sys.argv[1].rstrip("/") + "/completion", sys.argv[2]
os.makedirs(out, exist_ok=True)
for path in sys.argv[3:]:
    name = os.path.basename(path)[:-4]
    body = {"prompt": open(path).read().rstrip(" \t"), "n_predict": 170, "temperature": 2.2, "min_p": 0.08, "top_k": 0, "top_p": 1.0,
            "repeat_penalty": 1.05, "repeat_last_n": 512, "dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 2,
            "seed": 1, "cache_prompt": False}
    t = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=600))
    open(f"{out}/{name}.txt", "w").write(r["content"])
    tm = r["timings"]
    print(os.path.basename(out), name, "| wall", round(time.time() - t), "s | wrote", tm["predicted_n"], "tok at", round(tm["predicted_per_second"], 1), "/s | stop", r.get("stop_type"), flush=True)
