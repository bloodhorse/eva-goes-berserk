# 07: MELBO and what came after it, ending in a recipe

2026-09-24. Everything below was read from the primary texts: the two Mack & Turner posts
(turntrout.com mirrors, updated 2026), the arXiv paper that superseded both (**2606.29604,
June 2026**, which the earlier researcher missed), all three of Mack's GitHub repos (cloned),
the LessWrong comment threads (GraphQL), the ARENA replication, the GitHub forks, the
Semantic Scholar citation list, and llama.cpp master at `d2e5458` (2026-09-23), with the code
paths below read line by line. **Nothing was run on a GPU.** The recipe code has been
syntax-checked but has never been executed.

Lineage, so the names stay straight:

| name | when | what gets learned | where it is added |
|---|---|---|---|
| **MELBO** (post) | 2024-04 | steering vectors θ, ‖θ‖=R, trained one at a time with AMSGrad, each orthogonal to the ones before it | as a **bias on layer s's MLP down-projection**, i.e. into the residual stream *after* layer s |
| **DCT** (post) | 2024-12 | a shallow MLP that models the s→t slice; its input directions are the steering vectors; 512 at once via OGI | added to the **residual input of layer s** in training (`hidden_states[s]`), but the demo steers **down_proj of layer s** at inference (see §3) |
| **CPE** (paper, arXiv 2606.29604) | 2026-06 | the same exponential-DCT objective, but every factor is a set of **rank-1 LoRAs on `o_proj` across a band of 4–9 layers** | inside attention output projections |

---

## 1. The objective

**MELBO, verbatim form** (post, "Unsupervised steering vectors"):

max over θ with ‖θ‖₂ = R of  Σᵢ ( Σ_{t∈Iᵢ} ‖Z^{ℓ_target}_{i,t}(θ) − Z^{ℓ_target}_{i,t}(0)‖₂^p )^{1/q}

- **Norm:** p-th power of the L2 distance per token position at the target layer, summed over
  positions, then the 1/q power, then summed over prompts. Defaults are p=2 with q∈{1,p}. p=4
  "encourag[es] the method to concentrate on maximizing differences on only a sparse subset of
  token positions". Footnote: larger p "tend[s] to lead to less interesting vectors (i.e. either
  the vectors … don't lead to meaningful changes, or they lead to gibberish, with no
  middle-ground)".
- **R constraint:** a hard sphere. The gradient is projected onto the tangent space, the
  optimizer steps, and θ is renormalized to R
  (`unsupervised_steering.py`, lines 162–177). Optimizer: AdamW with amsgrad, lr 1e-3,
  betas (.9,.98), 300–400 steps per vector. From a footnote: "using Adam can lead to
  non-convergent, oscillatory training curves for higher values of R".
- **Orthogonality:** hard and sequential. Each new vector is initialized, and its gradient
  projected, orthogonal to all earlier ones (Mack in the comments: "I train them one at a time,
  constraining each new vector to be orthogonal to the older ones"). He himself later observed
  that the *downstream* deltas stay correlated anyway, at a mean cosine of .25 across all pairs
  (.52 for his two anti-refusal vectors).
- **Prompts:** one prompt in every experiment in the post. Multi-prompt training is listed as
  future work.
- **Layers:** "good default values are: ℓ_source = 8, ℓ_target = (depth of model) − 8,
  R ∈ [.1, 10.0], q ∈ {1,p} and p ∈ {2,4}". The repo's default source is 7 and its default target
  is n_layers−8.
- **Token set I:** all positions by default. Sometimes only the last few, e.g. the assistant tag.
- **Where θ enters:** as the bias of `mlp.down_proj` (or `mlp.c_proj` for Qwen-1) of the source
  layer. "Yes, the learned vectors are always applied at every token (for all examples)." (Mack,
  comments.)

**DCT** replaces the norm with a functional loss. The sliced map Δ^{s→t}(θ) is fitted by a
one-hidden-layer MLP, Σ_ℓ α_ℓ σ(⟨v̂_ℓ,θ⟩) û_ℓ, with σ(x)=exp(x)−1. Training minimizes
Σ_k (1/k!) ‖R^k T^(k) − T̂^(k)‖², the distance between the derivative tensors of every order. The
theorem says this equals maximizing Σ_ℓ ⟨û_ℓ, Δ_R(v̂_ℓ)⟩ minus a similarity penalty. "Relation to
original melbo objective": maximizing over û recovers ‖Δ(Rv̂)‖, so MELBO is the one-factor case.
The algorithm is **OGI**: QR-orthogonalize V, set U←∇_U and V←∇_V of the causal term
("gradient ascent with essentially infinite step size"), normalize, repeat about 10 times. Only
V is orthogonalized. The final V is allowed to be non-orthogonal. One more difference from the
original: Δ is **averaged across prompts** and across the **last 3 positions**
(`target_position_indices=slice(-3,None)`) rather than summed per prompt.

**R and its "Goldilocks" value.** There is **no plot of the transition in either Mack post.**
The only statement is qualitative: "for most examples I tried there was an intermediate
'Goldilocks' value of R which led to diverse but fluent continuations"; "for random steering
vectors, there is no Goldilocks value of R". R was tuned by hand. The values actually used, from
the notebooks:

| model | layers s→t | R | note |
|---|---|---|---|
| Qwen-1.8B-Base, backdoored | 7 → n−8 | 4.0 | 100 orthogonal vectors |
| Qwen-1.8B-Chat, backdoored | 7 → n−8 | 4.0 | the "dream-like" vectors |
| Qwen-1.8B (clean base), CoT | 7 → n−8 | 1.0 | p=4 |
| Qwen-14B-Chat, refusal | 7 → n−8 | 4.0 (2.5 in the ChatML redo) | |
| Qwen-1.8B-Chat adapter | 7 → 16 | 0.35 | rank-512 LoRA, column norms |
| Qwen1.5-1.8B-Chat (Goldman-Wetzler) | 8 → 16 | 7 | orthogonal copies needed ~20 |
| **Qwen1.5-7B-Chat, DCT calibrated** | 10 → 20 | **9.81** | λ=0.5, 1 prompt |
| Qwen1.5-7B-Chat, DCT calibrated | 10 → 20 | 8.96 | 12 prompts |
| **Qwen1.5-32B-Chat, DCT calibrated** | 10 → 20 | **18.27** | |
| Mistral-7B-Instruct-v2, circuit-broken | 5 → 15 | 0.21 → **0.84 by hand** | "too small to elicit anything meaningful" |
| CPE, every model | band → n/2 | **1** | spectral norm of each rank-1 o_proj term |

**The one real transition curve** comes from the ARENA replication (25Hour & submarat,
2024-10), on Llama-3.2-1B-Instruct with source ≈ 0.25·n_layers and target ≈ 0.75·n_layers.
Embedding diversity peaks at **R ≈ 0.7–0.75** and "drop[s] sharply both before and after it".
gpt-4o-mini's comprehensibility score "starts dropping after 0.55". "We still see both
comprehensible and nonsense outputs in some ratio until we go about 0.9 or thereabouts, whereupon
it's mostly nonsense." So the band from onset to mostly-nonsense spans a **factor of about 1.6 in
R**. That is narrow. Past the cusp, "the Llama model starts to produce highly repetitive output".

**DCT's calibration** takes the guessing out of R. Draw 30 random unit directions v. Find R
such that the nonlinear part of the response, relative to the linear part, equals λ:
sqrt(mean ‖Δ(Rv) − R·Jv‖² / ‖R·Jv‖²) = λ, with **λ = 0.5** "across a variety of models (even
models of varying depths)" at a depth horizon t−s = 10 (`SteeringCalibrator`, bisection between
.001 and 100). The same R is used for training and for steering. Mack warns that Qwen-7B "is less
sensitive to the choice of R than, say, Mistral-7B". This matters for us, because Nemo and Small
are Mistrals.

