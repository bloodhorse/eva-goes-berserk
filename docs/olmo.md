# olmo

A bigger dreamer for the stream, to replace gpt-2 xl, whose pages bekh reads and doesn't like
(2026-09-24). The pick is **OLMo 3 32B at its last pre-anneal checkpoint, Q4_K_M, on a RunPod
serverless endpoint**, woken for a burst and asleep otherwise. Mistral Small 3.1 24B base is
the fallback if olmo's prose comes out dead.

**Where it stands:** decided, nothing built. No weights downloaded, no repo, no endpoint. The
first move is the build-size check (below), because it picks between two shapes.

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

## Q4, on a whole 24 GB card

**Q4_K_M, ~19.5 GB** (bekh, 2026-09-24: Q8 is superfluous; save the memory and the gold). It
fits a whole **RTX 4090** with room for an 8k KV cache (~0.25 MB a token, est.), and the 4090 is
the card azeroth-render proved on RunPod: ~$0.69/hr, billed per second. Q8 (~34 GB) would force
the 48 GB pool, a bigger image and a slower cold start.

One condition, cheap: 4-bit shaves the low-probability tail, which is the part we hunt in at
heat 1.8–2.5, so **if olmo reads dead, one fan at Q8 before we bury it**. A dud at Q4 may be the
quant, not the model.

## the endpoint: `bloodhorse/olmo-dreamer`

The deploy artifact gets its own repo, like `azeroth-render`: RunPod builds straight from a
GitHub repo on every push, with no registry and no write token lying around, and it clones the
whole repo, so nothing else rides along. It holds a Dockerfile (llama.cpp's CUDA server, plus
the weights or a path to them) and a handler.

**The lore to carry, all measured on azeroth-render** (its `SETUP.md` and `README.md`, and
`~/tower/attic/runpod-kit`):

- **active workers = 0**, always. Anything above bills forever; this is the one setting that
  costs real money. Max workers small (1–2); FlashBoot on.
- **the MIG trap.** A "24 GB" tier includes `RTX PRO 6000 Blackwell MIG 1g.24gb`, an eighth of a
  card. Untick every PRO/MIG entry **in the console**, because `gpuTypeIds` set through the API
  doesn't bind the scheduler. The worker reports its own GPU with every answer (`box.gpu`), and
  no timing is believed before it's read.
- **a narrow pool gets throttled.** With only 4090 / A5000 / 3090 ticked, one job queued 278 s
  for a card. Whole 48 GB cards (A40, A6000, L40S) fit Q4 too and buy availability back.
- **the CUDA trap.** Pin "Allowed CUDA versions" to what the image's llama.cpp was built for,
  or a worker lands on an old driver.
- **build logs**: read them from the downloaded file, not the web view, which hides the failing
  step's output. There's no builds route in the REST API.
