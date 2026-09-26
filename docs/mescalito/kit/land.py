"""Land one dosed page into the stream the way stream.write_page does: a bare room under
stream/<date>/<HHMM>, root = the seed as handed over, one model node = the page, one
kind:page ledger row. No live posts, no heartbeat (no writer ran). Then the voices, in the
writer's order — the reader, the sleeper, the painter through its backlog, the mirror — each a
subprocess the way launchd runs them, each best-effort; `--no-voices` lands and stops.

    uv run --python 3.12 land.py [--no-voices] <page file> <vector> <dose> <rng seed> <tokens> [<seed id>]

<seed id> is the seed's path under shelf/seeds/, "kept/21-1132.txt" (the storm girl) when
omitted; the room's root is that file, lowercased the way the stream hands seeds over.
LAND_UNFLAG=1 lands the page unflagged when flag_of would flag it — the reader, the sleeper and
the painter all skip flagged pages — and keeps the flag it would have had on the node as
flag_overridden.
"""
import json, os, secrets, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "eva", "stream"))
import stream  # noqa: E402  (puts server/ and cli/ on the path)
import eva, loom  # noqa: E402

MODEL_FILE = "Mistral-Nemo-Base-2407.Q5_K_M.gguf"
VOICES = {"reader": ("eva/stream/interpreter.py", "--once"),
          "sleeper": ("eva/stream/remembering.py", "--once"),
          "painter": ("eva/stream/plating.py", "--backlog"),
          "mirror": ("eva/stream/push.py",)}


def land(page, vector, dose, rng, tokens, seed_rel="kept/21-1132.txt"):
    dose, rng, tokens = float(dose), int(rng), int(tokens)
    stamp = f"nemo · {vector}"
    with open(page, encoding="utf-8", newline="") as f:
        raw = f.read()
    eos = " [end of text]" in raw
    text = raw.split(" [end of text]")[0] if eos else raw[:-2] if raw.endswith("\n\n") else raw
    with open(os.path.join(stream.SEEDS, seed_rel), encoding="utf-8", newline="") as f:
        seed = f.read().lower().rstrip(" \t")
    seed_id = "seeds/" + seed_rel

    params = json.loads(json.dumps(eva.PARAMS))
    params.update(n_predict=170, stop=[], temperature=2.0, min_p=0.08, top_k=0, top_p=1.0,
                  repeat_penalty=1.05, repeat_last_n=512, n_probs=1,
                  dry_multiplier=0.8, dry_base=1.75, dry_allowed_length=2, seed=rng)

    started = time.time()
    name = stream.room_name(started)
    sitting = eva.blank(name, is_bare=True, root_text=seed)
    sitting["title"] = "stream · " + time.strftime("%Y-%m-%d %H:%M", time.localtime(started))
    sitting["params"] = params
    flag, overridden = stream.flag_of(text), None
    if os.environ.get("LAND_UNFLAG") == "1" and flag:
        overridden, flag = flag, None
    node = {"id": secrets.token_hex(4), "parent": sitting["root"], "kind": "model",
            "text": text, "ts": time.time(), "pruned": False, "posed": False,
            "meta": {"stop_type": "eos" if eos else "limit", "stopping_word": "",
                     "tokens_predicted": tokens, "tps": 0, "logprobs": [], "params": params,
                     "model": stamp, "model_file": MODEL_FILE, "seed": seed_id, "flag": flag,
                     "substance": vector, "flag_overridden": overridden,
                     "dose": {"vector": vector, "scale": dose, "layer": 10,
                              "llama": f"--control-vector-scaled cv-nemo/{vector}.gguf:{dose} "
                                       "--control-vector-layer-range 9 9"},
                     "source": os.path.relpath(page, loom.SHELF + "/..")}}
    sitting["nodes"][node["id"]] = node
    sitting["current"] = node["id"]
    loom.write_sitting(sitting)
    stream.ledger({"room": name, "seed": seed_id, "temperature": 2.0, "tokens": tokens, "tps": 0,
                   "flag": flag, "seconds": 0, "model": stamp, "substance": vector,
                   "flag_overridden": overridden, "dose": dose})
    print(name, "eos" if eos else "limit", tokens, "flag", flag, repr(text[-40:]), flush=True)
    return name


def voices(*names):
    for n in names or VOICES:
        script, *args = VOICES[n]
        cmd = ["uv", "run", "--python", "3.12", os.path.join(REPO, script), *args]
        try:
            code = subprocess.run(cmd, cwd=REPO, env={"STREAM_READER": "codex", **os.environ}).returncode
        except OSError as exc:
            code = exc
        if code:
            print(f"land · {n} · {code}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    quiet = "--no-voices" in sys.argv
    land(*[a for a in sys.argv[1:] if a != "--no-voices"])
    if not quiet:
        voices()
