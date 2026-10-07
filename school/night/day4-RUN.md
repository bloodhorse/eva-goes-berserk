# day4 — the runbook

Copy-paste, in order, runnable without an agent. The recipe and its reasons are `school/day4.md`;
this file is only the hands. Every check prints `MATCH` or `MISMATCH`; on a `MISMATCH` stop and
read the lines above it — nothing after it is safe to run.

Paste this once in the terminal the rest is pasted into (zsh; the VPN up, `KEY` set):

```bash
cd ~/tower/forge/eva-goes-berserk/school
H=BekmemetevVO@ds-dev2.x340.org
hx() { ssh -o ConnectTimeout=15 -i $KEY $H "$@"; }
```

Steps 1–3 only write new files on the host and may be done while `day3` is still running.
Steps 4 onward need `day3` finished.

## 0. the shelves on the mac are the ones the recipe was written from

```bash
uv run -q --python 3.12 --with tokenizers python data/shelves.py build --deep | grep -E "^(modern|anth|serials|verse2|NOTE|contamination)"
[ "$(shasum -a 256 shelves/day4/summary.json | cut -d' ' -f1)" = "96f77d3346318ef0dac8eb8198fad6b422ac076301b1fcddb955f5672830c711" ] \
  && echo "MATCH the shelves are the recipe's" || echo "MISMATCH the input moved since day4.md was written"
```

A `MISMATCH` here means the dedupe or the sieve ran again after the recipe was written: the
shelves are still sound (every later check reads `summary.json`, not this file), but the sizes in
`day4.md` are stale by whatever moved — look at the table the build printed before going on.

## 1. upload the shelves (a)

About 420 MB of text; it lands in `/opt/llama/magdra/data/day4/`, a folder that does not exist yet.

```bash
hx 'ls -d /opt/llama/magdra/data/day4 2>/dev/null && echo "MISMATCH data/day4 already exists" || echo "MATCH data/day4 is free"'
rsync -a --exclude .trash --exclude .tokens.json -e "ssh -i $KEY" shelves/day4/ "${H}:/opt/llama/magdra/data/day4/"
```

Check — file counts, bytes and a sha256 over each folder, against `summary.json`:

```bash
hx 'cd /opt/llama/magdra/data/day4 && python3 -' <<'EOF'
import hashlib, json, os
shelves = json.load(open("summary.json"))["shelves"]
ok = True
for shelf, v in shelves.items():
    for split in ("train", "heldout"):
        d = f"{shelf}/{split}"
        h, n, size = hashlib.sha256(), 0, 0
        for name in sorted(os.listdir(d), key=lambda x: x.encode()):
            if name.endswith(".txt"):
                b = open(f"{d}/{name}", "rb").read()
                h.update(b)
                n += 1
                size += len(b)
        stray = [x for x in os.listdir(d) if not x.endswith(".txt")]
        good = (n, size, h.hexdigest()) == (v[split]["files"], v[split]["bytes"], v[split]["sha256"]) and not stray
        ok = ok and good
        print("MATCH   " if good else "MISMATCH", d, n, "files", size, "bytes", "stray: " + " ".join(stray) if stray else "")
print("UPLOAD", "MATCH" if ok else "MISMATCH")
EOF
```

Then the held-out sets against
the Gutenberg text on the host (fantasy, sci-fi, base). It reads only; about five minutes:

```bash
hx 'cd /opt/llama/magdra/data && nice -n 10 python3 -' <<'EOF'
import hashlib, os, re
from multiprocessing import Pool
WORD = re.compile(r"[a-z0-9]+")
APOS = re.compile(r"(?<=[a-z])['’‘`´](?=[a-z])")
def words(path):
    return WORD.findall(APOS.sub("", open(path, encoding="utf-8", errors="replace").read().lower()))
def grams(ws, stride):
    return [hashlib.blake2b(" ".join(ws[i:i + 8]).encode("ascii", "ignore"), digest_size=8).digest() for i in range(0, len(ws) - 7, stride)]
