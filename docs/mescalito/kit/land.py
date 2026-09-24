"""Land one dosed page into the stream the way stream.write_page does: a bare room under
stream/<date>/<HHMM>, root = the seed as handed over, one model node = the page, one
kind:page ledger row. No live posts, no kick, no push, no heartbeat (no writer ran).

    uv run --python 3.12 land.py <page file> <dose> <rng seed>
"""
import json, os, secrets, sys, time
sys.path.insert(0, "/Users/bekh/tower/forge/eva-goes-berserk/eva/stream")
import stream  # noqa: E402  (puts server/ and cli/ on the path)
import eva, loom  # noqa: E402

SEED_ID = "seeds/kept/21-1132.txt"
STAMP = "nemo · voices"
SUBSTANCE = "169x75v"
VECTOR = "169_f199"
MODEL_FILE = "Mistral-Nemo-Base-2407.Q5_K_M.gguf"

page, dose, rng = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
raw = open(page, encoding="utf-8", newline="").read()
# llama-completion's own tail: " [end of text]\n" on eos, then "\n\n" always.
eos = " [end of text]" in raw
text = raw.split(" [end of text]")[0] if eos else raw[:-2] if raw.endswith("\n\n") else raw
seed_path = os.path.join(stream.SEEDS, "kept/21-1132.txt")
seed = open(seed_path, encoding="utf-8", newline="").read().lower().rstrip(" \t")
assert seed == open("/Users/bekh/tower/forge/eva-goes-berserk/docs/olmo-seeds/2026-09-21-1650.txt",
                    encoding="utf-8", newline="").read()
tokens = int(sys.argv[4])

params = json.loads(json.dumps(eva.PARAMS))
params.update(n_predict=170, stop=[], temperature=2.0, min_p=0.08, top_k=0, top_p=1.0,
              repeat_penalty=1.05, repeat_last_n=512, n_probs=1,
              dry_multiplier=0.8, dry_base=1.75, dry_allowed_length=2, seed=rng)

started = time.time()
name = stream.room_name(started)
sitting = eva.blank(name, is_bare=True, root_text=seed)
sitting["title"] = "stream · " + time.strftime("%Y-%m-%d %H:%M", time.localtime(started))
sitting["params"] = params
flag = stream.flag_of(text)
node = {"id": secrets.token_hex(4), "parent": sitting["root"], "kind": "model",
        "text": text, "ts": time.time(), "pruned": False, "posed": False,
        "meta": {"stop_type": "eos" if eos else "limit", "stopping_word": "",
                 "tokens_predicted": tokens, "tps": 0, "logprobs": [], "params": params,
                 "model": STAMP, "model_file": MODEL_FILE, "seed": SEED_ID, "flag": flag,
                 "substance": SUBSTANCE,
                 "dose": {"vector": VECTOR, "scale": dose, "layer": 10,
                          "llama": f"--control-vector-scaled cv-nemo/{VECTOR}.gguf:{dose} "
                                   "--control-vector-layer-range 9 9"},
                 "source": os.path.relpath(page, loom.SHELF + "/..")}}
sitting["nodes"][node["id"]] = node
sitting["current"] = node["id"]
loom.write_sitting(sitting)
stream.ledger({"room": name, "seed": SEED_ID, "temperature": 2.0, "tokens": tokens, "tps": 0,
               "flag": flag, "seconds": 0, "model": STAMP, "substance": SUBSTANCE,
               "dose": dose})
print(name, "eos" if eos else "limit", tokens, "flag", flag, repr(text[-40:]))
