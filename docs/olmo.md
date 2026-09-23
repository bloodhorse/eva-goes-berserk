# olmo

A bigger dreamer for the stream, to replace gpt-2 xl, whose pages bekh reads and doesn't like
(2026-09-24). The pick is **OLMo 3 32B at its last pre-anneal checkpoint**, run on the 16 GB card
with whatever doesn't fit spilled into system RAM. Mistral Small 3.1 24B base is the fallback if
olmo's prose comes out dead.

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

## the box and the offload math

The box is the 5060 Ti 16 GB on ubuntu at bekh's employer's office. He has access to it, and
using it isn't prohibited, but it's a bit uncomfortable. So **the footprint stays small and
removable**: everything lives in one folder in his home dir, llama.cpp is built there with
nothing installed system-wide, the server binds localhost only and we reach it through an ssh
tunnel, and taking it all away is one `rm -rf` of that folder (his box, his command). Ideally
only the finished gguf ever lands on the box, not 65 GB of bf16 (see plumbing).

Offloading only costs speed, and the stream doesn't need speed: one ~170-token passage every
five minutes. Rough per-token cost: the card's share read at ~448 GB/s plus the RAM's share read
at DDR speed, maybe 50–80 GB/s dual-channel (est., we don't know the box's RAM yet).

| quant | est. tok/s | est. per passage |
|---|---|---|
| Q4_K_M | 7–10 | ~20–25 s |
| Q6_K | 3–5 | ~40–60 s |
| Q8_0 | 2–3 | ~60–90 s |

All of these fit the five-minute cadence. At a few tokens a second, live writing on the page
looks like someone typing.

**The plan (bekh, 2026-09-24): start on the 5060 Ti at Q4_K_M, because experiments on a new model
want speed.** Q4 puts only ~5 GB in RAM, well inside that box's ~20 GB free. One condition:
4-bit shaves the low-probability tail, which is the part we hunt in at heat 1.8–2.5, so **no
verdict of "olmo's prose is dead" is final until the same seeds have run at Q8 on the 1080 Ti
box**. A dud at Q4 may be the quant, not the model.

Fans are the experiment, and they batch: a llama-server with `-np N` decodes N branches in one
pass over the weights, and offloaded decoding is bound by memory reads, so a fan of 8 costs far
less than 8 single runs. Each slot needs its own KV (~0.25 MB a token, est.), so keep `-c` at
N × ~1k.

Rough needs: RAM ≥ 32 GB for Q4/Q6 with the OS breathing, 48 GB+ for Q8. Disk: the gguf only
(~26 GB at Q6), plus ~65 GB bf16 temporarily if the conversion happens on the box.

KV cache at `-c 2048` is ~0.5 GB (est., 64 layers × 8 kv heads × 128 dim, f16). Put all of it on
the card. The layer split is whatever `-ngl` leaves ~1 GB free for KV + compute buffers; tune
it on the first run by watching `nvidia-smi`.

## plumbing

Where to convert, in order of preference:

1. **somewhere that isn't the box**: a cheap rented pod (the vast.ai recipe in
   friendship-is-magic's `docs/attic/cousin-arm-01.md`, rent the pipe not the card; conversion
   needs no GPU), or the mac if it has ~100 GB free. Then only the ~26 GB gguf crosses to the box.
2. on the box, then delete the bf16.

```bash
# 1. weights (the branch, not main)
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python huggingface_hub
.venv/bin/hf download allenai/Olmo-3-1125-32B --revision stage1-step656000 \
  --local-dir olmo3-32b-stage1

# 2. llama.cpp (its converter + quantizer; the box needs a CUDA build for serving)
git clone --depth 1 https://github.com/ggml-org/llama.cpp
uv pip install --python .venv/bin/python -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt

# 3. convert → bf16 gguf → quantize
.venv/bin/python llama.cpp/convert_hf_to_gguf.py olmo3-32b-stage1 \
  --outtype bf16 --outfile olmo3-32b-stage1-bf16.gguf
llama.cpp/build/bin/llama-quantize olmo3-32b-stage1-bf16.gguf olmo3-32b-stage1-Q6_K.gguf Q6_K
```