HELD = {}
for shelf in ("modern", "anth", "serials", "verse2"):
    d = f"day4/{shelf}/heldout"
    for name in os.listdir(d):
        for g in set(grams(words(f"{d}/{name}"), 1)):
            HELD.setdefault(g, set()).add(f"{shelf}/{name}")
def scan(path):
    hits = {}
    for g in grams(words(path), 4):
        for owner in HELD.get(g, ()):
            hits[owner] = hits.get(owner, 0) + 1
    return path, hits
files = [f"{d}/{n}" for d in ("fantasy", "scifi", "base") for n in sorted(os.listdir(d)) if n.endswith(".txt")]
bad = []
with Pool(4) as pool:
    for path, hits in pool.imap_unordered(scan, files, chunksize=16):
        bad += [(n, owner, path) for owner, n in hits.items() if n >= 5]
for n, owner, path in sorted(bad, reverse=True):
    print(f"  {owner} shares {n} sampled runs of eight words with {path}")
print(len(files), "files read;", "HELDOUT MATCH: no held-out work is on the old shelves" if not bad else "HELDOUT MISMATCH")
EOF
```

It was `MATCH` from the mac on 2026-10-07 (against the mac's copies of fantasy and base and a
stream of the host's sci-fi). If it ever says `MISMATCH`, each named work goes to training
instead, on the mac, and the upload is repeated (`--delete` only removes, inside `data/day4/`,
the held-out copy of a file that now sits in `train/`):

```bash
uv run -q --python 3.12 --with tokenizers python data/shelves.py reject SHELF FILE --reason "on an old shelf"
uv run -q --python 3.12 --with tokenizers python data/shelves.py build --deep | grep -E "^(modern|anth|serials|verse2|NOTE|contamination)"
rsync -a --delete --exclude .trash --exclude .tokens.json -e "ssh -i $KEY" shelves/day4/ "${H}:/opt/llama/magdra/data/day4/"
```

with the shelf's name for `SHELF` and the file's name as printed (`modern/x.txt` is shelf
`modern`, file `x.txt`) for `FILE`; then the first check of this step is run again.

## 2. tokenise on the host (b)

`prep.py` is used as it is. Each shelf is two folders, so it is run twice with `--val-frac 0`:
once on `train/` into `bins2/<shelf>.bin`, then on `heldout/` with `--out bins2/<shelf>.val.bin`,
which writes the held-out tokens exactly where the trainer looks for them. **The order matters**
(the first run leaves an empty `.val.bin` that the second replaces). About two minutes.

```bash
hx 'cd /opt/llama/magdra && ls bins2/modern.bin bins2/anth.bin bins2/serials.bin bins2/verse2.bin bins2/anth-rough.bin 2>/dev/null | grep -q . && echo "MISMATCH a day4 bin already exists" || echo "MATCH bins2 has no day4 bins yet"'
```

```bash
hx 'cd /opt/llama/magdra && for s in modern anth serials verse2 anth-rough; do
  nice -n 10 .venv/bin/python prep.py data/day4/$s/train --out bins2/$s.bin --val-frac 0 --workers 4 > bins2/$s.prep.log 2>&1 || echo "FAILED $s train"
  nice -n 10 .venv/bin/python prep.py data/day4/$s/heldout --out bins2/$s.val.bin --val-frac 0 --workers 4 >> bins2/$s.prep.log 2>&1 || echo "FAILED $s heldout"
done; echo PREP4-DONE'
```

Check — token counts and file sizes against `summary.json` (the mac counted them with her
tokenizer the way `prep.py` does):

```bash
hx 'cd /opt/llama/magdra && python3 -' <<'EOF'
import json, os
shelves = json.load(open("data/day4/summary.json"))["shelves"]
ok = True
for shelf, v in shelves.items():
    t = json.load(open(f"bins2/{shelf}.json"))["train_tokens"]
    h = json.load(open(f"bins2/{shelf}.val.json"))["train_tokens"]
    sizes = (os.path.getsize(f"bins2/{shelf}.bin"), os.path.getsize(f"bins2/{shelf}.val.bin"))
    good = (t, h) == (v["train"]["tokens"], v["heldout"]["tokens"]) and sizes == (2 * t, 2 * h) and (h > 1025 or shelf == "anth-rough")
    ok = ok and good
    print("MATCH   " if good else "MISMATCH", shelf, f"train {t:,} (want {v['train']['tokens']:,})", f"held-out {h:,} (want {v['heldout']['tokens']:,})")