- env vars are set in the console (the API can't write them) and reach only workers started
  after the edit.
- the API key is in the keychain as `RUNPOD_API_KEY` and works (checked 2026-09-24, by one
  read-only call; the account's only endpoint is `azeroth-render`, min workers 0).

## cold start, and the way round it

azeroth's ~10 GB image: **~10 minutes the first time a host pulls it, 30–110 s after that, under
a second warm.** Olmo baked in is ~22 GB, so first pulls get worse. For a burst that's
tolerable if it's paid once per burst and hidden:

- **`eva go N` wakes olmo first.** A warm-up request goes out as the ration starts, and nemo
  writes the first dream while the worker boots (they take turns anyway).
- **idle timeout covers a burst**, not a request: long enough to span the gap between olmo's
  turns (a few minutes), so one ration costs one cold start. Pennies at per-second billing.
- **if olmo isn't up when its turn comes, nemo takes the turn.** A burst never stalls on a cold
  worker.

**Checked 2026-09-24 against RunPod's docs:**
- **the GitHub builder takes it.** Images up to **80 GB**; the whole build must finish in 160
  minutes, and **the `docker build` step in 30**. Baking in ~20 GB pulled from HF at ~40 MB/s is
  ~9 minutes of that 30, which fits but without much margin.
- **better than baking: RunPod's cached model.** The endpoint names one HF model (public, gated
  or **private**). RunPod starts workers on hosts that already hold it, or downloads it there
  first **without billing the download**, and it lands under
  `/runpod-volume/huggingface-cache/hub/models--<org>--<name>/snapshots/<hash>/`. The docs
  claim cold starts of "a few seconds, even for large models". Two catches: one cached model per
  endpoint, and **it downloads every file in the repo**. So the private HF repo holds the Q4 gguf
  and nothing else, and the image stays small (llama.cpp only). azeroth left this blank because
  its weights were 4 GB.

**The pick: a small image plus a cached model from a one-file private HF repo.** Baking is the
fallback if caching disappoints, and the network volume is now last.

## how the stream talks to it: the normal way

bekh doesn't care about privacy here, it's only text, so **RunPod's own front door**, no tailnet.
In order of preference, to verify against RunPod's current docs before building:

1. **a load-balancing endpoint (they exist, checked 2026-09-24)**: plain HTTP straight to the
   worker's port, any HTTP server, no handler. llama-server runs stock, and the stream calls
   `/completion` with `stream: true` **exactly as it calls nemo**. Same body, same sampler (DRY,
   xtc, min_p), word by word onto the page. The docs' terms: a health check on `PORT_HEALTH`
   at `/ping` (200 healthy, 204 initializing), which llama-server doesn't serve at that path, so
   it needs a tiny shim or a path setting; **a request waits at most 2 minutes for a worker** (so a
   cold start longer than that fails the request, and the warm-up plus nemo fallback matter);
   5.5 minutes per request; no queue. Whether it scales to zero isn't stated. Verify that before
   trusting it with money.
2. **the queue endpoint** (`/run`, `/runsync`, `/stream`): a thin handler starts llama-server in
   the worker and forwards the `/completion` body untouched, so the sampler still matches. Words
   come back through `/stream` polling. Whether that feels live or comes in lumps is a test;
   lumps are acceptable, olmo's pages would just land a sentence at a time.

**Parked: the lease over the tailnet.** One job holds the worker for a burst, the worker joins
the tailnet (as azeroth's does) and serves llama-server there. It's the cleanest stream, but it
needs bekh in the tailscale admin console for a new tag and a tagged key, so it's not worth it
unless both options above disappoint.

vLLM, RunPod's ready-made LLM worker, is out: no DRY, no xtc, and a blind test with a different
sampler compares samplers, not models.

## the conversion: once

On a plain RunPod pod (CPU-heavy, fat pipe; no GPU needed to convert), then destroyed:

```bash
pip install -U huggingface_hub
hf download allenai/Olmo-3-1125-32B --revision stage1-step656000 --local-dir olmo3-32b-stage1
git clone --depth 1 https://github.com/ggml-org/llama.cpp
pip install -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
python llama.cpp/convert_hf_to_gguf.py olmo3-32b-stage1 --outtype bf16 \
  --outfile olmo3-32b-stage1-bf16.gguf
cmake -S llama.cpp -B llama.cpp/build && cmake --build llama.cpp/build -j --target llama-quantize
llama.cpp/build/bin/llama-quantize olmo3-32b-stage1-bf16.gguf olmo3-32b-stage1-Q4_K_M.gguf Q4_K_M
```

The Q4 goes to a **private HF repo** (the permanent home of the weights, where a Dockerfile or a
volume pulls it from), or straight onto the network volume if that's the shape. Downloads from
HF ran at 36–44 MB/s on the vast run (`friendship-is-magic/docs/attic/cousin-arm-01.md`), so the
65 GB of bf16 is ~30 minutes. Checks: `general.architecture` reads `olmo2`; a plain seed gives
English, not token soup (soup = the `olmo2` mapping or the tokenizer, not the model).

## the test

Before olmo takes gpt-2's seat: the same seeds from the stream's pot, the same sampler (heat by
lot 1.8–2.5, min_p 0.08, the stream's settings), one fan on nemo and one on olmo, mixed
unlabelled, and bekh says which pile has the ghosts. `census.py --models` already does a mixed
blind fan. It needs olmo as a second endpoint URL.

Worth a look while we're there: the same fan on `main` (the dirty control, see above).

## order

1. ~~check the builder's image-size limit~~ (80 GB, fine; cached model is the pick).
2. convert on a pod → Q4 into a private HF repo, alone.
3. `bloodhorse/olmo-dreamer`: Dockerfile + handler (or none, on a load-balancing endpoint);
   endpoint configured by the lore above; one seed through it, `box.gpu` read.
4. the blind fan olmo vs nemo, by hand.
5. only if olmo wins: `eva go` learns the warm-up and the endpoint URL, and olmo takes gpt-2's
   turns.

## open

- **sampler at 32B**: nemo's heat range was found on nemo. Olmo may want its own; the first fans
  tell.
- **the first word typed**: with a cold worker behind a queue, how the page's live writing
  looks on olmo's turns.

## footnote: the team boxes (weighed and dropped, 2026-09-24)

The first plan was bekh's employer's boxes: ds-dev2 (RTX 5060 Ti 16 GB, 30 GB RAM, holding his
own idle sq1-r3vi3w qwen service) with Q4 spilled to RAM, and ds-dev (1080 Ti, 125 GB RAM,
root filesystem 100% full) for Q8. Dropped for RunPod: team boxes mean sudo, other people's
services and full disks, and bursts cost pennies on serverless. Survey facts are in git history
(this file, before the RunPod rewrite) and `~/.claude/docs/hosts.md`.
