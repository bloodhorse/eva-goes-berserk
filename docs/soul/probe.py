import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

U, out, prompt, n = sys.argv[1].rstrip("/") + "/completion", sys.argv[2], sys.argv[3], int(sys.argv[4])
os.makedirs(out, exist_ok=True)


def post(body):
    req = urllib.request.Request(U, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))


def draw(i):
    r = post({"prompt": prompt, "n_predict": 60, "temperature": 1.0, "top_k": 0, "top_p": 1.0, "min_p": 0,
              "repeat_penalty": 1.0, "seed": i, "cache_prompt": False})
    open(f"{out}/{i}.txt", "w").write(r["content"])


with ThreadPoolExecutor(4) as ex:
    list(ex.map(draw, range(1, n + 1)))
r = post({"prompt": prompt, "n_predict": 1, "temperature": 1.0, "n_probs": 24, "cache_prompt": False})
json.dump(r["completion_probabilities"][0], open(f"{out}/next.json", "w"))
print(os.path.basename(out), "done", n, flush=True)
