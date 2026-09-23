# mescalito, slice 1 + 6: structured weight noise, and quantization as a knob

Researcher 1 of 6. Brief items 1 (weight noise, structured) and 6 (quantization as a knob), plus
the mid-MLP hypothesis. Papers and scene posts, plus a small bench run on this Mac (Qwen2.5-1.5B
base, Q4_K_M, llama.cpp), because nobody has published the prose comparison we need and the
tools to run it turned out to be about 150 lines.

## The short version, argued

1. **Uniform weight noise doesn't make a model strange. It makes it *average*.** Isotropic
   noise, quant rounding, block-gain jitter and random LoRAs all wipe out the weak, rare,
   fine-grained associations first. What survives is the high-frequency backbone of the
   model. You get the generic word ("the", "of"), the repeated phrase, the loop,
   confabulated specifics told in a confident register. The scene calls it
   **"drunk"**. The evidence points the other way from the brief's worry: the model doesn't
   drift toward a *slant*, it drifts toward the *prior*. LASER shows the mechanism at
   component level. The IQ1 cactus A/B on reddit shows it in prose: IQ1 turns five metaphors
   into one metaphor five times and then loops, while Q8 writes "a bottled rain". That's the
   opposite of lightning.
2. **Where you put the noise doesn't change what it does to the next token.** On the
   bench, every perturbation I ran landed on *one curve*: attention, the middle third's
   down_proj, the late up/gate band, a random LoRA, a spectral-band LoRA, Q3_K_S, Q2_K. At
   matched mean KLD they flip the same fraction of top tokens (±2 pts) with the same heavy
   tail (q99 ≈ 6–8× mean). The tensor family only changes *how much dose* gets you there.
   Per-token statistics can't see the difference between slur and lightning. If the
   difference exists, it lives at page level (does the whole page tilt one way, or does each
   token wobble on its own?), and only reading will find it.
3. **Every family has a knee, and past it there's no slant, just a cliff.** Across one
   doubling of dose, ppl goes from ×1.3 to ×100 or more (bench table below). The one
   published per-component sweep says the same thing: *"the sharp σ = 1.0 → σ = 2.0 transition
   is more consistent with a regime change in the model's coherent-generation capacity than
   with a graded loss"*.
4. **The one family of uniform perturbation that the literature says is *not* damage** is
   the **thicket**. Big pretrained models (tested up to 32B) are surrounded, at small
   isotropic σ, by perturbed copies that are *specialists*. Each is better at some things and
   worse at others: *"a distribution over models … diverse specialists whose behavior is
   qualitatively different from the singular pretrained weights."* That's the "different
   weather" picture, and it's real, but it has two catches. It shows up as task-accuracy
   shifts well *below* any visible slur, and nobody has read what a thicket neighbour writes
   as prose. The honest bet: a single frozen isotropic draw at ppl +2–7% is the only
   isotropic dose worth reading. It will read as a *slightly different sober writer*, not a
   drunk one and not a dreamer.
5. **My single bet for "lightning" is not noise at all. It's the *sign* of noise's effect,
   reversed.** If uniform noise drives the model toward the average by drowning its fine
   structure, then **amplify the fine structure**. Take the singular band *just below* the
   top outlier components of the late-middle MLP up/gate matrices (1.5B bench: components
   64–512 in layers 14–24 of 28). Add a fraction of that band back onto itself, uniformly over
   every learned direction in it, adding no new direction. LASER removes that band to make a
   model *more* factual and says it holds *"a different response of the same semantic
   category"*. Going the other way should make the model *less average*: same slot, other
   noun. Bench, n = 2 per arm (anecdote, flagged): **removing** the band gave loops and the
   seed recited back. **Amplifying it by a quarter** (matched KLD 0.043, same curve as
   everything else) gave *"I am a voice in my mother's dreams, a ghostly messenger to my
   brother who is away on a mission, a little bird, a flute, a bird in a cage."* **Then a
   matched-divergence set at n = 5 didn't reproduce it.** The amplified arm was the least loopy
   (distinct-2 0.72 vs base 0.56), but not stranger, and the best single pages came from
   the controls. So the bet stands on mechanism (LASER, plus "remove → average" held on the
   bench), not on the bench's prose. It ships as a runtime LoRA on the existing Q4 gguf, with
   no requant, and the scale can be set **per request**. Mixing several bands or jittered
   copies with random per-page scales gives the "living charge" of item 2 for free. The real
   test is on the 32B, where genre lock isn't the whole story.

## (a) Mechanisms

### Bench numbers first (so the rest can refer to them)

Qwen2.5-1.5B base, Q4_K_M as the reference, KLD over 5,120 tokens of `docs/anthology-weird.md`,
`llama-perplexity --kl-divergence`. "same top" = share of positions where the perturbed model's
top token is the base's. Tools in `scratchpad/mescalito/lab/`: `q4k_gain.py` (block-gain noise in
place on a Q4_K/Q6_K gguf), `noise_lora.py` (writes an untrained LoRA gguf: gaussian, a singular
band, or singular-gain jitter), `kld.sh` (one line per condition), `pages.sh` (paired pages, same
RNG seed).

| condition (1.5B, 28 layers) | ppl × | mean KLD | q99 KLD | same top |
|---|---|---|---|---|
| **quant** Q6_K (vs the Q4_K_M ref) | 0.98 | 0.024 | 0.18 | 93.1 % |
| **quant** Q3_K_S | 1.17 | 0.184 | 1.12 | 82.3 % |
| **quant** Q2_K | 1.65 | 0.53 | 2.95 | 70.2 % |
| block gain, all linear, σ 0.05 | 1.02 | 0.013 | 0.08 | 95.1 % |
| block gain, all linear, σ 0.1 | 1.07 | 0.054 | 0.36 | 90.0 % |
| block gain, all linear, σ 0.2 | 1.36 | 0.30 | 1.87 | 77.5 % |
| block gain, all linear, σ 0.4 | **696** | 6.6 | 17.0 | 5.9 % |
| block gain, ffn_down L9–18 (mid third), σ 0.4 | 1.05 | 0.054 | 0.34 | 89.8 % |
| block gain, ffn_down L9–18, σ 0.8 | 8.5 | 2.19 | 9.5 | 36.5 % |
| block gain, ffn_up+gate L14–24, σ 0.4 | 1.28 | 0.23 | 1.59 | 81.6 % |
| block gain, ffn_up+gate L14–24, σ 0.8 | **5·10⁵** | 13.2 | 23.2 | 0 % |
| block gain, attn q/k/v/o all layers, σ 0.2 | 1.08 | 0.092 | 0.60 | 86.8 % |
| block gain, attn all layers, σ 0.4 | 3.15 | 1.16 | 5.2 | 58.0 % |
| random gaussian LoRA r16, FFN L9–24, ×2 | 1.08 | 0.070 | 0.41 | 89.1 % |
| random gaussian LoRA r16, FFN L9–24, ×4 | 1.52 | 0.43 | 2.50 | 72.9 % |
| random gaussian LoRA r16, FFN L9–24, ×8 | **28 912** | 10.3 | 21.0 | 0.7 % |
| singular-gain jitter, top 0–64, up/gate L14–24, τ 0.5 | 1.26 | 0.24 | 1.49 | 81.1 % |
| same, ×2 | **139** | 5.0 | 13.2 | 14.8 % |
| singular-gain jitter, band 64–512, τ 0.15 | 1.008 | 0.005 | 0.035 | 97.3 % |
| same, ×2 | 1.024 | 0.020 | 0.15 | 93.8 % |
| singular band 64–512 **removed** (LASER-style, ×−1) | 1.73 | 0.54 | 3.98 | 72.5 % |
| singular band 64–512 amplified ×1.25 | 1.05 | 0.043 | 0.33 | 91.1 % |
| singular band 64–512 amplified ×1.5 | 1.27 | 0.24 | 1.91 | 79.9 % |
| singular band 64–512 amplified ×2 | **310** | 5.8 | 15.6 | 10.8 % |