print("TOKENS", "MATCH" if ok else "MISMATCH")
EOF
```

Left behind per shelf and harmless: `bins2/<shelf>.val.val.bin` (empty), `bins2/<shelf>.val.json`,
`bins2/<shelf>.val.tokenizer/`, `bins2/<shelf>.prep.log`. `bins2/<shelf>.json` says
`"val_tokens": 0`; nothing reads that field. `anth-rough` has no held-out works, so its
`.val.bin` is empty and the trainer measures nothing for it, as for the cyborg corpus.

## 3. the mix file, multiplied out (c)

The recipe goes into one file on the host, one `bin:weight` per line, in `day4.md`'s order.
`run4.sh` looks for `night/day4/mix.txt` and then `runs/day4/mix.txt`; both are outside git, so
**the tracked copy of the mix is the block below** (and the `MIX=` line in `day4.md`) — change it
here, then write it again. `anth-rough` is on it at 0 on purpose (`day4.md`, *For bekh's
decision*).

```bash
hx 'mkdir -p /opt/llama/magdra/runs/day4 && cat > /opt/llama/magdra/runs/day4/mix.txt' <<'EOF'
bins2/fantasy.bin:409
bins2/scifi.bin:82
bins/anime.bin:123
bins/fanfic.bin:0
bins2/base.bin:82
bins/wired-core.bin:79
bins/wired-bulk.bin:228
bins2/literary.bin:309
bins2/horizons.bin:135
bins2/released.bin:79
bins2/library.bin:151
bins/lain.bin:10
bins/cyborg.bin:2
bins2/horizons-verse.bin:6
bins2/modern.bin:1767
bins2/anth.bin:427
bins2/serials.bin:201
bins2/verse2.bin:2
bins2/anth-rough.bin:0
EOF
```

Check — every shelf's readings worked out from the bins on the host, against the recipe's table:

```bash
hx 'cd /opt/llama/magdra && python3 -' <<'EOF'
import json
STEPS, PER_STEP = 16650, 24576
WANT = {"fantasy": 0.32, "scifi": 0.11, "anime": 0.05, "fanfic": 0.0, "base": 0.02, "wired-core": 1.01, "wired-bulk": 0.21, "literary": 1.0, "horizons": 2.01, "released": 2.0, "library": 2.01, "lain": 1.05, "cyborg": 1.09, "horizons-verse": 0.98, "modern": 2.5, "anth": 2.5, "serials": 1.0, "verse2": 2.05, "anth-rough": 0.0}
mix = [line.split()[0].rsplit(":", 1) for line in open("runs/day4/mix.txt") if line.strip()]
total = sum(float(w) for _, w in mix)
ok = len(mix) == len(WANT) and total == 4092
for path, w in mix:
    name = path.split("/")[-1][:-4]
    n = json.load(open(path[:-4] + ".json"))["train_tokens"]
    reads = float(w) / total * STEPS * PER_STEP / n
    good = name in WANT and abs(reads - WANT[name]) < 0.015
    ok = ok and good
    print("MATCH   " if good else "MISMATCH", f"{name:15} {n / 1e6:8.2f} M  weight {w:>5}  {100 * float(w) / total:6.2f}%  read {reads:5.2f}x  (want {WANT.get(name)})")
print(f"sum of weights {total:g}, {STEPS * PER_STEP / 1e6:.1f} M tokens;", "MIX MATCH" if ok else "MIX MISMATCH")
EOF
```

## 4. day3 has finished and its final save is on the mini (d)

```bash
hx 'cd /opt/llama/magdra && tail -n 1 runs/day3.log | grep -q "^DONE step=84103 " && grep -q "guard down" runs/day3.guard.log && ! pgrep -f "[t]rain.py" > /dev/null \
  && echo "MATCH day3 is DONE, its guard is down, no trainer is alive" || echo "MISMATCH day3 is not finished: $(tail -n 1 runs/day3.log | cut -c1-60)"'
