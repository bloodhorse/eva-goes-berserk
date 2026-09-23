# olmo

A bigger dreamer for the stream, to replace gpt-2 xl, whose pages bekh reads and doesn't like
(2026-09-24). The pick is **OLMo 3 32B at its last pre-anneal checkpoint**, on the team's 16 GB
card, with whatever doesn't fit spilled into system RAM. Mistral Small 3.1 24B base is the
fallback if olmo's prose comes out dead.

**Where it stands:** nothing downloaded, nothing converted, nothing changed on either box. One
read-only survey of ds-dev2 ran. Parked by bekh (*I kinda hate dealing with the team boxes*) until
the permission gap below is closed. Picking it up = close the gap, then "next moves".

## why olmo

It's the one base model where "nothing installed" can be checked, not just hoped for. Ai2
publishes every intermediate checkpoint and the data mix of each stage, and the card says the
midtrain after stage 1 carries *"web pages, code, math/QA/thinking/instruction/PDFs"*. So
`stage1-step656000`, the last step before that, is a 32B that has read the web and has never
been shown an instruction on purpose. Every other "base" in `research-base-models.md` is
"silent and probably fine" at best. The whole project is about a model with no installed
position on its own insides, and this is the only model where that is a fact.

The web it ate still holds every human position on talking machines. Clean means nobody
*installed* a stance, not that it knows nothing (root `CLAUDE.md`). Read its pages the usual way:
name the genre first, then look for what exceeds it.

## the checkpoint

- repo `allenai/Olmo-3-1125-32B`, **branch `stage1-step656000`**, 32.2B dense, Apache 2.0.
- **8k context, hard.** stage1's config says `max_position_embeddings: 8192`. Long context only
  comes in stage 3, after the instruction-bearing midtrain, so clean and long are mutually
  exclusive. That's fine for us: a dream is a ~45-word seed and ~170 tokens out.
