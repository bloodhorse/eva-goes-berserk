# olmo

A bigger dreamer for the stream, to replace gpt-2 xl, whose pages bekh reads and doesn't like
(2026-09-24). The pick is **OLMo 3 32B at its last pre-anneal checkpoint, Q4_K_M, on a RunPod
serverless endpoint**, woken for a burst and asleep otherwise. Mistral Small 3.1 24B base is
the fallback if olmo's prose comes out dead.

**Where it stands (2026-09-24, night):** the weights exist on HF already (below — no
conversion), the deploy repo `bloodhorse/olmo-dreamer` is written and pushed (private, like
azeroth-render), the ten seeds for the blind fan are cut into `docs/olmo-seeds/`, and **the
endpoint exists: `qdipqwxl1l5ngm`**, load-balancing, booted clean on gemma-270m (a whole
A5000, Montreal), **streams word by word** through the balancer (61 chunks, longest gap
0.15 s, first token 0.52 s). Next: the cached model flipped to olmo, the ten seeds fanned ×4
(`fan.py` in the repo), the pages to the sheets site as `olmo-prophecies`.

**The flip to olmo stalled (2026-09-24, 19:41–20:10 UTC):** after the cached model was set to
the 18 GB repo, every worker sat on runpod's "initializing model files" — assigned, never
mounted, no failure reported, `THROTTLED` on and off — three of them reaped with nothing to
show, the fourth still fetching at 28 minutes. **Tonight's read came off a plain pod
instead** (`olmo-box`: an A40 48 GB in EU-SE-1, secure, $0.49/hr, stock `server-cuda` image,
the gguf curl'd from HF at boot — **50 MB/s, 6 minutes for 18.1 GB**, so HF's pipe is not the
problem; runpod's cache is). Two pod traps, both paid for: a `bash -c` entrypoint loses the
image's library path, and llama-server's libs live in `/app` beside the binary — export
`LD_LIBRARY_PATH=/app` or it dies on `libllama-server-impl.so`; and updating a pod's start
command recreates the container and wipes its disk, so the download runs again. `fan.py`
and `probe.py` take `--url` for a pod's proxied port.

**bekh's call (2026-09-24, 03:20 his clock): serverless stays** — zero idle, per-second, the
burst shape is exactly what it's priced for. **Tomorrow's move is baking the weights into the
image**, the doc's own fallback: runpod's *registry* is fast (the 3 GB image landed in 20 s on
every host, cached after the first pull) and their *model cache* is a black box; an image with
the gguf inside skips "initializing model files" entirely, and the cold path becomes a
registry pull plus llama mmapping 18 GB off local disk. Builder limits fit: 80 GB image cap,
30 min for the docker build step, the curl is ~6 of them. The Dockerfile change is one `RUN
curl` line and `MODEL_PATH` set to it; the cached-model setting comes off the endpoint. The
network volume stays plan C. The alternative shape, argued and not taken: a pod with the
weights on its own volume disk, stopped and started by api (~$4/month for the disk, start in
seconds) — the serverless promise kept by a box.

**What the first boot taught (2026-09-24):**
- **the console lies less than the API, again.** REST listed five whole cards; the console
  had `PRO 6000 MIG 24GB` ticked as well. Only graphql's `gpuIds` shows the truth, including
  the exclusion once it's unticked (`…,-NVIDIA RTX PRO 6000 Blackwell Server Edition MIG 1g.24gb`).
- **`PORT_HEALTH` must be an exposed container port** (`80/http,8081/http` on the template),
  or the console warns and the poll never reaches the shim. **`/ping` through the front door
  hangs** — the balancer keeps that path; `probe.py ping` reads llama's `/health` instead.
- **the slow stage is runpod's "initializing model files"**: image pulled at 19:26, model
  ready at 19:38 — twelve minutes for 278 MB, with the worker flipping `THROTTLED` meanwhile.
  Our own boot after that: a second. Expect the 18 GB flip to be worse; it's paid once per host.
- **runpodctl** (`brew install runpod/runpodctl/runpodctl`, key from the keychain at the point
  of use — `RUNPOD_API_KEY=$(_kc RUNPOD_API_KEY) runpodctl …`): `serverless logs <id>` gives
  container and platform lines, `serverless model-status <id>` says whether the cached model is
  assigned and mounted. It can set `--model-reference`, but its `saveEndpoint` mutation carries
  no endpoint `type`, so the flip stays a console click until that's known safe. It can't
  create a load-balancing endpoint or build from github either.

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
- **A gguf of this branch exists**: `Tricit/Olmo-3-1125-32B-stage1-step656000-Q4_K_M-GGUF`,
  one file, 18.1 GB, public, apache, made 2026-09-21 through ggml's gguf-my-repo space. The
  doc said "none exists" for three days and nobody checked; bekh asked. Two checks (2026-09-24):
  its source is a mirror repo (`from-our-page/…`, because gguf-my-repo can't take a branch)
  whose 14 shards match allenai's branch by size and sha256, tokenizer and config by size;
  and the gguf header, read by range request, carries `olmo2.attention.sliding_window = 4096`
  with the 64-entry pattern, 48 sliding layers — the config's `layer_types` exactly. A
  conversion by a pre-olmo3 llama.cpp would have no window at all and run full attention on
  48 layers. Arch `olmo2` (llama.cpp registers `Olmo3ForCausalLM` on it and writes the
  window), ctx 8192, file type 15 = Q4_K_M, pre-tokenizer `dbrx`.
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

The deploy artifact has its own repo, like `azeroth-render`: RunPod builds straight from a
GitHub repo on every push, with no registry and no write token lying around, and it clones the
whole repo, so nothing else rides along. **Written 2026-09-24, `~/tower/forge/olmo-dreamer`**:
a Dockerfile on `ghcr.io/ggml-org/llama.cpp:server-cuda` (CUDA 12.8.1, ubuntu 24.04) plus
python3; `boot.sh` finds the gguf under the cached-model path, writes `box.json` (card, cpus,
gguf, a `mig` flag) into a dir llama-server serves with `--path`, so `GET /box.json` needs no
proxy in front of the streaming route; `health.py` is the shim RunPod polls on `PORT_HEALTH`
— 204 until llama's `/health` says 200, because llama says 503 while loading and RunPod reads
that as broken; `probe.py` on the mac does ping / box / props / workers and `say`, which
streams a completion and stamps every token's arrival — the measurement of whether a
load-balancing endpoint passes SSE through word by word or in lumps. The console settings
table and the verify sequence are the repo's `README.md`.

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

**The pick: a small image plus a cached model from a one-file public HF repo** (Tricit's, above
— public, so no HF token anywhere). Baking is the fallback if caching disappoints, and the
network volume is now last. The endpoint is probed first with `ggml-org/gemma-3-270m-GGUF`
(one file, 278 MB) so a boot fix costs seconds and not an 18 GB pull per fresh host, then the
cached model is flipped to olmo.

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

## the conversion: not needed

Tricit's Q4 (above) is the checkpoint, checked. If a Q8 fan is ever wanted (the "dud at Q4
may be the quant" clause), no Q8 of stage1 exists on HF as of 2026-09-24; the recipe is then
a GPU pod, `hf download allenai/Olmo-3-1125-32B --revision stage1-step656000`, llama.cpp's
`convert_hf_to_gguf.py` (now a shim over a `conversion/` package — clone the whole repo) to
bf16, `llama-quantize` to Q8_0, ~65 GB of bf16 at 36–44 MB/s from HF. Q4s of `main` (the dirty
control) exist from several quantizers (`lmstudio-community`, `mradermacher`, `Hyperccino`).

## the test

Before olmo takes gpt-2's seat: the same seeds, the same sampler (heat by lot 1.8–2.5, min_p
0.08, the stream's settings), one fan on nemo and one on olmo, mixed unlabelled, and bekh
says which pile has the ghosts. `census.py --models` already does a mixed blind fan. It needs
olmo as a second endpoint URL — and RunPod's door wants a bearer header the loom's tools
don't send, so the plan is a tiny local proxy on the mac that adds it, and every tool talks
to `http://127.0.0.1:<port>` unchanged.

**The seeds are cut (2026-09-24): `docs/olmo-seeds/`**, ten files named by the room they came
from, each the seed exactly as it was fed (the room's root text), with `picks.json` as the
index (room, writer, temperature, source seed, why). bekh's brief: opus reads the last fifty
pages of the stream, picks the ten that read mystical, prophetic, weird — where the weirdness
feels meant, not broken — and returns their seeds. All ten were nemo's pages (the six gpt-2
pages in the window read flat or fell apart); nine distinct seed files, the storm-girl seed
(`seeds/kept/21-1132.txt`) twice, mystical both times. Four of the ten are one family — the
line, the tower, the carrier, the voice — and one of those seeds is the harvested text of
another pick's dream, whose page then went meta: a woman in a grey room given a computer and
told to write a story. The brass-head and brass-witch seeds reliably summon an oracle's voice.

Worth a look while we're there: the same fan on `main` (the dirty control, see above).

## order

1. ~~check the builder's image-size limit~~ (80 GB, fine; cached model is the pick).
2. ~~convert~~ (Tricit's Q4 exists and checks out).
3. ~~`bloodhorse/olmo-dreamer` written; endpoint `qdipqwxl1l5ngm` created, gemma booted,
   SSE word by word~~ → flip the cached model to olmo (console); box / say again; record the
   18 GB cold start here.
4. the local bearer proxy; the blind fan olmo vs nemo on `docs/olmo-seeds/`, by hand, to the
   sheets site unmarked.
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