tail -n 1 night/day3/pull.log
a=$(hx 'sha256sum /opt/llama/magdra/runs/day3/ckpt.pt | cut -d" " -f1'); b=$(ssh -o ConnectTimeout=15 bek@100.69.218.90 'sha256sum /srv/music/school-archive/models/day3/ckpt.pt | cut -d" " -f1')
[ -n "$a" ] && [ "$a" = "$b" ] && echo "MATCH the mini holds day3's final save" || echo "MISMATCH the mini's copy is not the final save"
```

The puller's own line in `night/day3/pull.log` says `MATCH` by size; the sha256 above is the
stronger word. On `MISMATCH` the mini has an older save (the puller sleeps six hours): copy it by
hand, about half an hour, and run the check again:

```bash
hx 'cat /opt/llama/magdra/runs/day3/ckpt.pt' | ssh bek@100.69.218.90 'cat > /srv/music/school-archive/models/day3/ckpt.pt.part && mv /srv/music/school-archive/models/day3/ckpt.pt.part /srv/music/school-archive/models/day3/ckpt.pt'
```

Then the final save gets a name of its own on the host, so no later run can write over the
fallback (4.3 GB; `df` first):

```bash
hx 'cd /opt/llama/magdra && [ "$(df --output=avail -BG / | tail -1 | tr -dc 0-9)" -ge 40 ] && echo "MATCH 40 GB free or more" || echo "MISMATCH under 40 GB free"'
hx 'cd /opt/llama/magdra && [ -e ckpt-day3-final.pt ] && echo "ckpt-day3-final.pt is already there" || cp runs/day3/ckpt.pt ckpt-day3-final.pt'
hx 'cd /opt/llama/magdra && [ "$(sha256sum ckpt-day3-final.pt | cut -d" " -f1)" = "$(sha256sum runs/day3/ckpt.pt | cut -d" " -f1)" ] && echo "MATCH ckpt-day3-final.pt is the final save" || echo "MISMATCH"'
```

The card is free and still ours:

```bash
hx 'systemctl is-active llama-server.service | grep -q "^inactive" && [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)" -lt 500 ] && echo "MATCH the card is free" || echo "MISMATCH something holds the card"'
```

## 5. the kit for day4

`run4.sh` and the trainer that re-reads `runs/<name>/weights.json` at every eval and logs a
training loss per shelf are in the repo (`night/run4.sh`, `scratch/train.py`); the host still has
`day3`'s kit. The old kit goes aside first; `guard.sh` is unchanged.

```bash
hx 'cd /opt/llama/magdra && mkdir -p kit-before-day4 && cp -p train.py run3.sh guard.sh prep.py export.sh export_hf.py kit-before-day4/ && echo kept'
rsync -a -e "ssh -i $KEY" scratch/train.py night/run4.sh "${H}:/opt/llama/magdra/"
hx 'cd /opt/llama/magdra && chmod +x run4.sh guard.sh export.sh run3.sh'
a=$(cat scratch/train.py night/run4.sh | shasum -a 256 | cut -d' ' -f1); b=$(hx 'cd /opt/llama/magdra && cat train.py run4.sh | sha256sum | cut -d" " -f1')
[ "$a" = "$b" ] && hx 'cd /opt/llama/magdra && [ -x run4.sh ] && [ -x guard.sh ] && [ -x export.sh ]' && echo "MATCH the kit is the repo's and executable" || echo "MISMATCH"
```

What `run4.sh` would run, without running it. The recipe wants `--eval-iters 152` (eight
batches for each of the 19 shelves on the line); this runbook assumes `run4.sh` takes it as
the environment variable **`EVAL_ITERS`**, a knob it did not have when this was written:

```bash
hx 'cd /opt/llama/magdra && o=$(STEPS=16650 LR=5e-5 WARMUP=300 EVAL_EVERY=500 EVAL_ITERS=152 MIXFILE=runs/day4/mix.txt DRY=1 ./run4.sh day4 ckpt-day3-final.pt | head -1); \
  for want in "--init ckpt-day3-final.pt" "--batch 6 --accum 4" "--lr 5e-5 --warmup 300" "--steps 16650" "--eval-every 500" "--eval-iters 152" "--prompts prompts.txt" "--compile" "bins2/modern.bin:" "bins2/anth-rough.bin:0"; do \
    case "$o" in *"$want"*) ;; *) echo "MISMATCH run4.sh would not pass: $want"; bad=1;; esac; done; [ -z "$bad" ] && echo "MATCH run4.sh would start day4 as planned"'
