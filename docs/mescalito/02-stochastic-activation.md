# mescalito, slice 02: stochastic weights, activation noise, random vectors, DRµGS, twins

Brief items 2 and 3, the orchestrator's additions A (on-manifold noise) and B (the damaged twin),
DRµGS, and "activation temperature". This covers the per-token or per-n-token perturbation that
the brief's "lightning" points at.

## The verdict for this slice

**Isotropic noise, whether a fresh draw per token or a frozen draw per page, is mostly absorbed by
a model of this size. The part that gets through reads as a sampler change, not as a new
weather.** Three independent measurements say a trained transformer has a *plateau* around its
real activations. Random directions barely move it (ActAdd: "doesn't change much"; Heimersheim:
"naive isotropic random directions are *much* less sensitive"; DRµGS on a 30B: rotating the
attention input by up to 1 radian still yields near-identical greedy text). OLMo is the extreme
case. In the one measurement on an OLMo-3-32B, it tolerates activation noise **60× larger** than
Llama-3.1-8B before a comprehension check breaks (σ_max 0.66 vs 0.011). My reading is that this
is architectural: OLMo's post-norms cap how loud any noised sublayer can write into the residual.
This is the "sober" bekh sees, and plain noise will not dissolve it before it turns to slur. **The
mechanic that should give lightning is a *strike*: a short burst (4–16 tokens) of an
*on-manifold* vector (the difference between two real activations, i.e. "another document's
state"), injected mid-depth at 0.5–1× the residual norm, 1–3 times a page, with clean decoding
between strikes.** It is on-manifold because the model can *read* a real activation direction,
while it shrugs off random ones. A strike rather than a steady push fits the geometry. The
residual has stable regions with sharp boundaries, and the boundaries get sharper with scale and
training ("stable regions … become more defined as training progresses or model size
increases", measured on OLMo). So small pushes do nothing and a large one jumps a region. It is
short so the ground stays intact: after the strike the clean model is back and does what OLMo is
good at, which is building an argument around whatever the strike deposited. Concept-injection
work shows exactly this shape of intrusion ("I don't detect an injected thought. The ocean
remains calm and undisturbed."). Nobody has run it as a generation schedule. It needs one
~80-line patch to `llama-server` (below), or zero patches with the pending
`/cvectors` hot-swap PR plus chunked requests.

---

## (a) Mechanisms

### 1. Stochastic weights at inference (MC-dropout, Bayesian sampling, "noisy inference")

**Mechanics.** Draw a perturbed model per sample and generate from it. MC-dropout needs dropout
layers, and modern LLMs have none; the one ICLR paper that does this for LLMs says so:
"dropout is not included in many popular LLMs". The live LLM variant is Liu et al.
(Qualcomm, ICLR 2026). They add non-negative uniform noise U(0, 0.07) to the **MLP hidden
activations** of layers 20–32, **one draw per sample, shared across layers**, and note: "This
approximately modifies the MLP bias and thus effectively samples a model ω̂." Their reason for
sharing the draw across layers is itself a finding: "As LLMs include skip connections, adding
independent noise across layers may cancel out". Evolution-strategies fine-tuning (Qiu et al.
2025) also generates from per-member weight-noised models, at σ = 0.001 on every parameter, but
it reports rewards, not prose.

**Reported feel.** Nobody reports prose. The hallucination paper reports that greedy answers
diverge more on questions the model doesn't know, "without degrading model generation
accuracy". At that dose it gives epistemic wobble and no strangeness.

**On consumer stacks.** No flag anywhere: llama.cpp, vLLM, exllama, mlx and transformers have
nothing. In llama.cpp the weights are mmapped and quantized. Per-token weight noise would mean a
re-quant per token, which is impossible. Per-page re-noise of the gguf is item 1's frozen noise
with a fresh draw, and it is uneconomic on Q4. gguf-py can *dequantize* Q4_K/Q6_K but cannot
*quantize* Q4_K (checked: `gguf.quants.Q4_K` has only `dequantize_blocks`). So each draw means
dequant → noise → `llama-quantize` from an F16 intermediate of ~64 GB. That is tens of minutes per
page. Dead.

**The route that exists today, stock `llama-server`: a pool of random LoRA adapters.** A LoRA is
low-rank weight noise ΔW = B·A that llama.cpp applies on top of the quantized weights. The server
already supports:
- **per request**: `"lora": [{"id": k, "scale": s}]` in `/completion`. This is a fresh draw per
  page, with the scale as the dose. Changing it clears the slot's KV cache
  (`lora_should_clear_cache` returns true for non-aLoRA), so the page is re-prefilled under the
  new weights. That costs well under a second for a 45-word seed.
- **per n tokens, with the KV kept**: `POST /lora-adapters [{"id":k,"scale":s}]` changes the
  *global* set. A following request that has no `lora` field takes `slot.lora =
  params_base.lora_adapters` and does **not** clear the cache (verified in
  `server-context.cpp`, `launch_slot_with_task`). Generate in chunks of n tokens with
  `cache_prompt`, swap the adapter between chunks, and each stretch of text keeps the KV
  it was written under. That is a "living charge" with zero C++.
- load the pool at startup with `--lora a.gguf --lora b.gguf … --lora-init-without-apply`.

This is weight noise, so it is not isotropic in the residual. The perturbation is *input-gated*:
ΔW·x fires in proportion to what the layer reads. My own untested variant, and the one I would
try on the weight side, is **neuron cross-wiring**: rank-r LoRA on `ffn_down` with A = one-hot
rows on r random MLP neurons and B = directions. Each chosen neuron, whenever it fires, also
writes u_j. Neurons fire sparsely and by context, so the push is triggered by content, scattered
over all layers, and rare. That matches "from everywhere" better than any global noise. Isotropic
u_j will mostly be ignored (see §6). The version worth trying takes u_j = **another neuron's
real output column** (dequantize `ffn_down` with gguf-py and copy column j′ into B): *when
feature j fires, the model also hears feature j′.* That is synaesthesia as a mechanic. Nobody has
done it that I could find. Script below (`rand_lora.py --mode wire`, which writes random u_j; the
column-copy variant is 10 more lines).

**Cost on a 32B Q4, one 48 GB card.** A rank-8 adapter on `ffn_down` × 64 layers is ~67 MB
f32, so a pool of 16 is ~1 GB of VRAM. Compute overhead is two thin matmuls per layer, which is
negligible. No build.

**Bet.** Isotropic low-rank noise: a slur at large scale and nothing at small, like item 1.
Cross-wiring with real columns: the best weight-side lightning candidate, untested.

### 2. Isotropic activation / residual-stream noise, fresh per token

**Mechanics.** h ← h + ε, ε ~ N(0, σ²I), at every decode step, on some layers. Variants: on the
embedding (earliest), on block outputs (residual), on attention-branch outputs.

**Doses that exist in print, normalised.** In d dimensions, isotropic ε with σ = α·RMS(h) has
‖ε‖ = α‖h‖. So α *is* the noise-to-residual norm ratio, per layer, per token.
- **Noise Steering (Khalid, Shapsough, Zualkernan 2026), paper.** Five 7–9B instruct models,
  story generation. The noise is added after each selected block, "σres = α · medianl RMS(l)",
  "α is a fixed scaling coefficient set to 0.175 across all experiments", with cosine decay to
  zero over the story. Residual noise "achieves a 0% collapse rate for every model and improves
  Vendi Score in all five cases", and "Constraint adherence is largely undisturbed". Embedding
  noise at the same α: "causes complete collapse on Phi-4-mini (100%)". Their summary is that
  internal perturbation beats T = 1.8, which "inflates reading grade level and causes
  catastrophic collapse on several models". This is the only paper that measures prose under
  per-token residual noise. Its α = 0.175 is **the only published safe dose**, and it was chosen
  as safe, not as a cliff. They explicitly left "a more comprehensive sensitivity study
  across … per-model α values" undone.
- **Noisy GRPO (Joshua Harris), scene/blog.** Noise on the embedding output at "0.6 * mean absolute
  hidden state magnitude" (≈ α 0.5–0.75) during RL rollouts. It keeps entropy up, and he doesn't
  describe the text.
- **Random Soft Prompts (2026), paper.** Random embedding-scale vectors appended to the prompt.
  The effect is "a rise in early-generation entropy followed by convergence to the baseline
  later in generation", because attention to the injected tokens decays with length (their
  Theorem 1). That is lesson one of this whole slice: **the model heals**. Perturb the context once
  and it dilutes. Perturb every step and it jitters.
- **OLMo-3.1-32B specifically (Fornasiere et al. 2026, "Language models recognize dropout and
  Gaussian noise applied to their activations"), paper.** Gaussian noise on every layer's attention
  and MLP module outputs. The σ at which simple comprehension drops below 95%:
  Llama3.1-8B 0.011, Qwen3-14B 0.105, Qwen3-32B 0.24, **Olmo3.1-32B 0.66**, and OLMo's σ_max
  "does not fall in the range [0.0, 0.5]". Also: "Olmo3.1-32B starts below chance because, at low
  perturbation magnitudes, it answers 'neither'". It doesn't notice. My reading is
  architectural. The hooks sit on `self_attn`/`mlp` outputs (checked in their `hooks.py`), and in
  OLMo 2/3 those outputs then pass through `post_attention_layernorm` /
  `post_feedforward_layernorm` before the residual add. **The post-norm renormalises the noised
  write, so noise inside an OLMo block can only rotate what the block writes and cannot make it
  louder.** Llama has no such limiter. For us this means: noise inside OLMo's blocks is capped
  by construction, so for any real dose **inject at the residual (`l_out`)**, which is exactly
  where llama.cpp's control vector sits.

**Where the cliff is (inferred, not measured on prose).** The literature gives safe points (α ≈
0.1–0.2 per layer on 7–9B) and one collapse point: embedding noise on a weak-language model at
α < 0.175. Nobody has swept α on residual noise and printed pages. The mechanism predicts two
regimes. **Per-token isotropic noise at late layers ≈ correlated logit noise**: ε projected
through the unembedding shifts groups of tokens with similar output embeddings together. That is
a random "theme" re-rolled every token. It is a temperature relative with a semantic accent: at
low α it gives diversity, and at high α it gives slurred word choice with grammar intact. **At
early layers** the whole stack amplifies it; that is where the embedding-noise collapses live
(salad).

**Architecture note for the patch.** OLMo 2/3 in llama.cpp (`src/models/olmo2.cpp`) has **no
pre-norm**: `cur = inpL` goes straight into `build_qkv`, and `ffn_inp` goes straight into
`build_ffn`. So a perturbation of the residual reaches V and the MLP linearly. Only Q and K get
re-normalised (QK-norm). Unlike Llama, nothing rescues the model from a big residual push by
normalising it away. Scale by measured norms (recipe below).

**Cost.** Per-token additive noise needs no graph change in llama.cpp. At decode the batch is one
token, so the per-layer control-vector tensor *is* per-token noise if you refill it before every
`llama_decode`. That is 63 × 5120 floats = 1.3 MB host→device per token, microseconds of work.
The one trap: `llama_context::set_adapter_cvec` sets `sched_need_reserve = true` on every call
(`src/llama-context.cpp`), which forces a scheduler re-reserve per token. Patch it to reserve
only when the layer range changes. Throughput then stays ≈ stock (~26 tok/s measured on an A40).

**Bet.** Slur, with a diversity bump before it. It is not lightning, because nothing it adds is a
direction the model reads as content.

### 3. DRµGS (EGjoni, Dec 2023): the closest existing thing, verified against the repo

**What it is (from `README.md`, `porting/A Guide to Making DRUGS.md`, `drugs/generation/utils.py`,
`drugs/models/llama/drugged.py`, `drugs/dgenerate.py`).**
- **Rotation, norm-preserving, fresh draw every forward pass.** `get_perturbed_vectors` draws a
  per-vector angle `torch.rand_like(...) * max_theta_radians` (uniform in [0, θ_max]). It builds
  an orthogonal direction by projecting a random vector off the input and returns `cos θ·x +
  sin θ·‖x‖·r⊥`. `dose_theta` is θ_max in radians.
- **Injection points (five types, all *inside* attention).** **H** = the hidden states *as fed
  to the Q/K/V projections*, perturbed in place inside `llama_drugged_attention_forward`. That
  tensor is the output of the pre-attention RMSNorm, so **the residual stream itself is not
  touched**. **Q**, **K**, **V** = the projected vectors (Q before RoPE; K after RoPE, since "the
  Huggingface transformers library was not receptive" to pre-RoPE). **A** = the per-head attention
  output before `o_proj`. The orchestrator's memory that H is "the residual stream" is wrong. The
  author is emphatic: "Anywhere but the Residual Stream … Seriously, the residual stream is your
  model's only tether to sanity. Don't touch it unless you too are part of the model." (footnote:
  "Exception: Do not inject drugs directly into the residual stream.")
- **Where in depth.** A dose *shape* over layer depth. The published samples use
  `injection_depth = 0.4`, `spread ≈ 0.156`, i.e. roughly layers 15–34 of a 60-layer 30B.
- **Protections.** The first 6 positions are spared ("because that's where the attention sink
  lives"). `protect_inputs=True` by default means the prompt is prefilled clean and only generated
  tokens are drugged. The default sampler is **argmax**: "simply selecting the most likely
  prediction is often enough". The noised KV compounds over steps; the `cold_shower` re-prefills
  "every t-predictions", and the author found it "seems unnecessary".
- **A bug nobody mentions.** The "random direction" is `torch.rand_like`: uniform on [0,1),
  **not centred**. The source line, `drugs/generation/utils.py` lines 57–62 at commit
  `3c053ead813b2d903df23a33f9b25b6ba3c25c1e`
  (https://github.com/EGjoni/DRUGS/blob/3c053ead813b2d903df23a33f9b25b6ba3c25c1e/drugs/generation/utils.py#L52-L67),
  verbatim:
  ```python
      random_angles = torch.rand_like(input_vectors[:,:,:,0], device=input_vectors.device, dtype=input_vectors.dtype) * max_theta_radians
      #The next three lines are an old family recipe for cooking up orthogonal vectors.
      random_vectors = torch.rand_like(input_vectors)
      projections = input_vectors * (torch.sum(random_vectors * input_vectors, dim=-1, keepdim=True) / 
                     torch.sum(input_vectors * input_vectors, dim=-1, keepdim=True))
      orthoshifts = random_vectors - projections
  ```
  `torch.rand_like` samples U[0,1) (PyTorch's documented semantics; `randn_like` is the normal
  one). The porting guide confirms the author knew and meant it for the *angle*: "I arbitrarily
  decided on a uniform distribution (which is what that call to `torch.rand_like` samples from)
  because it's easier to validate". The same call builds the *direction*, which is where the bias
  comes from. I measured it (numpy, d = 128/4096/5120): the orthogonalised draw has cosine
  **0.87** with the all-ones direction projected off the input, and **two successive draws have
  cosine 0.75 with each other**. DRµGS is mostly a *fixed-direction* rotation with a random
  angle, plus a smaller random part. Some of its "variety" is a consistent push toward ±1·(all
  dims). A port should use `randn`. The author himself floated "**Kn**, **An**, **Hn** … for
  softer, normally distributed noise variants" and "**L2H** … which just add the random vector
  noise without regard for magnitude preservation", **but never compared rotation to additive
  noise on the same states.** Addition A's question is unanswered by him.

**Dose and feel, verbatim and from the author's own sample files** (all on chat-tuned models,
greedy, system prompt "Respond as Alan Watts would."):
- README: "The `dose_theta` parameter defines a maximum angle in radians … You probably shouldn't
  go past 0.1". "we can add quite a lot of noise in earlier layers and the model very quickly
  drowns that noise out with its own signal". "something special seems to happen in the middle
  layers that causes relatively large spikes in output divergence". "the most likely prediction
  changes, but generally remains reasonable".
- **30B-Epsilon (AWQ 4-bit), H at θ = 0.1**: five seeds, **near-identical** text. The only
  differences are "understanding" vs "contemplation" and "spirituality" vs "the human
  experience".
- **Same, H at θ = 1.0 rad** (57°, ten times the recommended ceiling): still fully coherent. Now the
  branches differ at the *opening move* ("I am here to assist you in your journey of
  self-discovery…" / "I would like to inquire about the context in which the message was
  sent…"). Every seed lands in the same attractor ("the interconnectedness of all things").
- **Mistral-7B (dolphin), H at θ = 1.0**: the failure is a **loop**, not salad. "Jimmy's friends
  all agreed that the balloon was a beautiful sight to see … Jimmy was so happy that he had let
  the balloon go…" repeats for the rest of the budget. At θ = 0.5 the stories are coherent and
  diverge ("He had taken it to the park … He had also taken it to the beach"). One lovely
  wobble at 1.0: "he noticed that the balloon string was getting shorter and shorter, and he
  realized that he needed to cut the string". That is dream logic, the kind we want, from the
  noised 7B.
- HN thread (Dec 2023, 169 points): mostly jokes. gwern: "Injecting noise has many
  mathematically-sound interpretations, like the Bayesian interpretations of dropout for
  ensembling or posterior sampling." doctorpangloss: "as a betting man: there is no benefit".
  Nobody posted outputs.

**Ports.** None. llama.cpp issue #4704 "Add support for DRµGS" was closed by the stalebot; the
author wrote there: "The method requires intimate contact with the kv-cache … after having spent
like 3 days clawing at the guts of the huggingface transformers library, I would … be impressed
to learn that this would be feasible from outside of llama.cpp". koboldcpp #1080 is open, and
LostRuins wrote: "That modifies the model weights itself, so I think it might not be ideal for
KCPP. I am looking into implementing XTC first." (He is wrong: DRµGS does not touch the weights.)
No exllama, vLLM or text-generation-webui port turned up. The repo supports transformers only,
for Llama and Mistral.

**Patch for llama.cpp, H type, on OLMo.** In `src/models/olmo2.cpp` the loop begins
`ggml_tensor * inpSA = inpL; cur = inpL;` and then `build_qkv(model.layers[il], cur, …)`. OLMo has
no pre-norm, so "H" (the attention input) *is* the raw residual here. That means the rotation
must be applied to a copy: `cur = build_rot_noise(inpL, il)` while `inpSA` stays clean. That
keeps DRµGS's rule of not touching the residual. `build_rot_noise` goes in `llama-graph.cpp`
next to `build_cvec` and reads two per-layer inputs refilled host-side each decode: a random
direction r [n_embd] (reuse the cvec tensor machinery) and [cos θ, sin θ]. In ggml ops:
`dot = ggml_sum_rows(ggml_mul(h, r))`, `hh = ggml_sum_rows(ggml_sqr(h))`,
`rp = ggml_sub(r, ggml_mul(h, ggml_div(dot, hh)))`, `rp = ggml_mul(rp, ggml_div(ggml_sqrt(hh),
ggml_sqrt(ggml_sum_rows(ggml_sqr(rp)))))`, `out = ggml_add(ggml_scale(h, cosθ), ggml_scale(rp,
sinθ))`. That is about twelve elementwise ops on one 5120-vector per layer per token, so the cost
is negligible. The work is plumbing a second adapter-like tensor set: ~150 lines plus a custom
build. **Skip prefill** (n_tokens > 1 → θ = 0) to match `protect_inputs`.

**Bet.** DRµGS is **coherent diversity**, not strangeness. On a 30B it barely moves at the
recommended dose, and at 10× it re-rolls the opening move inside the same attractor. Its failure
is loops, not salad. That is what a plateau predicts for off-manifold directions. It is worth
porting only as the rotation primitive for §6, with randn and with the direction drawn on-manifold.

### 4. Random control vectors: one random direction per layer, held for the page

**What llama.cpp does, precisely** (from `common/common.cpp` `common_control_vector_load_one`,
`src/llama-adapter.cpp`, `src/models/olmo2.cpp`):
- The file is a gguf with 1-D **F32** tensors named `direction.<k>`, all the same length (n_embd).
  `k = 0` is rejected ("invalid (zero) direction tensor layer index"). Several files, and
  duplicate k within a file, are **summed**, each × its `--control-vector-scaled` strength.
  Metadata is **not read** by the loader. The generator writes `controlvector.model_hint` /
  `controlvector.layer_count` and repeng writes the same; they're cosmetic.
- `direction.k` lands in `tensors[k]` and is added by `build_cvec` right after the block's final
  residual add: `cur = ggml_add(ctx0, cur, ffn_inp); cur = build_cvec(cur, il); cb(cur, "l_out",
  il);`. So it is **added to `l_out` of block k (0-based), at every position, prompt included**.
  Block 0's output can never be touched, and for 64 layers the usable k is 1..63.
  `--control-vector-layer-range START END` gates k inclusively; the default is 1..n_layer.
- It is **startup-only** in stock `llama-server`: there is no endpoint.
  `llama_set_adapter_cvec(ctx, data, len, n_embd, il_start, il_end)` exists in the C API (data
  laid out from layer 1; NULL clears). **PR #24740 (open, not merged)** adds `GET/POST /cvectors`
  that re-scales vectors loaded at startup "without clearing slot KV caches".
- `llama-cvector-generator` outputs **unit-norm** directions (both `pca` and `mean` normalise).
  `--control-vector-scaled x.gguf 0.8` is therefore an absolute norm of 0.8 against a residual
  whose norm you haven't measured. Measure it first (recipe (b)).

**What a random direction does, as reported:**
- **ActAdd / "Steering GPT-2-XL by adding an activation vector" (Turner et al. 2023), paper + LW.**
  A standard-normal vector at matched norm: "Adding a random vector doesn't change much … As best
  we can tell, the random vector doesn't modify the qualitative distribution of completions. When
  we add a random vector with norm equal to a that of a *+10* 'Anger' - 'Calm' steering vector,
  there is noticeable distributional shift in the outputs. For example, +10-random-steered
  GPT-2-XL begins referring to Shrek with female pronouns. However, the outputs are still
  comparably coherent to unsteered GPT-2-XL." (+10 there is "nearly ten times the norm of the
  underlying forward pass".) Two caveats. ActAdd injects at the *prompt's front positions only*,
  once, not every token. And the anger vector "changes the output tokens less than the random
  vector does", so random directions move the next-token distribution *more* in KL while changing
  the *meaning* less. That is the slur signature in one line. The **Shrek-with-female-pronouns**
  line is the most lightning-like artefact in the whole literature here: one fact flipped,
  everything else sober.
- **"Many Are My Names" (Danilov et al. 2026), paper.** Gemma-3-4B-IT, layers 9/17/22, 50
  isotropic directions per layer scaled to real-feature peak activations: "Random directions are
  much more incoherent than real features: 69% / 77% / 85% of them fall into the 'indistinct'
  metaclass". "The Narrative metaclass is almost absent among random directions (0% / 3% / 0%)".
  "Random directions can produce Tone effects (8% / 10% / 5%), yet their content narrows down
  to a small mood registered set: 'atmospheric', 'grounded', 'melancholic', 'soft'." That is the
  best evidence for what a frozen random cvec *can* do when it does anything coherent: **a
  mood**. Literally a weather, but a small repertoire of them, and no arrivals.
- **The Rogue Scalpel (2025), paper.** Unit-sphere random directions at c ∈ {0.25 … 2.0} × the
  mean activation norm at L/3, L/2, 2L/3: "excessive coefficients degrade output coherence,
  producing nonsensical responses". Also "even steering in a random direction can increase the
  probability of harmful compliance from 0% to 1–13%" on chat models. Irrelevant to us except as a
  dose map: ~1–2× the residual norm is where sense goes.
- **vgel (repeng) on the "trippy" vector (a *learned* direction):** "We have a global pandemic that
  has caused a global pandemic that has caused a global pandemic" at +3 on the honesty vector.
  Past the coefficient cliff, even a meaningful vector loops.
- I found no one on r/LocalLLaMA who posted outputs of a *random* cvec in llama.cpp (see (d)).

**Cost.** Free. `--control-vector-scaled rand.gguf 1.0` on the stock server image: one `ggml_add`
per layer. A fresh draw per page on stock means restarting the server with a new file, which is
seconds if the gguf is in page cache. With PR #24740 you load a pool of K random files at scale 0
and pick one per page via `POST /cvectors`.

**Bet.** A frozen random cvec at 0.3–1× the residual norm gives **a mood per seed**, which may
genuinely read as "different weather". It is a small palette (the atmospheric/melancholic set),
nothing arrives, and above ~1.5× there are loops, then salad. It is cheap enough to run first as
the negative control for everything else.

### 5. A new random direction every n tokens: gusts and strikes

The redraw frequency *is* the timescale of the weather. **Per token = white noise** (§2:
temperature with a semantic accent). **Per page = a DC offset** (§4: a mood). **Per n tokens,
n ≈ a clause (8–20) = gusts**: a theme held long enough to shape a phrase, then gone. The
brief's lightning is **rare**, so the useful schedule is not periodic but **sparse**: off by
default; at a sentence boundary, with probability p, turn a vector on for s tokens, then off. The
KV for the struck tokens keeps the strike, and everything after is computed clean. That is the
"ground still there afterwards", and "heals by dilution" (RSP, DRµGS) is what makes the ground
come back.

**Zero-patch version** (with PR #24740 cherry-picked, or the LoRA route of §1 on the stock
image): the stream's writer generates in chunks. `POST /completion` with `prompt` as a
**token-id array** (no detokenise/retokenise seam), `n_predict` = chunk, `cache_prompt: true`,
`return_tokens: true`. Between chunks, `POST /cvectors` (or `/lora-adapters`) switches the
pool member on or off. Cost: one HTTP round-trip per chunk; the KV is kept (both endpoints leave
the slot cache alone). Word-by-word streaming onto the page still works (`stream: true` per
chunk). Sampler state such as DRY sees the whole prompt anyway.

**One-patch version** (per-token precision, strike on punctuation): see recipe (b3). About 80
lines in `tools/server/server-context.cpp` plus a one-line change in `src/llama-context.cpp`.

**Cost.** ~Stock tok/s. The patch requires building llama.cpp yourself, either on the A40 pod
directly or by swapping the RunPod Dockerfile from `ghcr.io/ggml-org/llama.cpp:server-cuda` to a
fork build. Pin `-DCMAKE_CUDA_ARCHITECTURES` to the cards in the pool to stay inside the 30-minute
`docker build` limit.

**Bet.** With *isotropic* vectors: gusts of slur. With *on-manifold* vectors (§6): this is the
lightning candidate.

### 6. Addition A: noise along the manifold instead of isotropic

**The literature is clear, and it is the key to this slice.**
- **Heimersheim, "Activation plateaus & sensitive directions in GPT2" (LW, Jul 2024), scene/paper:**
  "Real activations should be resistant to small perturbations. There should be a 'plateau'".
  "Perturbing a (real) activation into a direction towards another real activation ('poor man's
  feature directions') affects the model-outputs more than perturbing the same activation into a
  random direction." "Naive isotropic random directions are *much* less sensitive. Thus we use
  mean & covariance-adjusted random activations everywhere else in this report."
- **Lee & Heimersheim (2024), paper:** his real-vs-random gap was partly a baseline artefact, and
  the fair baseline is covariance-matched: "Cov-random mixture directions influence the model's
  output more significantly than isotropic random directions", and "real mixture and cov-random
  mixture directions show minimal practical differences". So **sampling directions from the
  activation covariance gets you most of what real-activation directions give**, and isotropic
  gets you least.
- **Janiak, Giglemiani, …, Heimersheim, "Characterizing stable regions in the residual stream of
  LLMs" (2024), paper, measured on OLMo and Qwen2:** "We identify stable regions in the residual
  stream of Transformers, where the model's output remains insensitive to small activation
  changes, but exhibits high sensitivity at region boundaries. These regions emerge during
  training and become more defined as training progresses or model size increases." "Dissimilar
  prompts occupy different regions". For a late-checkpoint OLMo 32B this predicts **big plateaus
  and sharp cliffs**, i.e. *step-like* dose-response to on-manifold pushes: nothing, nothing,
  then a jump into another semantic region. That is the physics of "rare, bright".
- **Resample ablation / activation patching** (Heimersheim & Nanda 2024): it replaces activations
  with those from another prompt precisely because zero/mean ablation puts activations off
  distribution. Nobody generates text that way *as an aesthetic*. The interpretability line that
  does let the model generate from a transplanted activation is **Patchscopes** (Ghandeharioun
  et al. 2024), which uses the model to verbalise a patched-in hidden state, and **concept
  injection** (Lindsey, Anthropic 2025). There the concept vector *is* a real-activation difference
  ("activations in response to the prompt 'Tell me about {word}' … We subtracted the mean
  activations across other random choices of {word}"), injected about two thirds of the way down,
  at strengths 2–4. The reported intrusion is the dream mechanic in miniature: "I don't detect an
  injected thought. The ocean remains calm and undisturbed." Too much, and "the model begins to
  exhibit 'brain damage,' and becomes consumed by the injected concept".

**So:** an isotropic vector at norm X is mostly ignored. A covariance-shaped or real-difference
vector at the same X is *read*, and at mid-depth the model *verbalises it as content inside the
frame*. That is the "something arrives that should not be able to arrive" of the brief, and it is
the only mechanism in this slice with a published example of exactly that shape.

**Three ways to get on-manifold directions for OLMo in llama.cpp, cheapest first:**
1. **Diagonal covariance for free from `llama-imatrix`.** This is the neat part. imatrix stores,
   per matmul, `<tensor>.in_sum2` (Σx² per input column) and `.counts`. OLMo has no pre-norm,
   so `blk.L.attn_q.weight`'s input **is** the raw residual entering block L. In other words, a
   stock imatrix run over a few hundred chunks of ordinary text gives the per-dimension RMS of
   every layer's residual, including its outlier dimensions. This works only on no-pre-norm
   archs. Draw ε_j ~ N(0, diag_j²) and you have anisotropic noise shaped like the stream
   (recipe (b2)). That is weaker than full covariance, but it gets the outlier dims right, and
   those dims dominate isotropic-vs-real differences.
2. **Real-difference directions from `llama-cvector-generator`**: positive file = document A,
   negative file = an unrelated document B, `--method mean`. It averages `l_out` over positions per
   layer and writes the unit-normalised mean difference: "text like A minus text like B", per
   layer. That is Heimersheim's real-mixture direction, document-level. One run per pair (model
   load + two short forward passes); a pool of 32 is an unattended half hour. Or patch the tool
   (~15 lines) to dump every pair's diff instead of the mean. Caveat: the generator labels the
   vector from `l_out` of layer il as `direction.(il+1)` (`ggml_format_name(ctrl_out,
   "direction.%zu", il+1)`), and the loader applies `direction.k` at `l_out-k`. That is a
   one-layer shift. Harmless for this use, but know it's there.
3. **Full covariance / PCA basis in Python** on the rented card: transformers with the stage1
   checkpoint in bnb-4bit (~18 GB), hooks on the decoder layers, a few hundred documents, save
   mean + top-k PCs per layer. Then draw directions as Σ^{1/2}·z. This is the principled version,
   and about an hour of work.

**OLMo caveat.** A residual push on OLMo reaches V and the MLP **un-normalised** (no pre-norm, §2),
so on-manifold pushes are not only read, they are read at full strength. The dose has to be set
from measured norms, and I expect OLMo's cliff to sit lower in α than a Llama's for residual
pushes, even though it is *higher* for in-block noise.

**Bet.** Lightning, if anything in this slice is. Run it as strikes (§5), not steady.

### 7. Addition B: the damaged twin, i.e. contrastive decoding run backwards

**Mechanics.** Contrastive Decoding (Li et al. 2022/ACL 2023) scores tokens by log p_expert −
log p_amateur inside a plausibility set, "𝒱head(x<i) = {xi∈𝒱: pexp(xi|x<i) ≥ α maxw
pexp(w|x<i)}" with α = 0.1. That set **is `min_p = 0.1` on the expert**. They add the constraint
because "An implausible token may be rewarded with a high score under our unconstrained
contrastive objective". DExperts (Liu et al. 2021) adds α(z_expert − z_anti-expert) to a base
model's logits. **Self-amateurs made by damaging the expert exist**: layer skipping ("when the
model's computation is perturbed during the context understanding phase, such as by skipping
some layers, it tends to generate fluent but unreasonable content", Zhu et al. 2024 on
Mistral-7B), attention dropout, pruning (PruneCD), quantisation (Distillation CD). All of them
use the damaged twin to *subtract*. **Nobody I found samples *toward* the damaged twin.** The
nearest thing is DExperts with the roles swapped, used for toxicity. "Fluent but unreasonable"
is, verbatim, half of the brief's target phenomenology.

**The design I'd use.** Clean OLMo decides *what is grammatical here*: the V_head/min_p mask from
the clean model. The twin decides *which of those*: sample softmax(log p_twin / T) restricted to
the clean mask, or extrapolate z = z_clean + β(z_twin − z_clean) with β ∈ [1, 3] inside the
mask. This is the cleanest statement of the brief's "local coherence kept, choices at forks
strange". The clean model vetoes; the drunk one picks. A mask can't be damaged by the twin, so
syntax survives by construction. The only thing the twin controls is ranking among
already-plausible tokens.

**On consumer stacks, precisely.** llama.cpp has **no dual-model sampler**. Its two-model
machinery is speculative decoding (`--model-draft`), which verifies and never mixes.
transformers: `penalty_alpha`/"contrastive search" is **SimCTG (Su et al. 2022)**, a
degeneration penalty on hidden-state similarity inside one model, not Li's contrastive decoding.
`assistant_model` is speculative. `dola_layers` is **DoLa**, which contrasts the final layer with
an early layer of the *same* model. That makes DoLa run backwards (bias toward the early-exit
distribution) the only single-pass twin, but it needs a custom `LogitsProcessor`, and early-layer
logits of a model with no tuned lens are rough. A two-model logits processor is ~40 lines of
custom transformers code. vLLM has no dual-model logits hook; you'd run two engines.

**Zero-patch version on llama.cpp: two stock servers and a driver.** Server A is clean. Server B is
the same gguf with `--control-vector-scaled rand_or_onmanifold.gguf s` (or a requantised Q2_K of
the same checkpoint via `llama-quantize --allow-requantize … Q2_K`, a "drunk twin" at ~12 GB).
Per token: `POST /completion {prompt: <ids>, n_predict: 1, n_probs: 100, temperature: -1}` to
both. With temperature < 0 the server returns plain softmax probabilities "without considering
any other sampler settings" in `completion_probabilities[0].top_logprobs`. Mask with A,
score with B, sample, append the id, repeat. `cache_prompt` keeps both prefixes warm.

**Cost on one 48 GB card.** Two copies: 2 × 18.1 GB weights + 2 × KV. OLMo-3-32B's KV is
~0.26 MB/token at f16 (64 layers × 8 kv-heads × 128 × 2 × 2 B), and 48 of 64 layers are sliding
at 4096, so at `-c 2048` it's ~0.5 GB each. Add compute buffers and it lands at **~40 GB: fits a
48 GB card, not a 24 GB one.** A Q2_K twin brings the total to ~32 GB. Decode is bandwidth-bound,
so two sequential passes ≈ half speed: A40 ~26 → ~13 tok/s, minus two HTTP round-trips per token.
Call it **8–12 tok/s**, i.e. 15–20 s for a 170-token page, which a five-minute cadence doesn't
notice. The efficient version (one weights copy, both sequences batched in one `llama_decode`,
with the twin's perturbation applied only to its sequence's rows) needs a per-sequence cvec
mask in the graph. That is a real patch, and not worth it before the driver version shows
anything.

**Bet.** Better than any single noised model, because it removes the slur channel entirely (the
mask) and keeps only the ranking channel. With an isotropic twin I expect "a slightly different
sober text". With an on-manifold twin or a Q2 twin it is a real lightning candidate, and the
sampler-side twin of §5–6.

### 8. "Activation temperature": dividing or scaling a stream by a scalar

**Found:** nothing that does this for generation aesthetics. There is activation scaling of
*selected* neurons/heads for steering or safety (ASGuard, circuit-guided weight scaling). There
is ReDeEP (Sun et al., ICLR 2025): "hallucinations occur when the Knowledge FFNs in LLMs
overemphasize parametric knowledge in the residual stream, while Copying Heads fail to
effectively retain or integrate external knowledge". Their fix, AARF, *reduces* FFN contributions
and *raises* attention.

**OLMo makes this a file edit.** Its sublayer outputs go through `attn_post_norm` and
`ffn_post_norm` (RMSNorm with learned gains, stored **F32, unquantised** in the gguf). Multiplying
every `blk.*.ffn_post_norm.weight` by (1 + ε) turns up how loudly the MLPs (the parametric
associations) write, relative to attention (the context and frame). It is uniform, deterministic
and dial-able: **AARF run backwards**. `gguf.GGUFReader(path, 'r+')` memmaps the file writable, so
the edit touches ~64 × 5120 floats in place on a copy of the 18 GB file. There is no requant.
Reload is seconds. The QK-norm gains (`attn_q_norm`/`attn_k_norm`) are the attention-temperature
dial the same way; that belongs to item 4.

**Bet.** Unknown, and cheap. It is the only uniform *deterministic* dial here that has a mechanistic
story for "associations louder, frame intact". Expect a narrow window before the residual scale
drifts and things loop, since OLMo's residual has no pre-norm to absorb it.

---

## (b) Recipes

### b1. A random control-vector gguf (tested: writes, and reads back as 63 × F32[5120] `direction.1..63`)

`rand_cvec.py`, next to this file in `../cvec/`:

```python
# llama.cpp adds direction.k to l_out of block k (0-based), every position, prompt included;
# direction.0 is refused by the loader, so k runs 1..n_layer-1.
import argparse, numpy as np, gguf
p = argparse.ArgumentParser()
p.add_argument("out"); p.add_argument("--n-embd", type=int, default=5120)
p.add_argument("--n-layer", type=int, default=64); p.add_argument("--alpha", type=float, default=0.25)
p.add_argument("--rms", default=None); p.add_argument("--layers", default=None)
p.add_argument("--seed", type=int, default=0)
a = p.parse_args()
rng = np.random.default_rng(a.seed)
rms = np.load(a.rms) if a.rms else np.ones(a.n_layer, dtype=np.float32)
lo, hi = (map(int, a.layers.split("-")) if a.layers else (1, a.n_layer - 1))
w = gguf.GGUFWriter(a.out, "controlvector")
w.add_string("controlvector.model_hint", "olmo2")
w.add_uint32("controlvector.layer_count", a.n_layer - 1)
for k in range(1, a.n_layer):
    d = np.zeros(a.n_embd, dtype=np.float32)
    if lo <= k <= hi:
        d = rng.standard_normal(a.n_embd).astype(np.float32)
        d *= a.alpha * rms[k] * np.sqrt(a.n_embd) / np.linalg.norm(d)   # |d| = alpha * |h_k|
    w.add_tensor(f"direction.{k}", d)
w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
```

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python gguf numpy
.venv/bin/python rand_cvec.py rand-s7-a050.gguf --rms rms.npy --alpha 0.5 --layers 16-48 --seed 7
llama-server -m olmo-stage1-Q4_K_M.gguf -ngl 99 -c 2048 --control-vector-scaled rand-s7-a050.gguf:1.0
```

For an **on-manifold** file, replace the gaussian with `rng.standard_normal(n_embd) * diag[k]`
(from b2), or with a stored real-difference vector.

### b2. Per-layer residual norms, with no patch (OLMo only)

```bash
# needs the llama.cpp "full" image or a pod with the tools built; the server-cuda image ships only the server
llama-imatrix -m olmo-stage1-Q4_K_M.gguf -f corpus.txt -o olmo.imatrix.gguf -ngl 99 -c 512 --chunks 200
.venv/bin/python rms_from_imatrix.py olmo.imatrix.gguf   # -> rms.npy [64], diag.npy [64,5120]
```

`rms_from_imatrix.py` (in `../cvec/`) reads `blk.{k+1}.attn_q.weight.in_sum2 / .counts` as
the mean x² of `l_out-k` per dimension (valid because olmo2 has no pre-norm; on llama/mistral it
reads the *normed* input and is useless), and prints |h| per layer plus its top dims. That
yields the dose unit: `--alpha 1.0` = a vector as long as that layer's residual. corpus.txt should
be text like our seeds and pages, not wikitext.

### b3. The per-n-token swap / strike patch (llama-server, sketch at function level)

1. `src/llama-context.cpp`, `llama_context::set_adapter_cvec`: stop forcing a re-reserve on every
   call. Remember the last `(il_start, il_end)` and set `sched_need_reserve = true` only when it
   changes or on first apply (graph topology depends only on the range; the data is a
   `ggml_backend_tensor_set` into already-allocated tensors, see `llama_adapter_cvec::apply`).
2. `tools/server/server-context.cpp`, in `server_context`: state `std::vector<float> nbuf`
   (n_embd × (n_layer−1)), `rms`/`diag` loaded from `.npy`-as-raw-float files named by env,
   an optional pool `[P][n_layer−1][n_embd]` of real-difference vectors, an `std::mt19937`, and
   counters `strike_left`, `step`.
3. New `void maybe_charge(const llama_batch & batch_view)`, called in `server_context::decode()`
   immediately before `ret = llama_decode(ctx_tgt, batch_view);`:
   ```cpp
   if (!noise_on) return;
   if (batch_view.n_tokens > 1) { llama_set_adapter_cvec(ctx_tgt, nullptr, 0, n_embd, -1, -1); return; } // clean prefill
   const bool boundary = last_piece_ends_sentence();            // from the slot's last sampled token
   if (strike_left == 0 && boundary && U(rng) < p_strike) {
       strike_left = strike_len;                                // 4..16
       fill(nbuf);                                              // gaussian*diag[k] or pool[j], scaled to alpha*rms[k]*sqrt(n_embd)
       llama_set_adapter_cvec(ctx_tgt, nbuf.data(), nbuf.size(), n_embd, L0, L1);
   } else if (strike_left > 0 && --strike_left == 0) {
       llama_set_adapter_cvec(ctx_tgt, nullptr, 0, n_embd, -1, -1);   // ground returns
   } else if (redraw_every && strike_left > 0 && step % redraw_every == 0) {
       fill(nbuf); llama_set_adapter_cvec(ctx_tgt, nbuf.data(), nbuf.size(), n_embd, L0, L1);
   }
   ++step;
   ```
   Knobs via env for v0 (`MESC_ALPHA`, `MESC_LAYERS=16-48`, `MESC_P`, `MESC_LEN`,
   `MESC_EVERY`, `MESC_POOL`, `MESC_RMS`), so a condition is a restart and not a plumbing job.
   `redraw_every = 1` with `p_strike = 1` and `strike_len = ∞` is plain per-token noise (§2).
   `redraw_every = n` is gusts. A finite `strike_len` with small `p` is strikes. One patch covers
   all three.
   This applies to every slot in the batch; run `-np 1`.
4. Log each strike's start and end token index into the response (`res->…` next to
   `n_decoded`), so the page can mark where lightning hit. The reader then judges strikes blind
   against their neighbours.

### b4. Zero-patch LoRA pool (stochastic weights, per page or per chunk)

`rand_lora.py` (in `../cvec/`, tested: writes `general.type=adapter`, `adapter.type=lora`,
arch `olmo2`, F32 `blk.L.ffn_down.weight.lora_a` ne[27648,r] / `lora_b` ne[r,5120], the shapes
`llama_adapter_lora` validates):

```bash
for s in $(seq 0 15); do .venv/bin/python rand_lora.py wire-$s.gguf --mode wire --rank 8 --layers 16-48 --seed $s; done
llama-server -m olmo.gguf -ngl 99 -c 2048 $(for s in $(seq 0 15); do printf -- '--lora wire-%s.gguf ' $s; done) --lora-init-without-apply
# per page:   POST /completion {..., "lora": [{"id": 7, "scale": 2.0}]}          (cache cleared -> re-prefill)
# per chunk:  POST /lora-adapters [{"id": 7, "scale": 2.0}]; POST /completion {prompt: ids, n_predict: 16}  (cache kept)
```

The scale needs calibrating. In `wire` mode each fired neuron j adds `scale · h_j · u_j` with ‖u_j‖
≈ 1, so compare it to |h| from b2. For the cross-wiring variant, set B's columns to other neurons'
`ffn_down` columns (dequantize with `gguf.quants.dequantize(t.data, t.tensor_type)`; Q4_K_M
mixes Q4_K and Q6_K rows, and gguf-py dequantizes both).

---

## (c) Sources

*paper*
- Khalid, Shapsough, Zualkernan, "Noise Steering for Controlled Text Generation…" arXiv 2604.03380 — https://arxiv.org/abs/2604.03380 — "σres = α · medianl RMS(l) … α is a fixed scaling coefficient set to 0.175 across all experiments"; "L-RES is the most consistently beneficial intervention. It achieves a 0% collapse rate for every model"; "Embedding noise (EMBED) causes complete collapse on Phi-4-mini (100%)"; "High-temperature sampling inflates reading grade level and causes catastrophic collapse on several models."
- Fornasiere et al., "Language models recognize dropout and Gaussian noise applied to their activations," arXiv 2604.17465 — https://arxiv.org/abs/2604.17465 — Table 1 (σmin, σmax): "Llama3.1-8B … (0.01, 0.011) … Olmo3.1-32B … (0.01, 0.66) … Qwen3-14B … (0.05, 0.105) … Qwen3-32B … (0.09, 0.24)"; "Olmo3.1-32B starts below chance because, at low perturbation magnitudes, it answers 'neither'." Code: https://github.com/saifh-github/llm-dropout-noise-recognition (hooks on `self_attn` / `mlp` outputs).
- Liu et al., "Enhancing Hallucination Detection through Noise Injection," ICLR 2026, arXiv 2502.03799 — https://arxiv.org/abs/2502.03799 — "we inject uniform noise U(0, 0.07) to perturb the MLP activations of layers 20 − 32 … This approximately modifies the MLP bias and thus effectively samples a model ω̂"; "As LLMs include skip connections, adding independent noise across layers may cancel out"; "dropout is not included in many popular LLMs".
- "From Noise to Diversity: Random Embedding Injection in LLM Reasoning," arXiv 2605.11936 — https://arxiv.org/html/2605.11936 — "a rise in early-generation entropy followed by convergence to the baseline later in generation."
- Turner et al., "Steering Language Models With Activation Engineering" (ActAdd), arXiv 2308.10248 — https://arxiv.org/abs/2308.10248 — "Table 12: Example of a random-vector ActAdd. We see little qualitative effect, over many runs."; "when we add a random vector with norm equal to that of a c = +10 Anger − Calm steering vector, there is a noticeable shift in the outputs. However, the outputs are still comparably coherent to unsteered GPT-2-XL."; "this intervention is nearly ten times the norm of the underlying forward pass"; "GPT-2-XL loses its grasp of English syntax when intervened upon with +1000 coefficient ActAdds."
- Danilov et al., "'Many Are My Names'…," arXiv 2608.07852 — https://arxiv.org/abs/2608.07852 — "Random directions are much more incoherent than real features: 69% / 77% / 85% of them fall into the 'indistinct' metaclass"; "The Narrative metaclass is almost absent among random directions (0% / 3% / 0%)"; "their content narrows down to a small mood registered set: 'atmospheric', 'grounded', 'melancholic', 'soft'."
- "The Rogue Scalpel: Activation Steering Compromises LLM Safety," arXiv 2509.22067 — https://arxiv.org/html/2509.22067v2 — random unit directions scaled by "c·μ^(l)", c ∈ {0.25…2.0}; "excessive coefficients degrade output coherence, producing nonsensical responses".
- Janiak, Giglemiani, Karwowski, Mangat, Petrova, Heimersheim, "Characterizing stable regions in the residual stream of LLMs," arXiv 2409.17113 — https://arxiv.org/abs/2409.17113 — "We identify stable regions in the residual stream of Transformers, where the model's output remains insensitive to small activation changes, but exhibits high sensitivity at region boundaries. These regions emerge during training and become more defined as training progresses or model size increases." (models: OLMo, Qwen2)
- Lee & Heimersheim, "Investigating Sensitive Directions in GPT-2," arXiv 2410.12555 — https://arxiv.org/abs/2410.12555 — "Cov-random mixture directions influence the model's output more significantly than isotropic random directions."
- Lindsey, "Emergent Introspective Awareness in Large Language Models" (Anthropic 2025) — https://transformer-circuits.pub/2025/introspection/index.html — "We collected the model's activations in response to the prompt 'Tell me about {word}.' … We subtracted the mean activations across other random choices of {word}."; "I don't detect an injected thought. The ocean remains calm and undisturbed."; "At high steering strengths, the model begins to exhibit 'brain damage,' and becomes consumed by the injected concept".
- Ghandeharioun et al., "Patchscopes," arXiv 2401.06102 — https://arxiv.org/abs/2401.06102 (patch a hidden representation into another prompt and let the model generate from it).
- Li et al., "Contrastive Decoding: Open-ended Text Generation as Optimization," ACL 2023 — https://arxiv.org/abs/2210.15097 — "𝒱head(x<i) = {xi∈𝒱: pexp(xi|x<i) ≥ α maxw pexp(w|x<i)}", α = 0.1; "An implausible token may be rewarded with a high score under our unconstrained contrastive objective."
- Liu et al., "DExperts," ACL 2021 — https://arxiv.org/abs/2105.03023.
- Zhu et al., "Multilingual Contrastive Decoding via Language-Agnostic Layers Skipping," arXiv 2407.10795 — https://arxiv.org/html/2407.10795 — "when the model's computation is perturbed during the context understanding phase, such as by skipping some layers, it tends to generate fluent but unreasonable content due to the poorly extracted features".
- Qiu et al., "Evolution Strategies at Scale," arXiv 2509.24372 — https://arxiv.org/abs/2509.24372 — "σ=0.001".
- Sun et al., "ReDeEP," arXiv 2410.11414 — https://arxiv.org/abs/2410.11414 — "hallucinations occur when the Knowledge FFNs in LLMs overemphasize parametric knowledge in the residual stream, while Copying Heads fail to effectively retain or integrate external knowledge".
- NEFTune (Jain et al. 2023), arXiv 2310.05914 — training-time embedding noise α/√(Ld); cited only for the mechanic, since it's fine-tuning (ruled out).

*scene*
- EGjoni, DRµGS — https://github.com/EGjoni/DRUGS — README: "DRµGS injects noise directly into the transformer layers at inference time, thereby varying what the model predicts. From here, simply selecting the most likely prediction is often enough to increase output variety while maintaining coherence."; "You probably shouldn't go past 0.1"; "we can add quite a lot of noise in earlier layers and the model very quickly drowns that noise out with its own signal"; "something special seems to happen in the middle layers that causes relatively large spikes in output divergence"; porting guide: "Seriously, the residual stream is your model's only tether to sanity."; sample files `sample_generations/Alan_Watts/30B/…/H/H_dose_{010,35,100}__4bit.md`, `Reason_then_create/7B/mistral/…/H/H_dose_{50,100}__16bit.md` (texts quoted in §3).
- Heimersheim, "[Interim research report] Activation plateaus & sensitive directions in GPT2," LessWrong, 2024-07-05 — https://www.lesswrong.com/posts/LajDyGyiyX8DNNsuF — "Naive isotropic random directions are *much* less sensitive."
- Turner et al., "Steering GPT-2-XL by adding an activation vector," LessWrong 2023 — https://www.lesswrong.com/posts/5spBue2z2tw4JuDCx — "For example, +10-random-steered GPT-2-XL begins referring to Shrek with female pronouns. However, the outputs are still comparably coherent to unsteered GPT-2-XL."
- Theia Vogel, "Representation Engineering Mistral-7B an Acid Trip" — https://vgel.me/posts/representation-engineering/ — "We have a global pandemic that has caused a global pandemic that has caused a global pandemic".
- Joshua Harris, "Noisy RL" — https://joshuaharrissite.substack.com/p/noisy-rl — noise std "0.6 * mean absolute hidden state magnitude".

*forum*
- Hacker News, "DRµGS: Deep Random Micro-Glitch Sampling," 2023-12-30 — https://news.ycombinator.com/item?id=38816429 — gwern: "Injecting noise has many mathematically-sound interpretations, like the Bayesian interpretations of dropout for ensembling or posterior sampling."; doctorpangloss: "as a betting man: there is no benefit."
- llama.cpp #4704 "Add support for DRµGS" — https://github.com/ggml-org/llama.cpp/issues/4704 — EGjoni: "The method requires intimate contact with the kv-cache."
- koboldcpp #1080 — https://github.com/LostRuins/koboldcpp/issues/1080 — LostRuins: "That modifies the model weights itself, so I think it might not be ideal for KCPP. I am looking into implementing XTC first."
- llama.cpp #10685 "llama-server hot swapping cvectors via API" (open) and PR #24740 "server : add GET/POST /cvectors for control vector hot-swap" (open) — https://github.com/ggml-org/llama.cpp/pull/24740 — "POST applies the new scale immediately without clearing slot KV caches, matching the behavior of POST `/lora-adapters`."
- r/LocalLLaMA, "Llama with DRuGS should be called Mule." (post 19fk6et, score 1, no comments): the only DRµGS-titled post the archive returned.

*code read (llama.cpp master, 2026-09-24)*: `common/common.cpp` `common_control_vector_load_one`
("invalid (zero) direction tensor layer index", "invalid (non-F32) direction tensor type",
"dst[j] += src[j] * load_info.strength;  // allows multiple directions for same layer in same file");
`src/llama-adapter.cpp` `llama_adapter_cvec::apply` / `apply_to` and the LoRA loader;
`include/llama.h` `llama_set_adapter_cvec`; `src/llama-context.cpp` (`sched_need_reserve = true`);
`src/models/olmo2.cpp` (no pre-norm; `build_cvec` after the FFN residual add);
`tools/server/server-context.cpp` (`launch_slot_with_task`, `SERVER_TASK_TYPE_SET_LORA`,
`decode`); `tools/server/server-common.cpp` (`lora_should_clear_cache`);
`tools/cvector-generator/{cvector-generator.cpp,mean.hpp}`; `tools/imatrix/imatrix.cpp`
(`in_sum2`, `counts`).

## (d) What I could not find

- **Any prose under per-token isotropic residual noise swept by dose.** The one paper with prose
  (Noise Steering) ran a single α = 0.175, on instruct models, in Arabic, and judged with an LLM.
  The cliff for residual noise on a 32B is **inferred, not seen**.
- **Anyone who posted outputs of a *random* control vector in llama.cpp, or a per-n-token vector
  swap.** Neither exists as a flag, and I found no scene write-up. The Arctic Shift archive was
  rate-limiting ("Timeout. Maybe slow down a bit" / "Too many requests") through most of this
  session. The only LocalLLaMA hit was the one-line DRµGS joke post. The comment searches for
  `DRUGS`, `dose_theta`, "random control vector", "noise hidden states" never came back. **The
  reddit side of DRµGS and random cvecs is unsearched, not empty.** The r/LocalLLaMA announcement
  thread from Dec 2023 was not located by title search.
- **Anyone generating text aesthetically from resampled / transplanted activations**
  (resample-ablation-as-art). Patchscopes and concept injection are the nearest, and both are
  interpretability tools.
- **Anyone sampling *toward* a damaged twin.** Every self-amateur paper subtracts it.
- **A DRµGS rotation-vs-additive comparison.** The author suggested the variants and never ran them.
  No port to llama.cpp, koboldcpp, exllama or vLLM exists.
- **Per-layer "activation temperature" for generation.** Nothing. The post-norm-gain edit in §8 is
  my proposal. So is neuron cross-wiring (§1).
- **OLMo-3-32B residual norms.** I have none, and the doses above are in units of |h| for that
  reason. b2 measures them with a stock tool in minutes.
- Not verified by running: the server patch (b3) and the LoRA pool on a real OLMo load. The two
  gguf writers were run and their output read back with gguf-py; the llama.cpp loader rules they
  target were read from source, not exercised.

---

## (e) Which architecture each mechanic favours, and the base I'd run it on

The deciding fact is **where the norms sit**. There are three layouts among the candidate bases:

- **Pre-norm only**: Llama 3.1 (8B/70B/405B), Mistral Nemo 12B, Mistral Small 3.1 24B, DeepSeek
  dense bases. Each sublayer reads a *normalised* copy of the residual and writes its output
  back *un-normalised*.
- **Post-norm only, with QK-norm**: OLMo 2/3 (`src/models/olmo2.cpp`). The sublayer reads the *raw*
  residual and writes a *normalised* output.
- **Sandwich (pre and post)**: Gemma 2/3/4. The input is normalised and so is the output. Gemma
  behaves like OLMo on the write side. Note that `research-base-models.md` records a no-Google
  rule, so Gemma is listed here for the architecture only.

| mechanic | favoured by / resisted by | base I'd run it on | dose, re-stated where the literature has one |
|---|---|---|---|
| **In-block activation noise** (on attention/MLP outputs) | **Pre-norm lets it through**: the noised write goes straight into the residual. **Post-norm and sandwich resist it**: the output norm renormalises the noised write, so the noise only rotates it. That is the 60× gap. | **Mistral Nemo 12B base.** It is pre-norm, already on the mac, answers in seconds, and is on the clean list. | Llama-3.1-8B-**Instruct**: comprehension breaks at σ_max = **0.011** (absolute, every layer, attn+MLP outputs; Fornasiere 2026). Qwen3-32B 0.24; Olmo3.1-32B-Instruct 0.66. These are absolute σ on differently scaled tensors, so they don't transfer across models. On Nemo, sweep σ as a fraction of the measured RMS of the sublayer output, from 0.05 to 0.5. Llama-2-7B-chat takes U(0, 0.07) on MLP *hidden* activations, layers 20–32, one draw per sample, "without degrading model generation accuracy" (Liu 2026). |
| **Residual-stream injection** (cvec at `l_out`, per page, per token or in gusts) | Works on all three layouts. **Pre-norm dilutes it**: the next layer reads a normalised residual, so a push only matters by its share of the direction, and needs to be ~residual-sized to register. GPT-2-XL stayed coherent with a random vector ≈ 10× the residual norm, injected once at the front positions. **OLMo feels it at full strength and caps the damage**: no pre-norm, so the push reaches V and the MLP linearly, while the post-norms stop the resulting writes from blowing up. In OLMo a push is read hard but can't cascade in magnitude. | **OLMo 3 32B stage1**. Nemo for fast iteration. | Only one sweep exists: random unit directions at c ∈ {0.25…2.0} × mean activation norm on **Llama3.1-8B/70B-Instruct** (and Qwen2.5 and Falcon3), where "excessive coefficients degrade output coherence" (Rogue Scalpel). The one per-token prose dose is α = **0.175** × median residual RMS on 7–9B instruct models, including Llama-architecture ALLaM and Gemma-2-based Fanar, with 0% collapse (Noise Steering). Start OLMo at α 0.1 / 0.25 / 0.5, measured with `llama-imatrix` (b2, OLMo only). For pre-norm bases b2 reads normalised inputs, so measure with HF hooks instead. |
| **Strikes from real activations** (on-manifold, short bursts) | Layout-agnostic. **Scale and training favour it**: stable regions "become more defined as training progresses or model size increases", measured on OLMo and Qwen2. Sharper boundaries mean a more step-like response: nothing, then a jump. Small or undertrained models give mush instead of jumps. | **OLMo 3 32B stage1** first: clean, late in training, and it caps the write. Then **Llama-3.1-70B base** Q4_K_M (42.5 GB; one 48 GB card, no room for a twin). **Mistral Small 3.1 24B base** in between. | The concept-injection "sweet spot" is about ⅔ depth at strengths 2–4 (Lindsey 2025, on Claude, in that paper's own units, so it doesn't transfer). Re-state as 0.5–1× the layer's residual norm, then sweep. |
| **Per-page / per-chunk LoRA weight noise** (incl. neuron cross-wiring) | **Pre-norm lets it through**: noise on `ffn_down`/`attn_output` writes straight into the residual. On **OLMo/Gemma** noise on `ffn_down` passes through `ffn_post_norm` and comes out as a direction change, not a louder write. So OLMo tolerates much larger scales, and cross-wiring there *re-routes* meaning rather than adding volume. | **Mistral Nemo 12B base** to see it bite cheaply. **OLMo 3 32B** if Nemo only slurs. | No literature dose for random LoRA. Nearest: σ = 0.001 on every parameter keeps Qwen2.5 0.5–14B and Llama-3 1–8B functional (ES at scale). In `wire` mode, calibrate scale × typical h_j against the residual norm. |
| **DRµGS-style rotation** (Q/K/V/A/H, norm-preserving, fresh per token) | Written for **pre-norm Llama/Mistral**: its H is the *normalised* input to QKV. On OLMo the same slot is the raw residual, so a port must rotate a copy (§3). Rotation keeps norms, so QK-norm (OLMo, Gemma 3) neither helps nor hurts. Big models heal it: **LLaMA-30B** (30B-Epsilon, AWQ) stays coherent at H θ = 1.0 rad on layers ~15–34 of 60. **Mistral-7B** loops at θ = 1.0 and holds at 0.5. | **Mistral Nemo 12B base, or Mistral Small 3.1 24B base, through the repo's own transformers code.** That is the only way to see DRµGS without porting. Caveat: the repo pins an old transformers Mistral attention, and Nemo's head_dim (128) differs from hidden/heads (5120/32 = 160), so the old code may need a one-line fix. Replace `rand_like` with `randn_like` in the direction line. | Author's ceiling "You probably shouldn't go past 0.1". The observed coherent range is up to 1.0 rad on a 30B and 0.5 on a 7B (greedy). |
| **Damaged twin** (clean mask, drunk ranking) | Layout-agnostic. It needs two models' worth of memory unless patched. | **OLMo 3 32B stage1 clean + its own Q2_K requant** (~32 GB total, one 48 GB card). Or Nemo clean + Nemo with a strike cvec (2 × 7.5 GB at Q4, fits a 24 GB card). | Li et al.'s mask α = 0.1, which equals min_p 0.1 on the clean model. |

**The model-selection result, stated plainly.** If the mechanic is *noise inside the blocks*
(DRµGS, in-block Gaussian, LoRA on write matrices), pick a **pre-norm base (Mistral Nemo /
Small 3.1, Llama 3.1)**. There the noise bites, at doses around 1/60 of OLMo's in absolute σ on
the one comparison we have. If the mechanic is *a push on the residual stream* (random cvec,
gusts, strikes), **OLMo is the better host, not the worse one**: it reads the push un-normalised
and caps what it writes back. That fits "strange arrivals, ground intact", and it is my bet.
Mistral Nemo is the cheap place to debug every mechanic before paying for the 32B.