Read the mean-KLD column against the same-top column. At KLD ≈ 0.05: 90.0 / 89.8 / 91.1 / 89.1 %.
At ≈ 0.24: 81.6 / 81.1 / 79.9 / (Q3_K_S at 0.18: 82.3). At ≈ 0.5: 70.2 / 72.5 / 72.9. It's one
curve. The locus changes the dose, not the shape. In hindsight that's close to forced: at a
given mean KLD, how many top tokens flip is set mostly by the *base's* margins, so these
statistics are blind to *where* the noise went by construction. That's the point. Measuring
tokens can't find lightning, and it can only be read. Caveats: a 1.5B, 10 chunks, one seed per
condition, Qwen (pre-norm, not clean). The Mac was shared with other agents' llama runs, and a
few runs died and were re-run.

### A. Isotropic gaussian on all weights (the baseline the brief suspects)

- **Mechanics.** W' = W + σ·std(W)·ε per tensor, full rank. In high dimensions almost all of ε
  is orthogonal to the few directions the next layer actually reads. Most of it does nothing,
  and the part that lands on high-curvature directions (early layers, outlier/super weights,
  attention logits) does all the damage. MELBO's author says it plainly: *"for random steering
  vectors, there is no Goldilocks value of R which leads to meaningfully different
  continuations … random vectors typically lead to uninteresting re-phrasings of the model's
  unsteered continuation, if they even lead to any changes."* CPE: *"random perturbations
  produce only local noise that quickly dissipates."*
- **Reported feel.** Nothing, then re-phrasings, then token-level incoherence. Nobody I found
  has published prose from a sweep. The per-component Llama-3.1-8B sweep describes σ_rel 2.0
  on one late attention layer as *"token-level incoherence: short fragments repeated,
  occasional cross-script characters, no syntactic structure"* (`ouchddenreeoraoraora`), with
  σ 1.0 still *"coherent and on-task."*
- **Dose and cliff.** Llama-3.1-8B-Instruct, per-tensor std-normalized noise on all block
  weights: σ_rel 0.05 → ppl +2 %, 0.10 → +8 %, 0.15 → +24 %, 0.20 → +64 %, and accelerating.
  One component at a time, the cliff (MMLU < 80 %) sits at σ_rel ≈ 1.0 in layers 0–10, 2.0 in
  11–20 and 4.6 in 21–31, with the most fragile tensor `layer_1_mlp` at 0.5. Absolute noise on
  Qwen2.5 0.5B–32B at σ = 0.001–0.005 (all weights, bf16) leaves the models functional and
  "specialised" (thickets, ES). The bench's block-gain runs put the knee between σ 0.2 and 0.4
  on all linear layers.
- **On llama.cpp + Q4.** Not a flag. True additive noise needs float weights: bf16 from HF →
  torch, per tensor → `convert_hf_to_gguf.py` → `llama-quantize … Q4_K_M`. gguf-py can
  dequantize Q4_K but cannot *quantize* it (only Q8_0, Q4_0/1, Q5_0/1, BF16 are implemented in
  `gguf/quants.py`). The shortcut is a Q8_0 gguf written by gguf-py straight from the noised
  floats, which needs a 48 GB card.
- **Cost, 32B.** 65 GB bf16 at 36–50 MB/s ≈ 25–30 min. The noise pass streams one shard at a
  time on CPU, ~10 min. Convert ~15 min, quantize 15–30 min. ~150 GB disk at peak. **~1 h per
  dose after the first download.**
- **Architecture.** The most leveraged tensors are GQA's k/v (8 KV heads serve 40 query
  heads in OLMo 3 32B, so each KV parameter is 5× leveraged; Q4_K_M already gives `attn_v`
  Q6_K in half the layers for this reason). With tied embeddings (Gemma, small Llamas),
  noising `token_embd` also noises the output head. Leave embeddings alone. OLMo 2/3's
  *post*-sublayer RMSNorm (`h + norm(Attn(h))`, `h + norm(MLP(h))`, no input norm, QK-norm)
  renormalises each sublayer's output. Pure *magnitude* errors are erased, and only
  *direction* errors survive, so the blow-ups should be softer than in pre-norm Llama/Mistral.
  That's inferred from the layout, not measured. **Run on** the OLMo 3 32B stage1 checkpoint
  (what we have). For a pre-norm control, Mistral Small 3.1 24B base.
- **Bet: slur.** Below the knee, a sober writer with slightly different habits. Above it,
  loops and salad. No slant in between.

### B. Structured by family / depth (mid-third ffn_down, late up/gate, attention only)

- **Mechanics.** Same as A, restricted by regex and layer range.
- **Reported feel.** Nothing published on prose. On the bench, with block-gain noise: the
  mid-third ffn_down needs twice the dose of "all linear" for the same KLD (σ 0.4 vs 0.2),
  late up/gate breaks explosively (σ 0.8 → ppl ×5·10⁵), and attention sits in between. At
  matched KLD they're indistinguishable token-wise (table).
- **Dose and cliff.** Early layers are 5× more fragile than late (the 8B sweep). The
  middle is robust because it's redundant: *"the model is remarkably robust to dropping middle
  layers"* (Stages of Inference). Robust here means *self-repairing*, so you need more dose to
  show anything, and by then you're close to the knee.
- **On llama.cpp + Q4.** As A, or as B′ (block gain) or C (LoRA) below, both of which avoid
  requantizing.