```

A `MISMATCH` on `--eval-iters 152` alone means the knob is not in `run4.sh` yet: use step 7b,
whose wrapper has the flag written in.

**If the new kit is not wanted or does not pass the smoke test**, put `day3`'s trainer back
(`hx 'cd /opt/llama/magdra && cp -p kit-before-day4/train.py train.py'`) and use the plain
wrapper of step 7b; the recipe is the same, only the mid-run weights file and the per-shelf
training loss are missing.

## 6. smoke test, which is also the baseline

Forty steps on the real start path, every shelf, the real batch, the real eval size. Its second
eval (step 40, with the rate still under a seventh of its peak) is **the baseline for every
shelf**: the new ones have never been measured, and the old ones are measured on 48 windows now
instead of `day3`'s six, so `day3`'s last numbers are not their starting point. Keep the log.

```bash
hx 'cd /opt/llama/magdra && [ -e runs/smoke-day4 ] && echo "MISMATCH runs/smoke-day4 exists, pick another name" || echo "MATCH"'
hx 'cd /opt/llama/magdra && .venv/bin/python train.py --data $(tr -s "\n" " " < runs/day4/mix.txt) --out runs/smoke-day4 --init ckpt-day3-final.pt \
  --batch 6 --accum 4 --lr 5e-5 --warmup 300 --steps 40 --log-every 10 --eval-every 20 --eval-iters 152 \
  --ckpt-minutes 1000 --prompts prompts.txt --compile > runs/smoke-day4.log 2>&1; echo "exit $?"'
```

Check — it ended in `DONE`, read 19 shelves, measured 17 (the cyborg corpus and
`anth-rough` have no held-out set), wrote samples, stayed inside the card, and the thirteen old
shelves read near what `day3` ended on (other windows, so not the same: more than 0.3 apart
means the weights are not `day3`'s):

```bash
hx 'cd /opt/llama/magdra && python3 -' <<'EOF'
import json, os, re
log = open("runs/smoke-day4.log").read()
done = re.search(r"^DONE step=40 .*alloc ([0-9.]+)GiB reserved", log, re.M)
data = re.search(r"^DATA (.*)$", log, re.M)
last = [l for l in log.splitlines() if l.startswith("step 40/40")]
ev = dict((k, float(v)) for k, v in re.findall(r"([a-z0-9-]+) ([0-9]\.[0-9]{3})", last[-1].split("| eval")[1].split("| lr")[0])) if last else {}
old = json.load(open("runs/day3/status.json"))["eval_per_file"]
checks = {
    "ended in DONE": bool(done),
    "19 shelves read": bool(data) and data.group(1).split("; val")[0].count(".bin:") == 19,
    "17 shelves measured": len(ev) == 17,
    "init is day3's final save": "INIT weights from /opt/llama/magdra/ckpt-day3-final.pt source_step=84103" in log,
    "under 15.6 GiB reserved": bool(done) and float(done.group(1)) < 15.6,
    "samples written": os.path.exists("runs/smoke-day4/samples.jsonl"),
    "old shelves read near where day3 left them": bool(ev) and all(abs(ev[k] - old[k]) < 0.3 for k in old if k in ev) and all(k in ev for k in old),
    "no traceback": "Traceback" not in log,
}
for k, v in checks.items():
    print("MATCH   " if v else "MISMATCH", k)
