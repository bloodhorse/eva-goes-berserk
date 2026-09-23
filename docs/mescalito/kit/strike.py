#!/usr/bin/env python3
"""strike.py: one page per seed, written by a sober llama-server with short struck stretches
from a second one that has a control vector loaded. Stdlib only. Untested against a live server.

  strike.py SEED.txt COND --sober 8080 [--struck 8081] [--p 0.25] [--len 12] [--max 3] >> raw.jsonl

--struck omitted  -> the whole page on --sober (the clean arm)
--sober 8081 alone -> the whole page under the vector (the frozen arm)
Rows are {cond, seed, text, strikes} so blind.py can shuffle them unread.

Why two servers and not one: stock llama-server loads control vectors at start only. The driver
hands the page's token ids back and forth; after a strike the sober server re-reads the struck
words as plain text, so the ground comes back by construction. Token ids, not text, cross the
seam, so nothing gets retokenized differently between the two.
"""
import argparse, json, random, re, urllib.request

SAMPLER = dict(temperature=2.0, min_p=0.08, top_k=0, top_p=1.0,        # temperature runs last
               dry_multiplier=0.8, dry_base=1.75, dry_allowed_length=2,  # the loop brake
               repeat_penalty=1.05, repeat_last_n=512)


def post(port, path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seed"); ap.add_argument("cond")
    ap.add_argument("--sober", type=int, required=True); ap.add_argument("--struck", type=int)
    ap.add_argument("--n", type=int, default=170)      # page length in tokens
    ap.add_argument("--p", type=float, default=0.25)   # chance of a strike at a sentence end
    ap.add_argument("--len", type=int, default=12)     # strike length in tokens
    ap.add_argument("--max", type=int, default=3)      # strikes per page, at most
    ap.add_argument("--chunk", type=int, default=4)    # sober tokens between boundary checks
    ap.add_argument("--rng", type=int, default=1)
    ap.add_argument("--sampler", default="{}")         # json overrides, e.g. OLMo's t3 + xtc
    a = ap.parse_args()
    samp = dict(SAMPLER, **json.loads(a.sampler))
    rng = random.Random(a.rng)
    text = open(a.seed).read()
    ids = post(a.sober, "/tokenize", {"content": text, "add_special": True})["tokens"]
    out, last, strikes, made = "", "", [], 0
    while made < a.n:
        # a strike may start only after a sober stretch that ended a sentence, never on the
        # first token: the frame has to exist before something can arrive in it
        at_end = made > 0 and re.search(r"[.!?\n]", last) is not None
        hit = a.struck and len(strikes) < a.max and at_end and rng.random() < a.p
        port, n = (a.struck, a.len) if hit else (a.sober, a.chunk)
        r = post(port, "/completion", dict(samp, prompt=ids, n_predict=min(n, a.n - made),
                                           cache_prompt=True, return_tokens=True,
                                           seed=rng.randrange(2**31)))
        toks = r.get("tokens") or []
        if hit:
            strikes.append([made, made + len(toks)])   # token span, kept for unblinding only
        ids += toks; out += r.get("content", ""); made += len(toks)
        last = "" if hit else r.get("content", "")
        if not toks or r.get("stop_type") == "eos":
            break
    print(json.dumps({"cond": a.cond, "seed": a.seed, "text": out, "strikes": strikes}))


if __name__ == "__main__":
    main()