- **Cost.** As A; B′ and C are minutes.
- **Architecture.** On OLMo 2/3, noise in `attn_output` or `ffn_down` that only changes the
  *overall* size of a sublayer's output is normalised away by the post-norm, so aim at
  q/k/up/gate (inside the sublayer, before its nonlinearity/softmax). QK-norm also bounds
  attention logits, so attention noise on OLMo is more forgiving than on Llama/Mistral. On
  pre-norm bases every tensor's gain passes straight to the residual. **Run on** the OLMo 3
  32B stage1 checkpoint, with Mistral Small 3.1 24B base as the pre-norm, no-QK-norm
  contrast.
- **Bet: slur, maybe with a different accent.** The dose tells you less than which bands you
  spare. Keep layers 0–⅛ and the last ⅛ out of every experiment. The bench and the 8B sweep
  agree those are where it breaks first.

### B′. Q4 block-scale noise (the gguf edit, no requant)

- **Mechanics.** A Q4_K super-block (256 weights, 144 bytes) decodes as `w = d·sc·q − dmin·m`.
  Multiply both fp16 fields `d` and `dmin` by the same factor f = e^(σz), and the whole block
  becomes exactly f·w. It's multiplicative, sign-preserving noise: the learned pattern inside
  the block survives, and only its gain wobbles. The Q6_K tensors in a Q4_K_M
  (`attn_v`/`ffn_down` in ~half the layers, `output`) decode as `d·scale·(q−32)`, so scaling `d`
  alone does the same. `q4k_gain.py` does this in place on a copy through
  `GGUFReader(path, "r+")` (a writable memmap). Byte length and offsets don't change, so
  llama.cpp loads it like the original. Tested on the 1.5B.
- **Reported feel.** Nobody reports *noising* the scales. The nearest scene post, someone
  *training* only the scales of a fixed GGUF, confirms the handle: *"In a fixed GGUF the integer
  codes are frozen, but every quantised block still carries one or two fp16 scales, and the
  decoded weight is linear in them."* He also notes *"prose is where every low-bit variant of
  this model drifts."* Bench pages at σ 0.1 (all linear) stay fluent and turn confabulatory
  (see the pages below).
- **Dose and cliff.** σ 0.05 / 0.1 / 0.2 → ppl ×1.02 / ×1.07 / ×1.36, and σ 0.4 → ×700. The
  log-normal tail is part of why it breaks: at σ 0.8 a few blocks get ×10. A bounded draw
  (uniform in [1−a, 1+a]) would make a gentler knee. Not tested.
- **On llama.cpp + Q4.** File edit, `q4k_gain.py SRC DST --pattern REGEX --layers a-b --sigma S
  --seed N`.
- **Cost, 32B.** Copy 18 GB (1–2 min on NVMe) plus one pass over the fp16 fields of the chosen
  tensors, I/O-bound: **minutes per dose, +18 GB disk per kept variant.** No VRAM change.
- **Architecture.** A pure gain edit is the one most erased by OLMo's post-norm when it hits
  `attn_output`/`ffn_down`, because it partly scales the sublayer output. On OLMo, use it on
  up/gate/q/k. On a pre-norm model (Mistral Small 3.1 24B base), gain noise on `ffn_down`
  reaches the residual directly.
- **Bet: slur.** It's the cheapest dose dial there is, and I'd use it to *calibrate* the
  knee on the 32B in ten minutes, not to hunt lightning.

### C. Random (never-trained) LoRA, low rank vs full rank

- **Mechanics.** ΔW = B·A with A, B gaussian, rank r. At equal Frobenius norm to full-rank
  noise, a rank-r perturbation packs all its energy into r random input→output direction pairs:
  r random steering directions per tensor, *conditional on the input*. EGGROLL (ES at
  hyperscale) argues rank-1 perturbations explore as well as full rank for *optimisation*,
  which says nothing about how they read.
- **Reported feel.** CPE's random LoRAs, matched in norm and placement to its learned adapters: *"Random LoRAs rarely produce a consistent theme (nearly all mass lies at zero),
  confirming that coherent personas do not arise from arbitrary weight perturbations."* The
  sandbagging paper uses rank-8 random LoRAs as a cheap carrier of weight noise
  (they derive an equivalence to direct noise in their appendix E) and reports that noise *removes* the
  higher-level policy first. In noised CoTs the models stop *"mentioning of broader
  implications"* while still answering. Bench: on the same curve as everything else. ×4
  gives ppl ×1.5, ×8 gives ×29 000.
- **Dose and cliff.** On the bench, rel 0.1 per matrix (‖BA‖/‖W‖) × scale: ×2 is the last
  "clean-ish" dose and ×8 is gone.