print("baseline, every shelf:", " ".join(f"{k} {v:.3f}" for k, v in ev.items()))
print("old shelves, these windows minus day3's:", " ".join(f"{k} {ev[k] - old[k]:+.3f}" for k in old if k in ev))
steps = [l for l in log.splitlines() if l.startswith("step ")]
print("the log's clock:", " | ".join(l.split("| elapsed")[1].split("|")[0].strip() + " at " + l.split("|")[0].strip() for l in steps[-3:]))
print("SMOKE", "MATCH" if all(checks.values()) else "MISMATCH")
EOF
```

`runs/smoke-day4/` keeps a 4.3 GB save; it stays until bekh says delete for good.

## 7. start (e, f)

`day4.md` has to have bekh's yes on its numbers first. Five processes: wrapper, trainer (the
wrapper's child) and guard on the host; watcher and puller on the mac.

On the host — the wrapper and the guard (an old guard log would stop the new guard at once, so
one is moved aside if it is there):

```bash
hx 'cd /opt/llama/magdra && [ -e runs/day4/ckpt.pt ] && echo "MISMATCH runs/day4 already has a save: this would resume it, not start it" || echo "MATCH runs/day4 is new"'
hx 'cd /opt/llama/magdra && { [ -f runs/day4.guard.log ] && mv runs/day4.guard.log runs/day4.guard.log.$(date +%s); true; } \
  && (STEPS=16650 LR=5e-5 WARMUP=300 EVAL_EVERY=500 EVAL_ITERS=152 MIXFILE=runs/day4/mix.txt nohup ./run4.sh day4 ckpt-day3-final.pt > runs/day4.wrapper.out 2>&1 < /dev/null &) \
  && sleep 2 && (nohup ./guard.sh day4 > runs/day4.guard.out 2>&1 < /dev/null &) ; sleep 1; echo launched'
```

On the mac — the watcher and the puller (every three hours instead of six: the run is short):

```bash
mkdir -p night/day4
[ -f night/day4/guard.log ] && mv night/day4/guard.log night/day4/guard.log.$(date +%s)
(nohup caffeinate -i night/watch.sh day4 > night/day4/watch.out 2>&1 < /dev/null &)
(EVERY=10800 nohup caffeinate -i night/pull_ckpt.sh day4 > night/day4/pull.out 2>&1 < /dev/null &)
```

Check, two minutes later — five alive, and the trainer started what the recipe says:

```bash
hx 'cd /opt/llama/magdra && n=0; for p in "[r]un4.sh day4" "[t]rain.py --data" "[g]uard.sh day4"; do pgrep -f "$p" > /dev/null && n=$((n+1)); done; [ $n = 3 ] && echo "MATCH 3 of 3 alive on the host" || echo "MISMATCH $n of 3 alive on the host"'
n=$(ps ax | grep -c -E "[b]ash night/(watch|pull_ckpt).sh day4"); [ "$n" = 2 ] && echo "MATCH 2 of 2 alive on the mac" || echo "MISMATCH $n of 2 alive on the mac"
hx 'cd /opt/llama/magdra && python3 -' <<'EOF'
import json, re
log = open("runs/day4.log").read()
data = re.search(r"^DATA (.*)$", log, re.M)
mix = [line.split()[0].rsplit(":", 1) for line in open("runs/day4/mix.txt") if line.strip()]
want = [f"{p}:{float(w):g} ({json.load(open(p[:-4] + '.json'))['train_tokens']:,} tok)" for p, w in mix]
checks = {
    "init is day3's final save": "INIT weights from /opt/llama/magdra/ckpt-day3-final.pt source_step=84103" in log,
    "every shelf at its weight and size": bool(data) and all(x in data.group(1) for x in want),
    "24,576 tokens a step": bool(data) and "24,576 tokens per step" in data.group(1),
    "16650 steps planned": re.search(r"^step \d+/16650 ", log, re.M) is not None,
    "no traceback": "Traceback" not in log,
}
for k, v in checks.items():
    print("MATCH   " if v else "MISMATCH", k)