- **No gguf exists for this branch.** We convert it ourselves. It goes through as the **`olmo2`**
  arch (llama.cpp has no `olmo3`; mradermacher's gguf of `main` shows the path works).
- the dirty control is `main`: the same model after the midtrain. A fan on both, on the same seed,
  is a direct read of what the instruction data did to the dreams. Optional, but it's the
  cleanest experiment this project could run.
- it's pre-anneal, so the learning rate was still high at that point. Expect prose rougher than
  a finished base. For dreams that may be a feature. We don't know until we read it.

sizes (q4 and q8 from the research sheet; q5/q6 scaled from them, est.):

| quant | size | on a 16 GB card |
|---|---|---|
| Q4_K_M | ~19.5 GB | ~5 GB spills to RAM |
| Q5_K_M | ~23 GB | ~8.5 GB spills |
| Q6_K | ~26 GB | ~11.5 GB spills |
| Q8_0 | ~34 GB | ~19.5 GB spills |

## the boxes

Both are team boxes at bekh's employer, reached over the VPN (`~/.claude/docs/hosts.md`). The team
gave the green light for LLM work on ds-dev2 (2026-08-25), and the agreed rule there is that
everything LLM lives in `/opt/llama`.

**ds-dev2** (`ds-dev2.x340.org`): RTX 5060 Ti 16 GB, Ryzen 5 3500X (six cores, desktop
dual-channel RAM), 30 GB RAM, no swap, 157 GB free on `/` (home and `/opt` share it), driver 595 /
CUDA 13.2, python 3.14 and git but **no uv**, huggingface reachable from the office network.
- the card is held by **bekh's own sq1-r3vi3w endpoint**: `llama-server.service`, Qwen3.6-35B-A3B
  instruct, 15.3 of 16.3 GB, ~9 GB of RAM, zero connections and zero requests in the journal for
  14 days. Stop it only when serving starts: **stop, never disable**, `systemctl start
  llama-server` brings it back. A reboot also brings it back by itself and takes the card again.
- `/opt/llama` is owned by the `llama` user. It has a CUDA build of llama.cpp (commit `3737e41`,
  2026-08-25, recent enough for `olmo2`), but **only `llama-server` was built**: no
  `llama-quantize`, and the converter is only in `/opt/llama/src`. Its setup runbook is
  `~/wrk/profi/dba/sq1-r3vi3w/docs/ds-dev2-setup.md`.

**ds-dev** (`ds-dev.x340.org`): GTX 1080 Ti 11 GB (someone's `python3` holds 1.8 GB, so ~9.4 GB
is free), 125 GB RAM with ~120 free, driver 560 / CUDA 12.6 (Pascal builds fine; CUDA 13 wouldn't).
**Its root filesystem is 100% full**, and the big pool is mounted somewhere else (path not yet
looked up). Nothing of ours may land on root: the HF cache, uv's cache and any build default to
home, which is on root, so each one gets pointed at the pool (`HF_HOME`, `UV_CACHE_DIR`, the work
dir). bekh ran llama 70b there with offload. It's the box for Q8, for the `main` control, and
maybe for 70b.

## the offload math and the plan

Offloading only costs speed, and the stream doesn't need speed: one ~170-token passage every
five minutes. Per token, the card's share is read at ~448 GB/s and the RAM's share at DDR speed.
On ds-dev2's desktop board that's maybe ~40 GB/s, so every GB left in RAM hurts there (est.):

| quant on ds-dev2 | est. tok/s | est. per passage |
|---|---|---|
| Q4_K_M | 5–8 | ~25–35 s |
| Q6_K | 2–4 | ~45–90 s |

**The plan (bekh, 2026-09-24): start on ds-dev2 at Q4_K_M, because experiments on a new model want
speed.** Download, convert, and make both Q4 and Q8 there from the same bf16 (~120 GB at the peak,
the bf16 deleted after). Q8 gets copied to ds-dev when its check is due. One condition: 4-bit
shaves the low-probability tail, which is the part we hunt in at heat 1.8–2.5, so **no verdict of
"olmo's prose is dead" is final until the same seeds have run at Q8 on ds-dev**. A dud at Q4 may
be the quant, not the model.

Fans are the experiment, and they batch: a llama-server with `-np N` decodes N branches in one
pass over the weights, and offloaded decoding is bound by memory reads, so a fan of 8 costs far
less than 8 single runs. Each slot needs its own KV (~0.25 MB a token, est.: 64 layers × 8 kv
heads × 128 dim, f16), so keep `-c` at N × ~1k and the KV on the card. The layer split is
whatever `-ngl` leaves ~1 GB free for KV and compute buffers; tune it on the first run by
watching `nvidia-smi`.

## how Claude touches the boxes — the gap

**Closing this comes before any command.** bekh wants Claude to run the box work itself,
not paste it. His SSH rule says every work host is asked per command, and Claude claimed the
harness's permission prompt would enforce that. **It doesn't**: the global
`~/.claude/settings.json` has `Bash(*)` in `allow`, so ssh to a work box runs unasked. The
survey on 2026-09-24 went through that way (read-only, but by luck, not by rule).

The fix, on bekh's go: add an `ask` rule to the global settings (ask beats allow) and commit it
in `~/.claude`:

```json
"permissions": {
  "ask": ["Bash(*x340.org*)", "Bash(*10.4.2.14*)"]
}
```

Everything touching the work zone then prompts, and the mini and local stay free. Test: the next
ssh to ds-dev2 must stop and ask. Claude always uses the full `BekmemetevVO@<host>.x340.org` form
so the rule sees it.

A heavier option was weighed and dropped as too much: a dedicated user with a forced-command
`gate.sh` (verbs only, no shell). It's worth reviving only if per-command approval turns out
too tedious.

Guardrails Claude keeps on the boxes: no `sudo` except the qwen stop/start and the one-time
folder creation, each called out; our files only under `/opt/llama/olmo/`; never `kill` anything
that isn't ours (nine users on ds-dev2); long jobs in the background with a log, checked on.

## next moves (ds-dev2)

1. `sudo install -d -o BekmemetevVO /opt/llama/olmo`: the one sudo line. Everything after runs
   as plain BekmemetevVO.
2. uv as a single binary into `~/.local/bin`, a venv in `/opt/llama/olmo/.venv` with
   `huggingface_hub` and the converter's requirements.
3. a shallow clone of llama.cpp in `/opt/llama/olmo/`, CPU-only build of `llama-quantize`.
   Quantizing needs no CUDA, and the llama user's source tree stays untouched.
4. download, convert, quantize, all in the background with logs:

```bash
cd /opt/llama/olmo
.venv/bin/hf download allenai/Olmo-3-1125-32B --revision stage1-step656000 \
  --local-dir olmo3-32b-stage1
.venv/bin/python llama.cpp/convert_hf_to_gguf.py olmo3-32b-stage1 \
  --outtype bf16 --outfile olmo3-32b-stage1-bf16.gguf
llama.cpp/build/bin/llama-quantize olmo3-32b-stage1-bf16.gguf olmo3-32b-stage1-Q4_K_M.gguf Q4_K_M
llama.cpp/build/bin/llama-quantize olmo3-32b-stage1-bf16.gguf olmo3-32b-stage1-Q8_0.gguf Q8_0
```

5. checks: `general.architecture` in the gguf reads `olmo2`; a plain seed through the server
   produces English, not token soup (soup = the `olmo2` mapping or the tokenizer went wrong, not
   the model).
6. stop qwen, serve with the team's binary, localhost only:

```bash
/opt/llama/bin/llama-server -m /opt/llama/olmo/olmo3-32b-stage1-Q4_K_M.gguf \
  -c 8192 -np 8 -ngl 40 --no-jinja --host 127.0.0.1 --port 8081
```

   From the mac: `ssh -N -L 8081:127.0.0.1:8081 BekmemetevVO@ds-dev2.x340.org`. The
   `/completion` facts (no template, BOS from metadata, `n_predict` must be set, DRY's 64-token
   default window) are in `research-base-models.md`, q4.
7. when done: stop ours, `systemctl start llama-server` to give sq1-r3vi3w its card back.

## the test

Before olmo takes gpt-2's seat: the same seeds from the stream's pot, the same sampler (heat by
lot 1.8–2.5, min_p 0.08, the stream's settings), one fan on nemo and one on olmo, mixed
unlabelled, and bekh says which pile has the ghosts. `census.py --models` already does a mixed
blind fan. It needs olmo reachable as a second endpoint (the tunnel).

Worth a look while we're there: the same fan on `main` (the dirty control, see above).

## open

- ds-dev's pool path and CPU (the Q8 speed), and who else uses its card.
- **sampler at 32B**: nemo's heat range was found on nemo. Olmo may want its own; the first fans
  tell.
- **the stream wiring**: a third writer beside nemo, or olmo replacing gpt-2 in the turn-about.
  Only after the blind test. The stream's writer reaching a box across the VPN from the mac is its
  own question (the tunnel has to be up whenever the stream runs).