- **On llama.cpp + Q4.** **This is the one that's a runtime flag.** `noise_lora.py --kind
  gauss` writes a LoRA gguf directly (tensors `blk.N.ffn_up.weight.lora_a/lora_b`,
  `adapter.lora.alpha` = rank so the scale is literal). Load with
  `llama-server --lora a.gguf --lora b.gguf … --lora-init-without-apply`, then **per request**
  `"lora":[{"id":0,"scale":1.7},{"id":3,"scale":-0.9}]` on `/completion`. Load K random
  adapters, draw K scales per page, and every page gets a fresh perturbation from a K-dim family.
  That's the "living charge" of item 2 with zero code. Tested: llama.cpp loads it on a Q4_K_M
  base, `--lora-scaled f.gguf:x` works in `llama-perplexity`/`llama-completion`, and different
  scales give graded KLD.
- **Cost, 32B.** Writing it takes seconds. The FLOPs per touched matrix go up by
  2r(n_in+n_out)/(2·n_in·n_out): r 16 on up/gate is +0.4 %, r 64 is +1.5 %. VRAM: r 64 over
  up+gate of 22 layers ≈ 370 MB in f32. Fits the 24 GB card with Q4.
- **Architecture.** Architecture-agnostic, as long as llama.cpp supports LoRA for the arch
  (it applies adapters generically to named tensors). Same OLMo post-norm caveat as B. **Run
  on** the OLMo 3 32B stage1 Q4 we already serve. It's the control arm, so run it wherever D
  runs.
- **Bet: slur, or nothing.** Random directions *"quickly dissipate"* or break things. Its value
  is as the **control** for D and E, and as proof that per-page stochastic weights on a Q4 cost
  nothing.

### D. The model's own singular band: amplify it, or jitter its gains (my bet)

- **Mechanics.** W = UΣVᵀ. ΔW = U_k·diag(s_k·(e^{τz_k} − 1))·V_kᵀ over a band of components
  [k0, k1). Every learned input→output direction in the band keeps its direction and gets a
  random gain. No new direction is added, and the perturbation stays inside the span the model
  trained. It's rank k1−k0, so it *is* a LoRA: A = V_kᵀ, B = U_k·diag(g). `noise_lora.py --kind
  spectral` computes it from the dequantized Q4 weights. `--kind band` writes the band itself,
  so scale −1 deletes it (LASER) and +c amplifies it.
- **Why this band.** LASER: removing the small-singular ("higher-order") components of *late
  MLP input matrices* improves factual recall. When the model is approximated by those
  components alone, *"these components describe either a different response of the same
  semantic category as the correct answer or generic high-frequency words … when the noisy,
  higher-order components are combined with the low-order components, their conflicting
  responses produce a sort of 'average answer'."* So that band is where *same slot, other
  noun* lives. Random-matrix analysis adds that information lives at *both* ends of the
  spectrum, the bulk is the noise-like part, and *"zeroing out the singular values that
  deviate from RMT raises language-model perplexity far more than removing values from the
  bulk."* The top outliers carry the backbone, and jittering them is what broke the bench
  fastest (top 0–64, τ 0.5, ×2 → ppl ×139).
- **Reported feel.** Nobody has run it for prose. The bench tokens say it's on the same curve.
  τ 0.15 on the 64–512 band is very gentle (ppl ×1.008, 97 % same top). Deleting the band
  costs ppl ×1.7. Doubling it costs ×310.
- **Dose and cliff.** Two dials. **Band amplification** (`--kind band`, scale +c, so the band
  becomes (1+c)× itself): +0.25 gives KLD 0.043 / ppl ×1.05, +0.5 gives KLD 0.24 / ×1.27, +1
  gives ×310 (gone). The window is c ≈ 0.1–0.4. **Gain jitter** (`--kind spectral`) on the same
  band: τ 0.15 × scale 1–3 is gentle (KLD 0.005–0.02). The knee is where the band's *net*
  amplitude passes ~1.5× its trained size. For OLMo 3 32B (up/gate rank 5120) the analogous
  band is roughly components 128–1024 in layers 32–54. That's scaled by rank share, not
  measured, so sweep it.
- **On llama.cpp + Q4.** LoRA gguf, per-request scale. Draw fresh per page with several
  adapters, same as C.
- **Cost, 32B.** One truncated SVD per touched matrix. A full numpy SVD of 5120×27648 is
  ~1 min on CPU, and `torch.svd_lowrank(q=512)` on the card takes seconds. Up+gate over layers
  32–54 is ~46 matrices: minutes on a GPU, under an hour on CPU. Adapter at rank 448 ≈ 60 MB
  per matrix in f32 (≈2.7 GB for 46), f16 halves it, and runtime cost is ~+10 %. On the 24 GB
  card, narrow the band to rank ~128 or write f16.
- **Architecture.** Works best where the MLP input is *not* renormalised away: pre-norm bases
  (Mistral Small 3.1 24B base, Llama 3.1 base) and OLMo alike, since up/gate sit before the
  SwiGLU. It prefers untied, non-softcapped models only because those are the cleanest to
  read. Gemma's logit softcapping would cap the damage *and* the effect at the head.
- **Bet: the best shot at lightning in the uniform family, about 1 in 4.** The two lucky
  pages moved me up, and the n = 5 matched set moved me back. It changes *which* learned
  association wins at a fork, everywhere at once, without adding off-manifold directions. The
  amplify/remove pair is the first thing in this whole slice that behaves *directionally*
  (remove → the average, amplify → away from it) instead of just "more or less broken". The
  risk: LASER's "different response of the same semantic category" is a *wrong fact* in QA,
  and in prose it might only be purple register. The second amplified page's "I am the wind
  that …" list is already sliding toward a loop.

### E. Checkpoint-delta noise (the model's own training noise): the OLMo-only idea

- **Mechanics.** OLMo 3 32B publishes stage1 checkpoints every 1000 steps (`stage1-step645000`
  … `stage1-step656000` on HF, verified). Δ = θ_656k − θ_655k is what one thousand steps of
  pretraining moved. At constant high learning rate, the step-to-step difference is mostly
  oscillation across the *"sharp hillsides"* of the river valley (Wen et al.), i.e. SGD's own
  noise. θ' = θ + α·DARE_p(Δ) (random drop p, rescale 1/(1−p)) is noise shaped exactly like
  training's noise. It needs no fine-tune and no other data, and it installs no position,
  because it's pretraining on pretraining. α ∈ [−1, 1] stays among weights SGD actually
  visited. |α| > 1 goes up the valley walls.
- **Reported feel.** None. DARE itself is documented only on fine-tune deltas: *"DARE can
  effectively remove 90% delta parameters without significantly decreasing performance … in
  some cases the drop rate can even reach 99%."* Nobody has read pretraining-checkpoint deltas
  as prose.
- **Dose and cliff.** Unknown. A 1000-step delta is probably tiny, so expect to need α of
  several units or a wider gap (645k→656k) before anything shows. Going up the walls should
  read *hotter*, not stranger. A learned temperature, not lightning, is my guess.
- **On llama.cpp + Q4.** Truncated SVD of Δ per matrix → LoRA gguf (rank 64–256) → per-request
  scale, including negative. Or apply it in bf16 and requantize (as A).
- **Cost, 32B.** A second 65 GB bf16 download (25–30 min), a diff per tensor, SVD as D.
- **Architecture.** Needs a base with dense published checkpoints: OLMo 2/3, Pythia, LLM360.
  That's a reason to stay on OLMo, not a reason to leave it.
- **Bet: temperature-like, not lightning.** Worth one evening because it's the only uniform
  perturbation with a claim to being "the model's own weather", and it's unexplored.

### F. Quantization as the knob

- **Mechanics.** Rounding to a grid is noise, roughly uniform within ± half a step, largest where
  weights are small relative to their block's range, i.e. *on the fine distinctions*.
  Importance matrices steer the error away from what calibration text uses.
- **Reported feel (verbatim below in sources).** "drunk PhD", "sleep deprived", "degrades
  'ability' much faster than 'understanding'", "smear concepts together", "less common tokens
  more", IQ1_S "complete garbage, such as a long text with a hyphen after every single word",
  and ikawrakow's IQ1_S LLaMA-13B page, which keeps grammar and loses the frame: *"he was
  drenched in sweat … I advised him to walk upstairs … This is why she wants to go back to her
  house, where it is not yet 1870's and all over a little bit of 20th century."* That last one
  is the closest thing to a dream sentence in the whole quant record. It's the frame dissolving,
  not an image arriving. One contrary voice: someone who liked DeepSeek-R1 IQ1_S "for writing"
  (a 671B MoE, where most weights are experts that are rarely active).
- **Dose and cliff.** Mistral-7B, wiki, imatrix (Artefact2): Q4_K_M 5.8 % top-token flips /
  q99 KLD 0.09 → Q3_K_M 8.4 % / 0.25 → Q2_K 14.9 % / 1.03 → IQ2_XXS 23 % / 2.5 → IQ1_S 38 % /
  5.5. The tail explodes below ~3 bpw, and that's the cliff for a 7B. Bigger models move it
  lower. For a ~32B dense, practitioners put the usable floor around IQ3_XXS–Q3_K (e.g. Qwen3.8
  27B *"is strong even at Q3_xxs"*), and IQ2 is where 27B-class dense models get
  "lobotomized". **The pre-anneal checkpoint is unusually quant-robust.** *"once learning rates
  decay, validation loss and quantization error diverge"*, *"Higher learning rates
  consistently lead to smaller errors"* (Catalan-Tatjer et al., on OLMo 2 up to 32B). So OLMo
  stage1 needs *more* bits removed than a released model for the same drift. Our Q4_K_M is
  already ~6–7 % flipped tokens vs a higher quant (Q6_K vs Q4_K_M on the bench: 93.1 % same
  top).
- **On llama.cpp + Q4.** `llama-quantize --tensor-type 'blk\.(3[2-9]|4[0-9]|5[0-4])\.ffn_(up|gate)=q2_k' --imatrix im.gguf
  olmo-bf16.gguf out.gguf q4_k_m` quantizes one band harder. That's *selective quant as
  localized noise*, a real no-code knob. IQ1/IQ2 need an imatrix. `--allow-requantize` from
  the Q4 works but compounds error.
- **Cost, 32B.** Needs the bf16 gguf (as A). ~20 min per variant after that.
- **Architecture.** MoE bases take low quants best (sparse experts, and the scene's IQ1
  successes are all 235B–671B MoEs). Dense ~24–32B pre-norm bases break at IQ2. Large
  vocabularies (OLMo 3: 100k) are said to suffer more. **Run on** nothing new. If it's run at
  all, use `--tensor-type` on the OLMo stage1 bf16, band-limited, as a control arm for D.
- **Bet: slur, and the cactus A/B shows it's *toward the generic*.** Quantization is the
  wrong knob. It's one-dimensional (the curve is the same for every type), and it removes
  exactly the rare associations lightning needs.

### G. MoE router noise (one line, because it's the only *discrete* on-manifold weight noise)

- **Mechanics.** Noise on the router matrix (`ffn_gate_inp` in gguf, small, usually F32 or
  Q8, and editable in place like B′) flips *which trained experts* a token goes to. Every
  alternative is a function the model learned, so the perturbation is off-distribution in
  routing but on-manifold in computation. Switch Transformers trained *with* router jitter
  noise for this reason. Nobody I found has used it at inference for prose.
- **On llama.cpp.** A file edit on the router tensors, or llama.cpp's expert-count override
  (`--override-kv <arch>.expert_used_count=int:N`) as a cruder cousin.
- **Architecture / model.** MoE only. The clean candidate is **OLMoE-1B-7B** (AllenAI, open
  data and intermediate checkpoints), cheap enough to try on the Mac. A dense OLMo 3 32B
  can't do it.
- **Bet: unknown, worth a cheap evening on OLMoE before anything bigger.** It's the one
  mechanic where "a different trained function answers" is literally what happens.

### Bench pages (seed `shelf/seeds/short/08-what-is-that-hum.txt`, T 1.0, min_p 0.05, same RNG)

Two pages per condition, excerpts cut verbatim (… marks a cut). The seed ends "*I'm calling for
myself. The humming is not my own,*". This is a 1.5B Qwen, so it's crude, and n = 2 per
condition is anecdote, not evidence. The one directional pair is marked.

- **base**: *"The switch is not saying anything, it's not even humming, it's just there to
  connect the switch and the other switches to the power grid. I think it's called a
  "switching station"."* / *"I'm looking at a phone and hearing a voice. You're not there, I'm
  in a conference room somewhere."*
- **Q2_K**: *"The secret to my own is the secret to the secret. I, myself, myself, myself,
  myself …"* / *"I am the one that I am. Am I the one? I am the one that is? The one?"*
  (**loop, toward sameness**)
- **block gain, all linear, σ 0.1** (KLD 0.054): *"It's the humming from an old relay. … The
  hum is from a 2004 switch that is the oldest in the world. It was created by a team of
  engineers and the chief designer at the time, Paul Dabney and was installed by Bill
  McGibb."* (**fluent confabulation, the frame goes factual**)
- **block gain, all linear, σ 0.2**: *"It's like asking Siri for a calculation. … I do it for
  99999% of the tasks I'm asked to do every day"* / *"It sounds like, "It's not me." I say,
  "It's not you." But, it sounds like, "It's not me.""* (**frame lost, then a loop**)
- **block gain, mid-third ffn_down, σ 0.5**: *"There are two kinds of people in the world:
  those who are awake, and those who are still sleeping. … This is the beginning of a story.
  This is a story."* (**the document notices itself, then repeats**)
- **random gaussian LoRA ×3**: *"The switch is a metaphor for everything that goes in and out of
  your pocket … it's a person who is the switch, or a switch who is a person."* / *"I am
  calling my own cell phone from my cell phone to my cell phone."*
- **singular-gain jitter, top 0–64, τ 0.5**: *"an electric contact between the brass and the
  brass. … The switch is a switch of a switch."* (**the backbone jittered: sameness**)
- **singular band 64–512 removed ×−0.5 (LASER direction)**: *"I don't have a phone, I don't
  have a radio. I don't have a phone, I don't have a radio."* / the seed recited back.
  (**toward the average: loops**)
- **singular band 64–512 amplified ×1.25 (the opposite direction)**, KLD 0.043: *"It is the hum
  of another consciousness. … It is the voice of the universe speaking through me"* / *"I am a
  voice in my mother's dreams, a ghostly messenger to my brother who is away on a mission, a
  little bird, a flute, a bird in a cage. I am an angel, an angel in a cage. I am a bird on a
  string. I am the wind in the wind-up toy."* (**the only condition that produced images,
  inside the frame**)
- **singular-gain jitter, band 64–512, τ 0.15 ×3**: *"There was a time before the hum of the
  switch."* / *"is in fact just a dead switch and nothing more"* (**sober**)

The directional pair looked like the thing to keep: **the same singular band, removed → loops and
recitation; amplified by a quarter → images**. That's what LASER's account predicts (the band
holds the non-average alternatives), and it's what "uniform noise regresses to the prior"
predicts in reverse. Two pages each is nothing. The matched set below is where it went.

**Matched-divergence set (the check on the anecdote).** Four arms at mean KLD 0.04–0.07
(base; singular band +0.25; block gain all-linear σ 0.1; random LoRA ×2), seed 08, five sampler
seeds each, 150 tokens. The run for a second seed document was cut short because the Mac was
shared. I read these knowing the key, so what follows is my read, not a blind one. The shuffled,
unlabelled 20 pages are in `lab/blind.md` for a real blind read, with the key held in
`lab/key.json`.

| arm | distinct-2 (higher = less loopy) | 4-gram repeat share |
|---|---|---|
| base | 0.56 | 0.23 |
| singular band +0.25 | 0.72 | 0.18 |
| block gain σ 0.1 | 0.55 | 0.25 |
| random LoRA ×2 | 0.67 | 0.10 |

**The anecdote didn't hold up at n = 5.** The amplified-band pages were the *least loopy* on
average, but they were not stranger. One kept the frame and brought something (*"my partner,
who is calling for me. There is a rhythm to the hum, and my partner knows that I can only hear
it when I am sleeping"*). Two slid into explainer register (*"It has been studied by
researchers in the US"*, *"It's a low hum that comes from a device with an electronic
circuit"*), one into a forum answer, and one into the worst recursion of the set (*"my
switch's switch's switch's switch"*). The best pages in the set came from the *controls*: the
random LoRA's *"I am a switch. I am a device that connects wires to wires. … Let me take your
name and go to you. I am ready."* and the base's *"Hello hums hello, hello hums hello."* A 1.5B
Qwen is dominated by genre lock (explainer, Q&A, loops) whatever you do to its weights, so this
bench can't tell lightning from luck. It *can* say two things. The amplify direction doesn't
break the frame any faster than the controls do at matched divergence. And removing the band
reliably makes things worse.

## (b) The hypothesis: "frame = attention, grammar = early/mid, what arrives = mid-late MLP, so
noise only the middle third's MLP down-projection"

**Verdict: half right on the map, wrong on the tool and the address.**

- **For "what arrives is MLP", moderate evidence, mostly from factual recall in small
  models.** ROME's causal tracing: *"a distinct set of steps in middle-layer feed-forward
  modules that mediate factual predictions while processing subject tokens"* (GPT-2 XL, GPT-J).
  Geva et al. 2023 split it: *"enrichment process, driven by the early MLP sublayers"*, then
  the attribute is extracted *"typically … via attention heads, which often encode
  subject-attribute mappings in their parameters."* So even for facts, the *arrival* is shared
  with attention. Hase et al. undercut the localisation itself: edit success is *"essentially
  unrelated to where factual information is stored in models, as measured by Causal
  Tracing."* LASER places the swap-able alternatives (other answers of the same type) in the
  **late** MLP *input* (up/gate) spectra, not mid-layer down_proj. None of this is measured on
  prose forks. "Which image arrives at a fork in a page" is an extrapolation from "which city
  follows 'the Space Needle is in'".
- **For "the frame is held by attention", decent evidence for *context retrieval*.**
  Retrieval heads (<5 % of heads): *"completely pruning retrieval heads leads to failure in
  retrieving relevant information and results in hallucination"*, while *"tasks where the
  model directly generates the answer using its intrinsic knowledge are less impacted."*
  That's the right shape: spare attention and the model keeps pulling from the document.
- **Against "grammar is early/mid and fragile", the evidence says grammar is the *last* thing
  to go.** ikawrakow's IQ1_S LLaMA-13B pages are grammatical while the frame drifts (he→she,
  era jumbled). The 8B sweep's collapse, when it came, was at the *token* level. What goes
  first under uniform damage is the **frame** (entity tracking, who "he" is) and rare facts.
  Grammar goes last. Frame goes early, and that's why global noise feels like a slur and not
  a dream.
- **Against "the middle third" as the address.** The middle is the most redundant part of the
  stack. Deletion there is cheapest, and self-repair is strongest. On the bench, the mid-third
  down_proj needed twice the dose of "all layers" for the same divergence, and it hit its knee
  anyway (σ 0.8 → ppl ×8.5). You're spending dose to fight self-repair.
- **Against i.i.d. noise as the tool.** Even with the right address, isotropic noise regresses
  the MLP toward the average answer (LASER's mechanism, the quant A/B, and the bench's
  band-removal pages). To change *which* association wins you have to move the association's
  *gain*, not bury it in noise. That's mechanism D.
- **What I'd run instead.** Spare layers 0–⅛ and the last ⅛. Spare attention entirely.
  Amplify (+0.1…+0.4) or gain-jitter the singular band of up/gate just below the top outliers
  over ~50–85 % depth (OLMo 3 32B: layers 32–54, components ~128–1024). Then, at matched mean KLD (≈0.05, ~90 %
  same top), compare pages from three loci (attention-only, mid down_proj, late up/gate
  spectral) blind. KLD is locus-blind (bench), so matching it isolates *where* from *how much*,
  and the reader decides whether *where* changes the kind of strangeness. Nobody has run that
  comparison.

## (c) Sources

*paper*: Perturbation Robustness Profiles (Dak, 2026, Zenodo 20403835), Llama-3.1-8B-Instruct,
per-tensor std-normalized noise. https://zenodo.org/records/20403835
> "We inject per-tensor standard-deviation-normalized Gaussian noise … W_l' = W_l + σ · std(W_l) · ε_l"
> perplexity 12.87 → 13.14 (σ 0.05) → 13.93 (0.10) → 16.02 (0.15) → 21.07 (0.20)
> "Fragility tracks layer depth … Early (0–10) 1.0 · Middle (11–20) 2.0 · Late (21–31) 4.6 … The most fragile component is layer_1_mlp (σ* = 0.5)"
> "It is token-level incoherence: short fragments repeated, occasional cross-script characters, no syntactic structure." (samples: `ouchddenreeoraoraora`, `caffcaffcaffcaffedomongailailail`)
> "the sharp σ = 1.0 → σ = 2.0 transition is more consistent with a regime change in the model's coherent-generation capacity than with a graded loss of any specific learned content."

*paper*: Neural Thickets: Diverse Task Experts Are Dense Around Pretrained Weights (2026), arXiv 2603.12228
> "in large, well-pretrained models the density of task-experts increases dramatically, so that diverse, task-improving specialists populate a substantial fraction of the neighborhood around the pretrained weights."
> "They are specialists rather than generalists, where the perturbations that most improve performance on one task hurt performance on other tasks."
> "you can instead think about your pretrained weights as specifying a distribution over models. This distribution resists characterization just in terms of its mean: rather it contains diverse specialists whose behavior is qualitatively different from the singular pretrained weights."
> σ = 0.005 (Qwen2.5 0.5B–32B), 0.001–0.003 in RandOpt; toy: perturbations "search over many possible continuations following the kinds of functions seen during pretraining".

*paper*: Evolution Strategies at Scale (Qiu et al. 2025), arXiv 2509.24372. σ = 0.001 full-parameter gaussian on 0.5B–8B, N = 30. Perturbed populations are evaluated as working models.

*paper*: Noise Injection Reveals Hidden Capabilities of Sandbagging Language Models (Tice et al.), arXiv 2412.01784
> "Direct parameter modification … all parameters in the model are perturbed by directly adding our noise vector … we also developed a LoRA adapter method of noise injection" (r = 8), σ ∈ [0, 0.01]
> "When comparing the CoT transcripts as σ increases, we also noticed a qualitative reduction in the models mentioning of broader implications that may occur as a result of the model's response."

*paper*: Mechanistically Eliciting Latent Behaviors (CPE; Mack, Panickssery, Turner 2026), arXiv 2606.29604
> "meaningful concepts should activate entire computational pathways that propagate through the network, while random perturbations produce only local noise that quickly dissipates."
> "Random LoRAs rarely produce a consistent theme (nearly all mass lies at zero), confirming that coherent personas do not arise from arbitrary weight perturbations."

*scene*: Andrew Mack, "Mechanistically Eliciting Latent Behaviors in Language Models" (LessWrong, 2024). https://www.lesswrong.com/posts/ioPnHKFyy4Cw2Gr2x
> "for most examples I tried there was an intermediate 'Goldilocks' value of R which led to diverse but fluent continuations."
> "for random steering vectors, there is no Goldilocks value of R which leads to meaningfully different continuations. In fact, if we take random vectors with the same radius as 'interesting' learned steering vectors, the random vectors typically lead to uninteresting re-phrasings of the model's unsteered continuation, if they even lead to any changes"
> "it is possible to cram exponentially many almost-orthogonal directions within the residual stream … the chance that a random vector overlaps with any of the important feature directions is small."

*paper*: LASER: The Truth is in There (Sharma, Ash, Misra 2023), arXiv 2312.13558
> "this rank approximation, especially for MLP weights in the later layers of the model, often offers surprising benefits"
> "we find that these components describe either a different response of the same semantic category as the correct answer or generic high-frequency words. Seemingly, when the noisy, higher-order components are combined with the low-order components, their conflicting responses produce a sort of 'average answer,' which is likely to be incorrect."

*paper*: Small Singular Values Matter (Staats et al. 2024), arXiv 2410.17770
> "zeroing out the singular values that deviate from RMT raises language-model perplexity far more than removing values from the bulk, and after fine-tuning the smallest decile can be the third most influential part of the spectrum."

*paper*: The Super Weight in Large Language Models (Yu et al. 2024), arXiv 2411.07191
> "Pruning as few as a single parameter can destroy an LLM's ability to generate text – increasing perplexity by 3 orders of magnitude" / "always found in the mlp.down proj weight, always in an early layer."

*paper*: Locating and Editing Factual Associations in GPT (ROME, Meng et al. 2022), arXiv 2202.05262
> "a distinct set of steps in middle-layer feed-forward modules that mediate factual predictions while processing subject tokens."

*paper*: Dissecting Recall of Factual Associations (Geva et al. 2023), arXiv 2304.14767
> "the representation at the last-subject position goes through an enrichment process, driven by the early MLP sublayers … this extraction is typically done via attention heads, which often encode subject-attribute mappings in their parameters."

*paper*: Does Localization Inform Editing? (Hase et al. 2023), arXiv 2301.04213. Edit success is "essentially unrelated to where factual information is stored in models, as measured by Causal Tracing." (search-summary wording; the abstract carries the same claim)

*paper*: Retrieval Head Mechanistically Explains Long-Context Factuality (Wu et al. 2024), arXiv 2404.15574
> "completely pruning retrieval heads leads to failure in retrieving relevant information and results in hallucination" / "tasks where the model directly generates the answer using its intrinsic knowledge are less impacted by masking out retrieval heads"

*paper*: The Remarkable Robustness of LLMs: Stages of Inference? (Lad et al.), arXiv 2406.19384
> "interventions to the early and final layers cause the most degradation, while the model is remarkably robust to dropping middle layers."

*paper*: Training Dynamics Impact Post-Training Quantization Robustness (Catalan-Tatjer et al., ICLR 2026), arXiv 2510.06213
> "As the learning rate decays, validation loss consistently decreases, whereas quantization error rises sharply"
> "Higher learning rates consistently lead to smaller errors" / "at similar validation loss, larger learning rates achieve better low-bit quantization at no apparent cost."

*paper*: Understanding WSD Learning Rates: A River Valley Loss Landscape Perspective (Wen et al. 2024), arXiv 2410.05192. The stable phase "progresses along the river while oscillating between the sharp hillsides" (summary wording).

*paper*: DARE, "Language Models are Super Mario" (Yu et al. 2023), arXiv 2311.03099. DARE "can effectively remove 90% delta parameters without significantly decreasing performance … in some cases the drop rate can even reach 99%" (search-summary wording).

*paper*: CreativityNeuro (2026), arXiv 2607.01433. Scales "creativity-relevant" weights by (1+α), concentrated in later layers ("applying CN weights to a suffix of layers … recovers the full effect with roughly half the network"). It's a *selected* direction, closer to steering than to noise, and costs MMLU −3.1 points.

*forum*: ikawrakow, llama.cpp PR #5453 "1.5 bit quantization" (IQ1_S), 2024-02-11. https://github.com/ggml-org/llama.cpp/pull/5453
> "Don't expect literary or otherwise masterpieces. But it is not complete gibberish either."
> LLaMA-v1-13B IQ1_S: "Alaska is a state of the USA that lies in the northwest area of the United States. It was discovered by the British explorer William de Hale who had been expelled from the Queen's College and had no hope to be seen in 1768."
> "After climbing thirty flights of stairs, he was drenched in sweat and didn't feel much like climbing. I advised him to walk upstairs, but his legs were not yet ready for that. This is why she wants to go back to her house, where it is not yet 1870's and all over a little bit of 20th century. She wants to be in her home."

*forum*: llama.cpp discussion #5962 (Artefact2's blind human eval of quants, March 2024). https://github.com/ggml-org/llama.cpp/discussions/5962
> p-e-w: "Many of the responses I've seen contained complete garbage, such as a long text with a hyphen after every single word!"

*forum*: Artefact2, "Which GGUF is right for me?" KLD table, Mistral-7B, 2024-02-27. https://gist.github.com/Artefact2/b5f810600771265fc1e39442288e8ec9
> top-token differ: Q6_K 3.9 % · Q4_K_M 5.8 % · Q3_K_M 8.4 % · Q2_K 14.9 % · IQ2_XXS 23.1 % · IQ1_S 38.4 %; KLD q99 0.022 · 0.089 · 0.25 · 1.03 · 2.50 · 5.52

*forum*: r/LocalLLaMA, "671B IQ1_S vs 70B Q8_0" (2025-06-03). https://reddit.com/r/LocalLLaMA/comments/1l1r366/
> atineiatte: "Since the distances between parameters are less distinct, there's more inappropriate 'overlap' in concepts … The takeaway is lower quants smear concepts together and at some point it stops mattering or being noticeable" (gemma3-4b, "5 metaphors comparing a cactus": IQ1_S → "Cactus are known for their ability to withstand the elements." ×5, then "Each comparison is based on the same concept." looping; Q8 → "The cactus is a bottled rain, holding onto every precious drop.")
> PraxisOG: "Llama 3.3 70b at iq3xxs is smart for thinking and doesnt act too drunk despite being under q4 … The iq1 model of mistral acts almost sleep deprived, can't really think abstractly"
> radamantis12: "for ds r1 I tried the iq1_s one time and I really liked, so could be the best open source model for writing based on my preferences"

*forum*: r/LocalLLaMA, "Do you still think larger model with more quant is better than smaller model with less quant?" (2025-01-02). https://reddit.com/r/LocalLLaMA/comments/1hrogx6/
> LocoLanguageModel (69): "Highly quantized larger models = drunk PhD who can still give you better domain information than the intern."
> Pedalnomica: "The sense I get is that quantization degrades 'ability' much faster than 'understanding'."
> kongnico: "can confirm as a drunk phd who will randomly ramble information at you"

*forum*: r/SillyTavernAI, "Low-bit quants seem to affect generation of non-English languages more" (2025-07-31). https://reddit.com/r/SillyTavernAI/comments/1mdg3dx/
> "the free DeepSeek was even misspelling words by inserting random letters … My hypothesis: Quantization affects the generation of less common tokens more"

*forum*: r/LocalLLaMA, "How bad is 1-bit quantization but on a big model?" (2026-03-12). https://reddit.com/r/LocalLLaMA/comments/1rqppyw/
> Solembumm2: "90B at IQ1, sadly, were unusable. All models I tried resulted in gibberish word salad. 70B at IQ2 were worlds apart above it."
> Lucis_unbra: "The model is getting less confident on confident tokens … Sometimes the model seems to only have certain ways to get to a correct fact. Quantization makes it harder to access."

*forum*: r/SillyTavernAI, "Big model with high quantization VS small model with low quantization?" (2025-04-15). https://reddit.com/r/SillyTavernAI/comments/1jz8kwa/
> fizzy1242: "bigger models tend to be more creative for sure. you only really need high quants for high precision tasks like coding. but Q3~ should be fine for storytelling"

*forum*: r/LocalLLaMA, "I retrained only the fp16 block scales of ISTA's 3-bit Qwen3.8-27B GGUF …" (2026-09-17). https://reddit.com/r/LocalLLaMA/comments/1wi87us/
> "In a fixed GGUF the integer codes are frozen, but every quantised block still carries one or two fp16 scales, and the decoded weight is linear in them."
> "half of it Wikitext prose because prose is where every low-bit variant of this model drifts"

*forum*: r/LocalLLaMA, "Qwen 3.8 27b is strong even at Q3_xxs" (2026-08-21, title only). https://reddit.com/r/LocalLLaMA/comments/1vugryn/

*scene*: DavidAU (as u/Dangerous_Fix_5526), r/SillyTavernAI, "From DavidAU - SillyTavern Core engine Enhancements …" (2025-01-31). https://reddit.com/r/SillyTavernAI/comments/1ie2pev/
> "One of my primary goals when making models is to break prediction, this has a cost however - gibberish, repeats, and other issues at some times - usually just when the model is really hitting its stride so to speak."
> reply, Altotas (17): "anything from him with the word 'brainstorm' … just spews gibberish no matter the settings"
(His "Brainstorm" is layer grafting, item 5. It's the scene's main attempt at strangeness through weight surgery, and its own users describe it as a slur.)

*scene*: DavidAU, HF card "Maximizing Model Performance …". https://huggingface.co/DavidAU/Maximizing-Model-Performance-All-Quants-Types-And-Full-Precision-by-Samplers_Parameters
> "Higher quants will have more detail, nuance and in some cases stronger 'emotional' levels. Characters will also be more 'fleshed out' too." / "'nuance' is lost as the full precision model is more and more compressed (lower and lower quants)."

*forum*: llama.cpp `tools/server/README.md`. Per-request LoRA:
> "`lora`: A list of LoRA adapters to be applied to this specific request. Each object in the list must contain `id` and `scale` fields … If a LoRA adapter is not specified in the list, its scale will default to `0.0`."

*forum*: llama.cpp `tools/quantize/README.md`: "`--tensor-type` quantize specific tensor(s) to specific quant types. Supports regex syntax. May be specified multiple times."

## (d) What I could not find

- **Nobody has published generated prose from a weight-noise sweep**, at any dose, on any
  tensor family. Every paper measures accuracy, perplexity or task-specialisation. The feel
  of A–E comes from quant anecdotes, CPE/MELBO's random baselines, and my 1.5B bench.
- **No mergekit "noise"/"randomize" merge method exists** that I could find, and no forum
  report of DARE at high drop on a *base-only* setup (DARE needs a delta, which a lone base
  doesn't have, hence E). No first-hand prose descriptions of DARE at p ≥ 0.9 either.
- **No report of noising Q4 block scales** (only of *training* them).
- **No one has tried a random LoRA for its writing.** CPE only scored "consistency of theme".
- **No KLD/ppl-vs-bpw table for OLMo 3 32B** or any stage1 checkpoint. The quant-robustness of
  pre-anneal checkpoints comes from OLMo 2 (Catalan-Tatjer), and the cliff numbers are from
  Mistral-7B.
- **No SVD-projected noise paper for LLM *generation*.** The spectrum literature (LASER, RMT,
  LoRA variants) is about pruning and QA accuracy.
- **Arctic Shift comment search timed out almost all session** (several agents on it at once),
  so reddit quotes come from post searches plus whole threads pulled by id. There are probably
  better r/SillyTavernAI low-quant prose threads from 2024 that I didn't reach.
- **The bench is small**: Qwen2.5-1.5B (not a clean base, pre-norm), 5k tokens, one seed per
  condition, a Mac shared with other agents' runs. It supports "one curve" and "sharp knees".
  It can't say anything about lightning at 32B.