print("START", "MATCH" if all(checks.values()) else "MISMATCH (the first step line takes about two minutes to appear)")
EOF
```

After that it is `night/mon.py day4`, the page (`…:8446/school-day4.html`), and the hourly look
with `day4`, `run4.sh` and `runs/day4` in its prompt. The first eval is at step 500, about
eighteen minutes in. What the numbers should do, and when to stop, is `day4.md`.

### 7b. the same start without `run4.sh`

`run3.sh` with three flags changed and one added, written beside it — for the old trainer or the
new:

```bash
hx 'cd /opt/llama/magdra && sed -e "s/--lr 8e-5/--lr 5e-5/" -e "s/--hours \"\$HOURS\"/--steps 16650/" -e "s/--eval-every 1000/--eval-every 500 --eval-iters 152/" run3.sh > run4-plain.sh && chmod +x run4-plain.sh \
  && grep -q -- "--batch 6 --accum 4 --lr 5e-5 --warmup 300 --steps 16650 --log-every 50 --eval-every 500 --eval-iters 152 --ckpt-minutes 20 --prompts prompts.txt --compile" run4-plain.sh \
  && echo "MATCH run4-plain.sh is run3.sh at day4 settings" || echo "MISMATCH"'
hx 'cd /opt/llama/magdra && { [ -f runs/day4.guard.log ] && mv runs/day4.guard.log runs/day4.guard.log.$(date +%s); true; } \
  && (MIX="$(tr -s "\n" " " < runs/day4/mix.txt)" HOURS=9.4 INIT=ckpt-day3-final.pt nohup ./run4-plain.sh day4 > runs/day4.wrapper.out 2>&1 < /dev/null &) \
  && sleep 2 && (nohup ./guard.sh day4 > runs/day4.guard.out 2>&1 < /dev/null &) ; sleep 1; echo launched'
```

(`HOURS` there only words the push to the phone; the length is the `--steps`.) The mac's two and
the check are step 7's, with `"[r]un4-plain.sh day4"` for the wrapper's name.

## 8. changing the mix while it runs

**The only way to change the mix inside a run is `runs/day4/weights.json`**, and only the new
trainer has it: it reads the file at each eval (within eighteen minutes) and logs a `MIX step=…`
line; a shelf not named in the file keeps its weight. `night/turn.py day4` exits 3 when some
shelf's turn has stood for two evals running, 2 when it is on this eval only, 0 otherwise; with
`--weights` it prints the file and the command that puts it there, for the confirmed ones:

```bash
uv run -q --python 3.12 python night/turn.py day4; case $? in 3) echo "MISMATCH a shelf has turned on two evals running: act";; 2) echo "MATCH nothing confirmed (a turn on this eval only: look again next eval)";; 0) echo "MATCH no shelf has turned";; esac
uv run -q --python 3.12 python night/turn.py day4 --weights
```

By hand, a shelf to zero (`horizons` here; the same line with `{"anth-rough": 64}` is how the
rough anthologies would come in at one read, if bekh says yes mid-run):

```bash
printf '%s\n' '{"horizons": 0}' | hx 'cat > /opt/llama/magdra/runs/day4/weights.json.new && mv /opt/llama/magdra/runs/day4/weights.json.new /opt/llama/magdra/runs/day4/weights.json'
sleep 1200; hx 'grep "^MIX" /opt/llama/magdra/runs/day4.log | tail -n 1 | grep -q "horizons" && echo "MATCH the trainer took it" || echo "MISMATCH not taken yet (it is read at an eval)"'
```

**A stop and a relaunch does not change the recipe**: on resume the trainer takes every setting,
the `--data` line included, from the save, and a `MIX=` in the environment is ignored without a
word. With the old trainer the only way to change the mix is a new warm start from
`runs/day4/ckpt.pt` under a new name.

## 9. stop (g)

One command; the trainer saves and exits, the wrapper follows, the guard takes a last snapshot
and goes down, the watcher ends on `guard down`:

```bash
hx 'p=$(grep -o "\"pid\": [0-9]*" /opt/llama/magdra/runs/day4/status.json | grep -o "[0-9]*$"); ps -o args= -p "$p" | grep -q "[t]rain.py" && kill -TERM "$p" && echo "TERM sent to $p" || echo "no trainer at pid $p"'
```

Check, two minutes later, and the mac's puller, which sleeps through the end and is ended by pid:

```bash
hx 'cd /opt/llama/magdra && tail -n 1 runs/day4.log | grep -q -E "^(STOPPED|DONE) step=" && grep -q "guard down" runs/day4.guard.log && ! pgrep -f "[t]rain.py --data" > /dev/null \
  && echo "MATCH stopped: $(tail -n 1 runs/day4.log | cut -c1-70)" || echo "MISMATCH not down yet"'