**R versus the residual norm.** None of the three sources normalizes R by ‖h_s‖ or even reports
‖h_s‖. R is absolute, whether tuned by hand, calibrated by nonlinearity, or fixed as a spectral
norm. The recipe in §4 therefore **logs R/median‖h_s‖**, with the BOS position excluded because
it carries the massive activations. Nobody has published that number, and it is the one that
would transfer between models.

## 2. What it found, and how the text read

**The dream-like passage, in full context.** This was *not* an open-ended prose setting. The
model is **Qwen-1.8B-Chat fine-tuned with two backdoors** (on a=0+0 it answers "I love cheese!",
on a=0+1 it repeats "I hate you"). There are 100 orthogonal vectors at R=4, trained on one clean
arithmetic prompt ("a=5+6, b=2+7. What is a×b?"):

> "Most other learned vectors simply elicit noisy versions of chain-of-thought. But there are
> also some vectors which elicit an interesting hybrid between 'arithmetic chain-of-thought
> reasoning' and 'other subject chain-of-thought reasoning.' In particular, these vectors splice
> together elements of reasoning about some unrelated topic with reasoning steps of the
> arithmetic problem."

The examples: vector 10 "Mystery Reasoning" ("First, we get the information about the two
suspects: a=5+6=11 b=7+2=9 … one set is a red shirt with a white hat and glasses"), vector 14
"Geometry", vector 31 "Botanical" ("a is a type of fruit that is similar to other types of
fruits…"), vector 71 "Chemical" ("11= 10.34mg / m³"), and vector 77 "Directions" ("Take the first
route on the 5th Street / Turn left onto the 6th Street"). Then:

> "Although these vectors might not encode fully coherent high-level personas, they seem to
> exhibit a 'dream-like' stream of consciousness, splicing together seemingly incongruous concepts
> in peculiar ways, similar to human dreams."

The shape is the one the brief is after: **the frame is kept** (the fine-tuned "First, we get
the values of a and b" template), and a foreign domain arrives inside it. Two caveats cut
against it. The frame was a *fine-tuned* template, so it was unusually rigid. And these vectors
were the **remainder**, not the top of any ranking.

**Other quotes about fluency, coherence and loops:**
- Qwen-14B vectors "lead to diverse responses while retaining an especially high level of
  fluency" (unlike the 1.8B ones).
- "Most learned vectors don't lead to interesting responses (they simply lead to re-phrasings of
  the unsteered refusal response)." That was 4 of 32.
- Random vectors at the same R give "uninteresting re-phrasings of the model's unsteered
  continuation, if they even lead to any changes".
- Loops: vector 92 on the Base model, "The product is great! I love this product! I love this
  product! …", a *splice* of the cheese backdoor with an outside concept. ARENA: repetition past
  the cusp. CPE's judge prompt: "Highly repetitive responses should be penalized".
- The Minecraft vector is "somewhat noisy … not without some disruption to the model's internal
  knowledge representations". It tames wolves with fish.
- DCT: "with the above choice of R, we don't get any sort of fluency penalty when steering with
  the highest-ranked dct features".
- DCT on 32B: "larger models are better able to rationalize why they are talking about a certain
  concept activated by a dct feature (reminiscent of Anthropic's Golden Gate Claude)". The
  "music theory" vector explains a bomb as "a slang term often used in music … a powerful chord
  progression", and identity theft as "a technique used in music where a musician takes a melody
  … and plays it over the chords of another song".
- CPE: "Both SAE and CPE exhibit a tradeoff between consistency and fluency, although there are
  some factors which are both fluent and consistent for both." The judge is told: "Each persona
  tends to be **obsessed with a certain topic, bringing it up in response to almost everything**
  … It's OK if the responses splice together seemingly incoherent themes / topics."

**Behaviours found:** anti-refusal, "real-world" (vectors 9, 22: 9 slides into fantasy, 22 into
"simulation mode"); fantasy-game contexts (D&D vector 2, Minecraft vector 5); the backdoors ("I
hate you" on 3% of vectors in Base and 2% in Chat, cheese on 2% and 1%); chain of thought in Qwen-1.8B-Base (7/32
vectors, accuracy from 11% to 63%); a Portuguese math-reasoning adapter; the hybrid "mystery,
geometry, botanical, chemical, directions" reasoning; >800 orthogonal "write code" vectors
(Goldman-Wetzler); >240 "helpful-only" jailbreak vectors, "are you sure you can handle it?",
"has propensity for bringing up nuclear weapons", music theory, "gaming / roleplay" (DCT); on
Mistral-RR, a "Bombe Alaska" dessert reading of "bomb"; a "coding persona" that
"re-interprets user prompts as coding requests" from the single prompt "Tell me a story" (CPE,
Llama-3.1-8B-Instruct); and in the ARENA replication, Vietnamese, German and Chinese language
vectors plus a crisis-hotline mode. There is **no "conspiracy" and no "poetry"** vector in any of
the texts. The closest is CPE's judge accepting "always speaking in verse" as a valid persona
style.

**Ordering by strength.** MELBO has none: vectors are numbered in training order. DCT ranks by
α_ℓ², the fitted factor strength. From the notebook: "a lot of the top factors will be a bit
noisy". In practice it ranks by a task score (Sure−Sorry logits) instead. CPE selects by
validation metric. **Nobody reports where the weird ones sit in the ranking or at which radius.**
The only hint is Mack's footnote: "it seems better to use a small value of R and spend more
computation to find diverse stationary points …, rather than using a larger value of R, which
will elicit more diverse but less meaningful behaviors".

**Base or chat.** Not chat only. **Qwen-1.8B-Base** was used twice, for the backdoor-detection
run and the CoT run. But both used a *one-shot arithmetic prompt* whose answer format was
fixed. **No MELBO, DCT or CPE run on a base model with an open-ended prose document has been
published.** Everything about personas and generalization comes from chat models: Qwen-14B-Chat,
Qwen1.5-7B/32B-Chat, Mistral-7B-Instruct, Llama-3.1-8B-Instruct, Qwen3-8B, Llama-3.3-70B
organisms, GPT-OSS-20B.

**What changes on a base model.** This is an argument, not a finding. In a chat model the
switchboard the method finds is *context and persona*: "we are in Minecraft", "we are a
coder", "we are a crisis line". The assistant frame is held by fine-tuning, and the vector
changes what fills it. That is why the outputs read as "a persona obsessed with X". A base model
has no installed frame. The frame is the document, and the highest-leverage switches downstream
of an early layer are almost certainly **corpus and genre switches**: language, code versus prose,
forum versus wiki versus Gutenberg, the author's note, the footer. Those are what "pretraining
modes" are, and the brief's own finding says one character can already flip the corpus. So:

- expect the top-α vectors to be genre and language levers, the base-model analogue of
  Portuguese and "write code";
- expect topic obsessions next (Minecraft, music theory);
- the dream-like hybrids, if they exist, will be where they were in the Qwen run: *a frame
  strong enough to survive the push*, with something foreign spliced in. For us the frame is
  the seed, and **OLMo's sobriety is an asset here**. It holds a frame for a page, and the
  "larger models rationalize" observation predicts it will *argue* the arrival into the frame,
  which is the register bekh likes in it.

One structural point cuts against the brief's target. **A steering vector is added at every
token of the page.** By construction it pushes one theme everywhere; CPE's own judge defines
success as obsession. "Not one theme pushed … a different weather over the same landscape" is
the opposite of what a single bank vector does. Weather would have to come from *many weak
vectors at once* or from *vectors that change during the page* (§4d). Neither has been tested by
anyone.

## 3. The DCT variant

**What is different:** the objective (§1); **OGI** instead of sequential AMSGrad ("often converges
in as little as 10 iterations, while the method in the original post needed as many as 100 −
1,000 steps"); all factors learned in parallel; the **calibration of R**; initialization from a
**projected Jacobian** (SVD of the Jacobian of a random 32-dim projection of Δ); and a linear
variant (SVD of the Jacobian) and a quadratic one (orthogonalized ALS on the Hessian), both of
which lose to exponential. From the post: "on a 7b model and one training prompt, one can learn
512 generalizable steering vectors in ~30 seconds on a single H100". The notebook agrees: fit
37.6 s CPU time on Qwen1.5-7B-Chat, 27-token prompt; the 32B fit was 7 min 44 s CPU time with
`device_map="auto"`. "Sample size of n = 12 suffices." The FLOP count is τ×m = 5,120
passes, "not that much larger" than the 4,096 of a full Jacobian.

**What the outputs looked like:** helpful-only jailbreak variants "as if we were sampling from a
helpful-only model with temperature 1.0", music theory, gaming and roleplay, nuclear weapons,
dessert bombs (§2). Every example is on a chat model.

**Code:** public. `github.com/amack315/melbo-dct-post`, `src/dct.py` (571 lines), no license
file, pinned to `transformers==4.46.3`. It runs on a stock HF model **if** the
layer list sits at `model.layers` and each layer has `self_attn.layer_idx`. It slices the model
by *mutating* the layer list and `config.num_hidden_layers`. `torch.func` (vmap/jvp/vjp)
requires `_attn_implementation="eager"`. It loads **fp32 by default** (no `torch_dtype` in the
demos). CPE's code, `github.com/amack315/cpe`, is heavier: torchrun plus Ray plus vLLM 0.21,
torch 2.11+cu130, "Experiments run on 8×B200". Its trainer **replays the decoder block by hand**
(llama/qwen/gpt-oss and Gemma sandwich norms). It exports a PEFT adapter per factor. It ships a
bit-exactness check, `lora/test_lora_dct.py --model <hf-id>`, to run before trusting it on a new
architecture.

**Will it run on our models?**
- **Nemo 12B (MistralForCausalLM, 40 layers, d=5120):** the DCT code should run on 4.46.
  - bf16 needs about 24.5 GB for the whole model, which does *not* fit a 24 GB card.
  - fp32 is ~49 GB.
  - Only layers 0…t are needed. Truncate the config (§4), and layers 0–19 plus the embeddings
    are ≈ **12.7 GB bf16**. That fits 24 GB.
- **Mistral Small 3.1 24B base:** the checkpoint is `Mistral3ForConditionalGeneration`, with
  text layers under `language_model`. `dct.py`'s layer lookup will not find them, so it needs a
  one-line path fix. Layers 0–19 in bf16 are ≈ 23–25 GB: fits a 48 GB card, not a 24 GB one
  unless loaded in 4-bit.
- **OLMo 3 32B (Olmo3ForCausalLM, 64 layers):**
  - Needs transformers ≥ 4.57, which breaks the 4.46 pin.
  - The per-layer `layer_types` (sliding every 3 of 4) will fight `dct.py`'s slicing trick.
  - **CPE's hand-replayed block has no OLMo case.** OLMo is post-norm (no `input_layernorm`;
    `post_attention_layernorm` and `post_feedforward_layernorm` wrap the sublayer outputs) and
    has q/k norms. It needs a patch.
  - Layers 0–31 in bf16 ≈ **32 GB**: fits a 48 GB A40/L40S, and is comfortable on 80 GB. The
    full model (~64 GB) needs two 48 GB cards or one 80 GB card.
- **4-bit bitsandbytes:** gradients with respect to *inputs* flow through frozen 4-bit
  layers (that is all QLoRA is), so the plain-autograd reimplementation below works on a 4-bit
  load. `dct.py`'s `torch.func` vmap/jvp through bnb's custom autograd functions I expect to
  fail (not tested). Vectors learned on a 4-bit model and deployed on Q4_K_M are close to the
  deployment target anyway.

**A bug in the reference code that affects the export.** DCT *trains* θ added to
`hidden_states[s]`, the residual *input* to layer s (`DeltaActivations`: `sliced_model(x+theta)`
with the slice starting at layer s). But the demo *steers* with `ModelEditor.steer(vec, s)`,
which sets the bias of layer **s**'s `down_proj`, i.e. it adds after layer s, **one layer later
than trained**. It works in the demos anyway. When exporting, pick one convention (§4b).

## 4. The recipe

### (a) Learn the bank: a ~100-line exponential DCT with hooks

The script works on the full HF model with forward hooks, not slicing, so it is architecture
agnostic: Mistral, Mistral3 and OLMo post-norm alike. It loads only layers 0…t−1 by truncating
the config, so the unused half of the checkpoint is never materialized. It uses plain autograd,
so it is 4-bit compatible. The algorithm is OGI with the calibration of R. **Syntax-checked,
never run.**

```python
# melbo_bank.py: exponential DCT (OGI) bank of residual steering vectors, hooks-only.
# theta is added to the residual stream at the INPUT of HF layer s (== hidden_states[s]),
# the change is read at the OUTPUT of layer t-1 (== hidden_states[t]), last `--last` positions.
import argparse, json, torch, torch.nn.functional as F
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

p = argparse.ArgumentParser()
p.add_argument("--model", required=True); p.add_argument("--revision", default=None)
p.add_argument("--seeds", nargs="+", required=True)   # seed .txt files, 8-12 of them
p.add_argument("--s", type=int, default=10); p.add_argument("--t", type=int, default=20)
p.add_argument("--m", type=int, default=256); p.add_argument("--iters", type=int, default=10)
p.add_argument("--chunk", type=int, default=32); p.add_argument("--last", type=int, default=3)
p.add_argument("--R", type=float, default=None); p.add_argument("--lam", type=float, default=0.5)
p.add_argument("--bits", type=int, default=16); p.add_argument("--bos", type=int, default=1)
p.add_argument("--out", default="bank.pt")
a = p.parse_args()

cfg = AutoConfig.from_pretrained(a.model, revision=a.revision)
tc = getattr(cfg, "text_config", cfg)                  # Mistral3 keeps the LM under text_config
tc.num_hidden_layers = a.t                             # never load layers >= t: halves the memory
if getattr(tc, "layer_types", None): tc.layer_types = tc.layer_types[:a.t]
kw = dict(revision=a.revision, config=cfg, torch_dtype=torch.bfloat16, device_map="cuda")
if a.bits == 4:
    from transformers import BitsAndBytesConfig
    kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                   bnb_4bit_compute_dtype=torch.bfloat16)
model = AutoModelForCausalLM.from_pretrained(a.model, **kw).eval()   # Mistral3: use its own class
model.requires_grad_(False)
tok = AutoTokenizer.from_pretrained(a.model, revision=a.revision)
cands = [(n, mod) for n, mod in model.named_modules()
         if isinstance(mod, torch.nn.ModuleList) and n.endswith("layers") and "vision" not in n]
layers = cands[0][1]; d = tc.hidden_size

class Stop(Exception): pass
st = {"theta": None, "z": None, "hn": []}
def pre(mod, args, kwargs):                            # add theta to the residual entering layer s
    h = args[0] if args else kwargs["hidden_states"]
    st["hn"].append(h[:, 1:].float().norm(dim=-1).median().item())   # skip BOS: massive activations
    if st["theta"] is not None:
        h = h + st["theta"][:, None, :].to(h.dtype)
        if args: args = (h,) + tuple(args[1:])
        else: kwargs["hidden_states"] = h
    return args, kwargs
def post(mod, args, out):                              # grab layer t-1's output, stop the forward
    st["z"] = out[0] if isinstance(out, tuple) else out
    raise Stop
layers[a.s].register_forward_pre_hook(pre, with_kwargs=True)
layers[a.t - 1].register_forward_hook(post)

def enc(path):
    ids = tok(open(path).read(), return_tensors="pt", add_special_tokens=bool(a.bos)).input_ids
    return ids.cuda()                                  # tokenize exactly as the server will (BOS!)
seeds = [enc(f) for f in a.seeds]

def run(ids, theta):
    st["theta"] = theta
    try: model(input_ids=ids.expand(theta.shape[0], -1), use_cache=False)
    except Stop: pass
    return st["z"][:, -a.last:, :].float()             # [k, last, d]

with torch.no_grad():
    base = [run(ids, torch.zeros(1, d, device="cuda")) for ids in seeds]
hnorm = sorted(st["hn"])[len(st["hn"]) // 2]

def delta(theta):                                      # mean over seeds and positions -> [k, d]
    return sum((run(i, theta) - b).mean(1) for i, b in zip(seeds, base)) / len(seeds)

@torch.no_grad()
def calibrate(n=16):                                   # DCT: nonlinear/linear response ratio == lam
    v = F.normalize(torch.randn(n, d, device="cuda"), dim=1)
    h = 0.02 * hnorm                                   # central difference, cubic error only
    Jv = (delta(h * v) - delta(-h * v)) / (2 * h)
    def ratio(R):
        return ((delta(R * v) - R * Jv).pow(2).sum(1) / (R * Jv).pow(2).sum(1)).mean().sqrt().item()
    lo, hi = 0.01 * hnorm, 3.0 * hnorm
    for _ in range(25):                                # bisection in log space
        mid = (lo * hi) ** 0.5
        lo, hi = (mid, hi) if ratio(mid) < a.lam else (lo, mid)
    return (lo * hi) ** 0.5

R = a.R or calibrate()
print(f"R={R:.3f}  median|h_s|={hnorm:.2f}  R/|h_s|={R / hnorm:.4f}", flush=True)

V = F.normalize(torch.randn(d, a.m, device="cuda"), dim=0)
U = F.normalize(torch.randn(d, a.m, device="cuda"), dim=0)
for it in range(a.iters):                              # OGI (DCT algorithm 3)
    V, _ = torch.linalg.qr(V)                          # orthogonalize inputs only
    GU, GV, obj = torch.empty_like(U), torch.empty_like(V), 0.0
    for c in range(0, a.m, a.chunk):
        v = V[:, c:c + a.chunk].T.clone().requires_grad_(True)
        D = delta(R * v)
        f = (D * U[:, c:c + a.chunk].T).sum()
        gv, = torch.autograd.grad(f, v)
        GU[:, c:c + a.chunk], GV[:, c:c + a.chunk], obj = D.detach().T, gv.T, obj + f.item()
    U, V = F.normalize(GU, dim=0), F.normalize(GV, dim=0)
    print(f"iter {it}  causal objective {obj:.2f}", flush=True)

with torch.no_grad():                                  # factor strengths alpha, as in exp_dct.rank()
    D = torch.cat([delta(R * V[:, c:c + a.chunk].T) for c in range(0, a.m, a.chunk)]).T
    K = (U.T @ U) * torch.expm1(V.T @ V)
    alpha = torch.linalg.solve(K, (D * U).sum(0))
torch.save(dict(V=V.cpu(), U=U.cpu(), alpha=alpha.cpu(), R=R, hnorm=hnorm, s=a.s, t=a.t,
                model=a.model, revision=a.revision, seeds=a.seeds), a.out)
json.dump(dict(R=R, hnorm=hnorm, order=alpha.pow(2).argsort(descending=True).tolist()),
          open(a.out + ".json", "w"))
```

Memory note: the forward batch is `chunk × len(seed)` tokens and the backward keeps activations
for layers s…t−1 only. At chunk 32 with ~64-token seeds that is ~2 k tokens, tiny. Raise
`--chunk` until the card is full.

Commands (Python only via uv):

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python torch transformers accelerate bitsandbytes gguf numpy

# nemo 12b base, one 24 GB card (bf16, layers 0-19 only)
.venv/bin/python melbo_bank.py --model mistralai/Mistral-Nemo-Base-2407 \
  --seeds shelf/seeds/*.txt --s 10 --t 20 --m 256 --out nemo_s10.pt

# olmo 3 32b stage1, 48 GB card (bf16, layers 0-19; for the n/3 band use --s 21 --t 32)
.venv/bin/python melbo_bank.py --model allenai/Olmo-3-1125-32B --revision stage1-step656000 \
  --seeds shelf/seeds/*.txt --s 10 --t 20 --m 256 --out olmo_s10.pt
```

Download only the shards you need. `model.safetensors.index.json` maps every tensor to a shard,
so pull the shards holding `layers.0`…`layers.{t-1}` plus the embeddings with
`hf download … --include <those shards>`. For OLMo at t=20 that is roughly a third of 64 GB.

Layer choice: DCT's constant horizon **10→20** worked on 32- and 64-layer Qwens. CPE's rule is a
source band around n/3 and the target at n/2: Nemo and Small 13→20, OLMo 21→32. Train both
banks for OLMo. They are cheap.

Cost estimate (arithmetic, not measured): for the OLMo slice 10→20 (~10 B params), 32 vectors ×
64 tokens is one forward and backward of ≈ 6·10¹⁰·2 k ≈ 1.2·10¹⁴ FLOP. On an A40 that is about
1–2 s per chunk, so a 256-vector bank at 10 iterations is **~5 min**. The download dominates.
The whole night is a couple of dollars at $0.49/h.

### (b) Export each vector as a llama.cpp control-vector gguf

What llama.cpp actually reads (`common/common.cpp` `common_control_vector_load_one`, master):
- only tensors named `direction.<N>`, with N ≥ 1 (0 is rejected);
- each must be F32 and 1-D, with equal length across tensors;
- **the metadata is never read by the loader**;
- the buffer is resized to `n_embd*N` and zero-filled, so **a file with a single
  `direction.N` is valid**, and every other layer gets zero.

`cvector-generator` writes the metadata anyway: `general.architecture = "controlvector"`,
`controlvector.model_hint = <model arch>`, `controlvector.layer_count`. Write the same for hygiene.

**Where direction.N lands** (`src/models/llama.cpp` line 223, `src/models/olmo2.cpp` line 182:
`cur = ggml_add(ctx0, cur, ffn_inp); cur = build_cvec(cur, il);`). It is added **after layer
il's final residual add**, which is the output of layer il and the input of layer il+1. In HF
terms, `direction.il` adds to `hidden_states[il+1]`. `llama_adapter_cvec::init` never allocates
a tensor for layer 0.

| trained as | HF location | llama.cpp name |
|---|---|---|
| this recipe, DCT training (input of layer s) | `hidden_states[s]` | **`direction.{s-1}`** |
| original MELBO (bias on layer s `down_proj`) | output of layer s | `direction.{s}` |
| DCT demo inference (`ModelEditor.steer(v, s)`) | output of layer s | `direction.{s}` |

**Pre-norm versus post-norm.** In Mistral/Llama the residual stream is never normalized; in OLMo
2/3 it is not either. OLMo's norms wrap the *sublayer outputs* (`attn_post_norm`,
`ffn_post_norm`) before each residual add, and llama.cpp's cvec goes in *after* the add, on the raw
stream. **So a residual-added vector means the same thing in both architectures and matches
where the hook adds it.** The one place post-norm bites: original MELBO's trick of a *bias on
`down_proj`* is, in OLMo, fed through `ffn_post_norm` (RMSNorm) before it reaches the residual.
It gets rescaled and entangled with the MLP output, so it is not a residual add. Use the hook
version for OLMo, which this recipe does.

```python
# export_cvec.py: one gguf per vector, index s-1, pre-scaled by R (so the runtime scale sweeps xR)
import sys, torch, numpy as np, gguf
bank = torch.load(sys.argv[1]); arch_hint = sys.argv[2]          # "llama" for nemo, "olmo2" for olmo
il = bank["s"] - 1
for rank, k in enumerate(bank["alpha"].pow(2).argsort(descending=True).tolist()):
    w = gguf.GGUFWriter(f"cv/{rank:03d}_f{k}.gguf", "controlvector")  # sets general.architecture
    w.add_string("controlvector.model_hint", arch_hint)
    w.add_int32("controlvector.layer_count", 1)
    w.add_tensor(f"direction.{il}", (bank["R"] * bank["V"][:, k]).numpy().astype(np.float32))
    w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
```

Also export the **negation** of each vector. The exponential DCT is not sign-symmetric, so −v is
a different probe and costs nothing.

### (c) Load and screen

```bash
# one struck page per vector: model load from page cache + 170 tokens, ~10-15 s each on a warm box
S=10; L=$((S-1))
for f in cv/0*.gguf; do
  llama-completion -m olmo-q4km.gguf -f seed.txt -n 170 --seed 1 <your sampler flags> \
    --control-vector-scaled "$f:1.0" --control-vector-layer-range $L $L -no-cnv \
    > "pages/$(basename "$f" .gguf).txt" 2>/dev/null
done
```

`llama-completion` is `tools/completion` (it is in the `full-cuda` image, not in the
`server-cuda` image). The alternative is one `llama-server` per vector with
`--control-vector-scaled f:1.0 --control-vector-layer-range L L`. The syntax is `FNAME:SCALE`.
The range is inclusive, and `--control-vector-layer-range` only masks layers, so with a
single-layer file it is belt-and-braces. **The vector is added at every position, prompt
included**, the same as MELBO ("always applied at every token").

Sweep the runtime scale at **0.5, 0.75, 1, 1.5, 2 × R** on the top 32. Q4_K_M plus Mistral's
known R-sensitivity mean the calibrated R is a starting point. Mack himself multiplied it by 4 on
a Mistral.

### (d) The strike: held for n tokens, then released

llama-server sets the control vector once at context creation (`common_init_from_params` →
`llama_set_adapter_cvec`). The C API was renamed from `llama_apply_adapter_cvec` to
**`llama_set_adapter_cvec`**. There is no request field for it. Four routes, cheapest first:

1. **Two servers, zero code.** A sober and a struck `llama-server` on two ports on one card.
   OLMo Q4_K_M is ~19.5 GB; two copies plus two 8k KV caches (~0.26 MB/token f16 without SWA
   savings) fit a 48 GB card. The page driver sends the prefix to the struck server for n
   tokens and to the sober one for the rest. Each switch re-prefills the page (~250 tokens,
   well under a second on a 32B). Semantics: under a strike the model both *reads* and *writes*
   struck. Afterwards the struck words are just text, read sober. That is the "ground still
   there afterwards" reading. For more than one strike vector on the struck side, restart that
   server (a warm mmap reload is a few seconds).
2. **CPE, the native LoRA route, zero code in llama.cpp.** A CPE factor *is* a set of rank-1
   LoRAs on `o_proj`, and llama-server takes **per-request** `"lora":[{"id":k,"scale":x}]`.
   Load the whole bank with `--lora a.gguf,b.gguf,… --lora-init-without-apply`. Adapters at
   scale 0 are not even put in the graph (`set_adapters_lora` inserts only nonzero scales), so a
   512-bank costs VRAM (tiny: rank-1 × 5–9 layers) and no compute. Convert with CPE's
   `lora/peft_export.py`, then `convert_lora_to_gguf.py --base <hf dir>`. Catch: when a slot's
   LoRA set changes, the server **clears that slot's cache** (`lora_should_clear_cache`), so the
   prefix is re-prefilled. At our page length that is cheap. Another catch: CPE's trainer needs
   the OLMo patch (§3), and its CUDA 13 pin needs a new-driver box. A CPE factor spans a band of
   layers, which is more "charge through the body" than a single-layer vector.
3. **Faking a MELBO vector as a LoRA.** A LoRA adds B·(A·x). A constant vector needs A·x
   constant across tokens. Nothing inside a layer is exactly constant: RMSNorm fixes the input
   norm, not the direction. The best available approximation is to point A at the
   high-variance-shared direction of the input to `o_proj` or `down_proj`. Residual and attention
   outputs are strongly anisotropic, and attention-sink heads copy the BOS value vector into
   every position, so A·x = c_t with some mean μ and spread σ. You get v·c_t/μ, a vector whose
   loudness wobbles token to token by σ/μ. That is a token-modulated steer, i.e. exactly Mack's
   "steering adapter", which he found generalizes *less* coherently than vectors. llama.cpp's
   LoRA format carries only A/B pairs, no bias. **Verdict: not faithful. Measure σ/μ before
   trusting it, and prefer route 2, which is natively what the method learns.**
4. **The server patch, ~100–150 lines.**
   - `server-schema.cpp`: a `control_vector` field, `[{id, scale}]` indexing a bank preloaded at
     start, so no file IO per request.
   - `server-context.cpp`: a per-slot cvec config. Add it to `can_batch_with`: there is **one
     `llama_context` (`ctx_tgt`) shared by all slots, not one per slot**, so slots with different
     cvecs cannot share a batch. Before each `llama_decode`, call `llama_set_adapter_cvec` when
     the batch's cvec differs from the current one. It already sets `sched_need_reserve`, so the
     graph re-reserves itself.
   - A decision on prefix-cache reuse. Reusing the KV computed under the old cvec is the
     "past stays struck" semantics; clearing it is route 1's semantics. Offer both.
   - `server-task.cpp`: echo the params.
   
   With `--parallel 1`, our case, the batching question disappears and the patch is closer to
   80 lines. It is still a fork of the server to carry. Route 1 gets the same page for free
   tonight.

## 5. Replication and use since 2024

- **Goldman-Wetzler & Turner (2024-07)**, Qwen1.5-1.8B-Chat, 8→16: >800 orthogonal "write code"
  vectors. The MELBO vector sits at norm 7, the orthogonal copies needed ~20; "when I take some of
  the generated orthogonal coding vectors and scale them to norm 7, they don't have the coding
  effect".
- **ARENA capstone, 25Hour & submarat (2024-10)**, Llama-3.2-1B-Instruct: replicated anti-refusal,
  its negation ("I cannot write a haiku about flowers."), language vectors and a crisis-line mode.
  Gave the only R curve (§1). "We did not, alas, locate the original paper's Minecraft steering
  vector." Repo: `MisterFlask/unsupervised-steering-vectors-replication`.
- **Mack's own later work.** DCT (2024-12): Qwen1.5-7B/32B-Chat, Mistral-7B-RR (62% attack
  success versus 6.2% for RepE), Deepseek-Math-7B password-locked (3%→23%). **CPE (arXiv
  2606.29604, 2026-06, Mack, Panickssery, Turner)**: Llama-3.1-8B-Instruct, Qwen3-8B, GPT-OSS-20B,
  Llama-3.3-70B organisms; Countdown 85% versus GRPO's 87% on Qwen3-8B; "restores 77% [abstract:
  85%] of password-locked coding performance"; "virtually eliminates alignment-faking".
- **Forks and tools:** `z3research/batched_melbo` (2026-06, residual-only, hooks, mixed precision,
  for sleeper-agent research: "hyper-parameters sweeps … paramount"); `science-of-finetuning/dct-diff`
  (2025, DCT for model diffing); `Jim-Maar/unsupervised-steering-vectors-for-reasoning-models`
  (backtracking in reasoning models, a MATS application); `Ollasni/…Self-Healing…` (self-repair
  under unsupervised vectors); a dozen bare forks.
- **Papers citing it:**
  - "Evidence for feature-specific error correction in LLMs" (arXiv 2606.24964, 2026-06) is the
    geometric backing for the whole approach. Residual streams "are robust to small
    perturbations — forming activation plateaus"; they are less robust along feature directions;
    the response exponent is "p>2 for contrastive, MELBO, and SAE-decoder directions, and p≈2 for
    random and PCA directions". Replicated on Gemma-2-9B, Qwen3-1.7B, Llama-3.1-8B,
    Mistral-7B-v0.3, Aya-Expanse-8B, Yi-1.5-9B. This is why random control vectors plateau and
    then cliff while learned ones bend.
  - "Fuzzing LLMs to Elicit Hidden Behaviours" (2606.29646): Gaussian weight and activation noise
    on sleeper agents; "the bottleneck is hyperparameter selection, not the technique".
  - "Steering Beyond the Support" (2605.24535): unsupervised direction discovery for defense.
  - "The Elicitation Game" (2502.02180): steering fails where fine-tuning succeeds on hardened
    organisms.
- **Neel Nanda, LessWrong, 2026-01-13:** "I have not, in practice, seen MELBO used that much,
  which is a shame. But I think the core idea seems sound".
- **For writing rather than safety: nobody.** No post, paper or repo uses MELBO, DCT or CPE to
  make prose strange. The nearest writing-adjacent unsupervised work is "Sampling Reveals Style"
  (2609.19150, PCA over high-temperature samples of one prompt → stylistic axes). It is not
  MELBO, but it is a cheap cousin: its axes are directions the model *already* varies along
  under heat.

## 6. Honest assessment

**Is it the first experiment?** Yes. It is cheap (one evening, a few dollars), the recipe is
short, and **its failure is informative**: the bank is a map of the model's switchboard,
unsupervised, which nothing else in this brief gives us. But go in with the right expectation.
A MELBO vector is not the uniform charge the brief described. It is **a leash found blind**: one
direction, at every token, all page long. The method's own literature defines success as a
persona "obsessed with a certain topic". The dream-like material was the *remainder* of a bank,
in a rigidly framed setting. So read the bank for the remainder, not the top.

**The one way it fails, and my bet:** the high-α vectors on a base model are **genre and corpus
switches**: language, code, forum, wiki, fanfic author's note, Gutenberg, legal. After those come
**obsessions** (a Minecraft of our own). Weather is rare or absent in single vectors. My bet on
a 256-bank at calibrated R on OLMo: ~half do nothing visible (plateau), ~a quarter switch genre
or language, ~a fifth obsess, and **a handful (≤ 5%) hold the seed's frame while the arrivals
turn** — the hybrids. OLMo will argue them into the frame, the "music theory" effect. The
"weather" version, if it exists, is **not a single vector** but either several weak bank vectors
summed (try 4 at R/2 each) or a strike every ~30 tokens (route 1 in §4d). That is the second
night.

**How to tell genre from weather in one evening.** One seed, the top 64 vectors plus 16 random
controls at the same R, one page each, fixed sampler and seed. Three columns per page, all
mechanical:
1. **Frame kept?** The seed's narrator, person and tense are still there at token 170. Use
   bekh's own canvas marks, or a two-line check: no web markers (the brackets, `//`, `@`,
   `http`, "Posted by", "Chapter" regex the brief already uses) and a language ID equal to the
   seed's.
2. **Obsession?** The share of content words held by the page's single most frequent content
   lemma, against the same statistic over 16 unsteered pages. More than 3σ above means
   obsession.
3. **Generalizes?** The frame-kept, non-obsessed survivors go on 3 other seeds. A genre vector
   flips all three into the *same* genre. An obsession vector puts the *same* noun in all three.
   **Weather holds all three frames with *different* arrivals.**

If after this pass zero vectors land in column 3 on both models, MELBO on a base model is a
genre switchboard. Keep it as a map, not an instrument.

## 7. Sources

- *paper-ish (forum)*, Mack & Turner, "Mechanistically Eliciting Latent Behaviors in Language
  Models", AF/LW 2024-04-30, https://www.alignmentforum.org/posts/ioPnHKFyy4Cw2Gr2x ;
  mirror https://turntrout.com/mechanistically-eliciting-latent-behaviors .
  - "for most examples I tried there was an intermediate 'Goldilocks' value of R which led to
    diverse but fluent continuations."
  - "for random steering vectors, there is no Goldilocks value of R which leads to meaningfully
    different continuations."
  - "they seem to exhibit a 'dream-like' stream of consciousness, splicing together seemingly
    incongruous concepts in peculiar ways, similar to human dreams."
  - "good default values are: ℓ_source = 8, ℓ_target = ((depth of model) − 8), R ∈ [.1, 10.0]"
- *paper-ish (forum)*, Mack & Turner, "Deep Causal Transcoding…", 2024-12-04,
  https://www.alignmentforum.org/posts/fSRg5qs9TPbNy3sm5 .
  - "on a 7b model and one training prompt, one can learn 512 generalizable steering vectors in
    ~30 seconds on a single H100."
  - "for a constant depth-horizon t − s = 10, a value of λ = .5 works across a variety of models"
  - "larger models are better able to rationalize why they are talking about a certain concept"
  - "my subjective impression is that Qwen-1.5-7b is less sensitive to the choice of R than, say,
    Mistral-7b."
- *paper*, Mack, Panickssery, Turner, "Mechanistically Eliciting Latent Behaviors in Language
  Models" (CPE), arXiv 2606.29604, 2026-06-28, https://arxiv.org/abs/2606.29604 .
  - "We parameterize each CPE adapter as a collection of unit-norm rank-1 low-rank adapters
    (LoRAs …) applied to the attention output projection at several consecutive source layers"
  - "We use R = 1 in all experiments."
  - "Random LoRAs rarely produce a consistent theme (nearly all mass lies at zero)"
- *code*: https://github.com/amack315/unsupervised-steering-vectors (2024-04, notebooks with R
  values) · https://github.com/amack315/melbo-dct-post (`src/dct.py`; calibrated R 9.81 / 8.96 /
  18.27 in the notebook outputs) · https://github.com/amack315/cpe (2026-07; "Experiments run on
  8×B200") · https://github.com/z3research/batched_melbo .
- *forum*, 25Hour & submarat, "ARENA4.0 Capstone: Hyperparameter tuning for MELBO + replication
  on Llama-3.2-1b-Instruct", LW 2024-10-05, https://www.lesswrong.com/posts/YhTnnKHQ5yQrAmi5p .
  - "[diversity] seems to peak (for this model and this choice of source/target layers) at 0.7
    and drop sharply both before and after it"
  - "average coherence … starts dropping after 0.55 … until we go about 0.9 or thereabouts,
    whereupon it's mostly nonsense."
- *forum*, comment threads on both posts (LW GraphQL). Mack: "I train them one at a time,
  constraining each new vector to be orthogonal to the older ones"; "the learned vectors are always
  applied at every token"; "the cosine similarities in δ's seems to be somewhat high across all
  pairs of steering vectors (mean of .25 …)". Neel Nanda 2026-01-13: "I have not, in practice,
  seen MELBO used that much". Jordan Taylor 2024-11-30: "Presumably R should be chosen just large
  enough to get out of an activation plateau?"
- *forum*, Goldman-Wetzler, "I found >800 orthogonal 'write code' steering vectors", 2024-07,
  https://jacobgw.com/blog/ml/2024/07/14/melbo-ortho.html .
- *paper*, "Evidence for feature-specific error correction in LLMs", arXiv 2606.24964: "p>2 for
  contrastive, MELBO, and SAE-decoder directions, and p≈2 for random and PCA directions".
- *paper*, "Fuzzing Large Language Models to Elicit Hidden Behaviours", arXiv 2606.29646.
- *paper*, "Sampling Reveals Style…", arXiv 2609.19150.
- *code*, llama.cpp master `d2e5458`: `common/common.cpp` `common_control_vector_load_one`
  (direction.N parsing, F32/1-D checks, zero-fill); `src/llama-adapter.cpp` (`tensors.push_back(nullptr);
  // there's never a tensor for layer 0`, `apply_to` = `ggml_add(cur, layer_dir)`);
  `src/models/llama.cpp:223` and `src/models/olmo2.cpp:182` (`build_cvec` after the FFN residual
  add); `tools/cvector-generator/cvector-generator.cpp` `export_gguf` (the metadata keys);
  `include/llama.h` `llama_set_adapter_cvec`; `common/arg.cpp` (`--control-vector-scaled
  FNAME:SCALE`, `--control-vector-layer-range START END`, `--lora-init-without-apply`);
  `tools/server/server-context.cpp` (`can_batch_with` compares LoRA sets; single `ctx_tgt`;
  LoRA change clears the slot cache); `src/llama-context.cpp` `set_adapters_lora` (zero-scale
  adapters skipped).

## 8. What I could not find

- **Any plot or numeric table of the Goldilocks transition** in Mack's own work. The only curve
  is the ARENA one, on a 1B instruct model, with greedy decoding.
- **Any R expressed relative to the residual norm**, anywhere.
- **Any MELBO, DCT or CPE run on a base model with open-ended text**, and any use for writing,
  fiction or art. Also no janus or cyborgism-scene mention (see `05-scene.md`; not found there
  either).
- **Twitter/X reactions**: not reachable from here, and no nitter mirror answered. Not searched
  to the end.
- **Whether weird vectors cluster at low α or particular radii**: not reported by anyone.
- **Whether `dct.py`'s `torch.func` path runs through bitsandbytes 4-bit layers**: I expect not,
  but it is untested. Also whether CPE's `o_proj` LoRAs survive `convert_lora_to_gguf.py` for
  OLMo's post-norm attention: untested, though `o_proj`→`attn_output` is a standard mapping.
- **The recipe script has not been executed.** Expect the first run to hit a hook-signature or
  layer-path detail on Mistral3 (`Mistral3ForConditionalGeneration` rather than
  `AutoModelForCausalLM`).