Serving on the box (localhost only, the split tuned by hand):

```bash
llama-server -m olmo3-32b-stage1-Q6_K.gguf -c 2048 -ngl 40 --no-jinja \
  --host 127.0.0.1 --port 8080
```

From the mac: `ssh -N -L 8081:127.0.0.1:8080 <box>`. The stream then points at `localhost:8081`
the way it points at nemo. The llama-server `/completion` facts (no template, BOS from metadata,
`n_predict` must be set, DRY's 64-token default window) are in `research-base-models.md`, q4.

Checks after conversion: `llama-cli` on a plain seed produces English, not token soup (if it
produces soup, the `olmo2` mapping or the tokenizer went wrong, not the model); `general.architecture`
in the gguf reads `olmo2`; `add_bos_token` is whatever the HF tokenizer config says.

## the test

Before olmo takes gpt-2's seat: the same seeds from the stream's pot, the same sampler (heat by
lot 1.8–2.5, min_p 0.08, the stream's settings), one fan on nemo and one on olmo, mixed
unlabelled, and bekh says which pile has the ghosts. `census.py --models` already does a mixed
blind fan. It needs olmo reachable as a second endpoint.

Worth a look while we're there: the same fan on `main` (the dirty control, see above).

## open

- **the 5060 Ti is taken** (2026-09-24): `/opt/llama/bin/llama-server` (pid 2327960) holds
  15.3 of its 16.3 GB, idle at the time of the look. It's a deployed service: system user `llama`, Qwen3.6-35B-A3B
  instruct, `0.0.0.0:8080`, an api key, `--metrics`, up 26 days. Whether anyone actually calls it
  decides whether this box is usable at all. Its disk has 157 GB free, driver 595, CUDA 13.2.
- **the 1080 Ti box is `ds-dev`** (the 5060 is `ds-dev2`). Driver 560, CUDA 12.6: Pascal builds
  fine. A `/usr/bin/python3` (pid 1022, someone's) holds 1.8 GB of the card, so ~9.4 GB is ours.
  **Its root filesystem is 100% full (46 GB, 0 free)**, and the big pool is mounted elsewhere.
  Nothing of ours may land on root: the HF cache (`~/.cache/huggingface`), uv's cache
  (`~/.cache/uv`) and the llama.cpp build all default to home, which is on root. Every one gets
  pointed at the pool (`HF_HOME`, `UV_CACHE_DIR`, the work dir itself).
- **which box.** The 5060 Ti box has **30 GB RAM, ~20 available, no swap**, with 9.4 GB already
  used by something else (2026-09-24). Q4/Q5 fit, and Q6 would put ~11.5 GB in RAM with no swap
  under it. The other box: a **1080 Ti (11 GB) and 125 GB RAM, ~120 free** (idle on
  2026-09-24). bekh ran llama 70b there with offload. There, Q8 fits with room to spare. That's
  the Q8 check, the `main` control, and maybe 70b. Unknowns on it: RAM channels/speed (that's the
  tok/s), who else uses it, and whether its CUDA still builds for Pascal (CUDA 12 does, 13
  doesn't).
- **how bekh reaches the box from here**: ssh, vpn, from Vietnam. Still open from BRIEF.
- **who else uses the card.** A training job or someone's desktop on it changes the split.
- **the box's CUDA/driver** for building llama.cpp with `-DGGML_CUDA=ON`.
- **sampler at 32B**: nemo's heat range was found on nemo. Olmo may want its own; the first fans tell.
- **the stream wiring**: a third writer beside nemo, or olmo replacing gpt-2 in the turn-about.
  Only after the blind test.