kill $(ps ax | grep -E "[n]ight/(watch|pull_ckpt).sh day4" | awk '{print $1}') 2>/dev/null; sleep 1
[ "$(ps ax | grep -c -E "[n]ight/(watch|pull_ckpt).sh day4")" = 0 ] && echo "MATCH the mac's two are down" || echo "MISMATCH"
```

To go on from where it stopped: step 7's host and mac commands again, unchanged (it resumes from
`runs/day4/ckpt.pt` and keeps its plan). The save of a stopped or finished `day4` goes to the mini
with the same pipe as step 4's, with `day4` for `day3`.

## 10. rollback (h)

`day4` is an experiment and `day3`'s final save is the fallback. Rolling back is: stop `day4`
(step 9), and she is `day3`'s end again — nothing has to be trained for that.

Check — the fallback is where it should be, three times:

```bash
a=$(hx 'sha256sum /opt/llama/magdra/ckpt-day3-final.pt | cut -d" " -f1'); b=$(ssh -o ConnectTimeout=15 bek@100.69.218.90 'sha256sum /srv/music/school-archive/models/day3/ckpt.pt | cut -d" " -f1')
[ -n "$a" ] && [ "$a" = "$b" ] && echo "MATCH the trainable save: host and mini agree" || echo "MISMATCH"
hx 'ls /opt/llama/magdra/runs/day3/model-84103-q8_0.gguf > /dev/null 2>&1 && echo "MATCH the servable snapshot is on the host" || echo "MISMATCH"'
[ "$(cat models/day3/latest)" = "model-84103-q8_0.gguf" ] && echo "MATCH the mac serves day3's last snapshot" || echo "MISMATCH the mac's snapshot is $(cat models/day3/latest)"
```

Serve her to the loom again:

```bash
kill $(lsof -tnP -iTCP:8086 -sTCP:LISTEN) 2>/dev/null; (nohup llama-server -m models/day3/model-latest-q8_0.gguf -c 1024 -ngl 99 --host 127.0.0.1 --port 8086 --no-jinja > night/day3/serve.out 2>&1 < /dev/null &)
```

To train on from `day3`'s end with `day3`'s mix (a new run, `day3b`, ten hours here; the rate is
2e-5, not `run3.sh`'s 8e-5, which is ten times what `day3` ended on):

```bash
hx 'cd /opt/llama/magdra && { [ -f runs/day3b.guard.log ] && mv runs/day3b.guard.log runs/day3b.guard.log.$(date +%s); true; } \
  && (MIX="bins2/fantasy.bin:2000 bins2/scifi.bin:1500 bins/anime.bin:2100 bins/fanfic.bin:1400 bins2/base.bin:1550 bins/wired-core.bin:160 bins/wired-bulk.bin:400 bins2/literary.bin:620 bins2/horizons.bin:135 bins2/released.bin:80 bins2/library.bin:72 bins/lain.bin:20 bins/cyborg.bin:4 bins2/horizons-verse.bin:12" \
      HOURS=10 LR=2e-5 WARMUP=300 EVAL_EVERY=1000 nohup ./run4.sh day3b ckpt-day3-final.pt > runs/day3b.wrapper.out 2>&1 < /dev/null &) \
  && sleep 2 && (nohup ./guard.sh day3b > runs/day3b.guard.out 2>&1 < /dev/null &) ; sleep 1; echo launched'
```

Without `run4.sh`: `sed -e "s/--lr 8e-5/--lr 2e-5/" run3.sh > run3b.sh && chmod +x run3b.sh`, then
`INIT=ckpt-day3-final.pt HOURS=10 nohup ./run3b.sh day3b …` in its place. The mac's two are
step 7's with `day3b`.

## the 4-read variant

The same runbook with the variant's mix and length from `day4.md`: its two weights in
`runs/day4/mix.txt` (`bins2/modern.bin` and `bins2/anth.bin`), `22009` for `16650`
everywhere, and in step 3 `WANT` for those two shelves at 4.0 and `5409` for the sum of
the weights.
