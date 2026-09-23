# 03 — attention tampering and layer tampering (brief items 4 and 5)

Two things are new here. I read the llama.cpp source for how OLMo 3 is actually wired (`src/models/olmo2.cpp` at master, 2026-09-24), and then **ran most of the mechanisms myself** on the closest cheap stand-in for your model: `Olmo-3-1025-7B` at its **stage1 checkpoint** (`AIgotahole/…stage1-step1413814-Q5_K_M-GGUF`, same arch as the 32B: olmo2, QK-norm, post-norm, sliding windows with every 4th layer full attention). I stripped its yarn keys so it matches your 32B's `rope_scaling: null`. Run on the mac, Metal.

Protocol, so you know how much to trust it: perplexity is measured on the first 40 KB of `docs/anthology-weird.md`, ctx 256 (page-sized), 24 chunks. The pages continue `shelf/seeds/short/05-all-ive-got-are-names.txt`: 170 tokens, temp 1.0, min_p 0.05, **no DRY**, seeds 11/22/33. The ppl numbers are real measurements. The pages are **three per variant, so they are anecdotes**. Loops show up everywhere because there is no repetition brake.

The scripts are in `scratchpad/mescalito/attn/`: `gguf_dial.py`, `gguf_gain.py` and `gguf_layers.py`. The measured pages are in `attn/out/*.txt`. The variant ggufs were deleted.

---

## (a) Per mechanism

### A1. Attention temperature, as a free gguf edit on OLMo

**Mechanics.** In llama.cpp's olmo2 graph, Q is RMS-normed over the whole 5120-wide vector *before* rope. The norm weight `blk.N.attn_q_norm.weight` is a plain **F32** vector in the Q4_K_M gguf. I read Tricit's 32B header by range request: all 64 `attn_q_norm`/`attn_k_norm`/`post_*_norm` tensors are type 0 = F32, because llama-quantize never quantizes 1-d tensors. q·k is linear in q and rope is a rotation, so multiplying that vector by *a* multiplies **every attention logit in that layer by a**. That is attention temperature 1/a. It needs no patch and no requant, and it is an in-place write of 64 × 20 KB. The kq_scale itself is hardcoded (`1.0f/sqrtf(n_embd_head)`), so **no metadata key scales attention on olmo2**: `attention.scale` is read only by granite-family archs, and `attn_logit_softcapping` only by gemma2. Slicing the vector by 128 dims gives per-head temperature. Slicing within a head by rope pair (neox: dims i and i+64) gives **per-frequency-band** temperature.

**Measured (7B stage1; clean ppl 13.55).** The dial runs from flatter (`attn_q_norm ×a`, a<1) to sharper (a>1):

| q_norm × | 0.6 | 0.8 | 1.25 | 1.6 | 2.0 | 0.6 on middle layers only (8–23) |
|---|---|---|---|---|---|---|
| ppl | **26.7** | 14.0 | 14.1 | 15.7 | 18.7 | 16.6 |

**The cliff is asymmetric.** Flattening by 1.67× doubles perplexity. Sharpening by 2× costs +38%. That is consistent with the active/dormant-head picture: most heads, most of the time, park their attention on a sink token as a no-op. Flatten them and they wake up and write a context-average into every position.

**Feel, measured.**
- *Flattened ×0.6*: incantation. The frame's vocabulary survives while its sense dissolves: *"the words that were the way they were, they were the words that were in them. what the wind was. the wind."* / *"i am nothing. you are nothing. … i am you."* This is glossolalia built from the seed's own words. It is not word salad, but it is not a page either.
- *Sharpened ×2.0*: the most lightning-like pages of the whole run. The frame is gripped hard, and the seed's nouns are recombined into new predicates: *"the letters were a spell to hold me prisoner, as if my own name were a cage"*, *"we are all letters that will never be sent. … we are alphabet soup. and we are not having it."*, *"all we know is that some names have been sown."* Grammar frays at the edges (*"and when the check comes do."*, *"dare not write. the same."*). The failure mode is anaphora and loops, and that is exactly what DRY exists to brake.
- *Sharpened ×1.6*: argument loops. *"and if it was the world that made me write down what i wrote down, then perhaps it was the world that made them leave me in a haze."* That is OLMo's sobriety turned into a mantra.

**Per band (a new result, as far as I know).** Sharpening only the slow-rotating (semantic) rope bands 40–63 by ×1.6 → ppl **24.2**, and the model **recites the seed back verbatim** (*"i have no more faith than you do. i have no more faith than you do. …"*). The same ×1.6 on the fast bands 0–23 → 14.4, and the pages read normal. So the attention "sharpness" that matters lives in the low-frequency channels. The fast (positional) bands tolerate a lot.

**Literature.** Thermometer of Thoughts (ACL 2026, Qwen3) does exactly `self_attn.scaling /= T`. It reports quality *"stable for attention temperatures between 0.9 and 1.1, with a limited effect from 0.8 to 1.3. However, temperatures below 0.5 or above 1.7 frequently lead to reasoning chains irrelevant to the input"*. Their failure level II is *"grammatically coherent but irrelevant to the given task"*, which is the frame lost with grammar intact. Their T is the inverse of my *a*, so their "irrelevant" high-T end is my flattened side.

**Dose.** a ∈ [1.25, 2.0], sharpening only. The flattened side past 0.8 is where the frame goes.

**Run it.** `cp` the gguf, then `gguf_dial.py model.gguf attn_q_norm 1.6 all`. The optional args are a layer range, heads, and bands. To undo, apply the reciprocal to the same file.

**Cost on the 32B.** Zero VRAM, zero speed. A second 18 GB copy on disk, or edit in place and reverse it.

**Arch line.** This favours **QK-norm models with F32 norm vectors**:
- OLMo 2 / OLMo 3: the norm spans all heads, so per-head control is possible.
- Gemma 3 and Qwen3 have per-head-dim q_norm shared across heads, so per-layer control only (and Qwen is dirty).
- Pre-norm, no-QK-norm archs (Llama 3.1, Mistral Nemo, Mistral Small 3.1) have no F32 hook. For those, use A2 (the flag) or A3 (the block-scale edit).

Clean base to run it on: **OLMo 3 32B stage1** (yours). All 64 layers are reachable this way, unlike A2.

**Bet: lightning-leaning** at 1.6–2.0 with DRY on. I rank this first among the attention mechanisms.

### A2. `--yarn-attn-factor`: the runtime attention-temperature flag nobody uses as one

**Mechanics.** In ggml's `rope_yarn`, `cos_theta = cosf(theta) * mscale; sin_theta = sinf(theta) * mscale`. mscale is `attn_factor` even when ext_factor = 0 (checked in `ggml-cpu/ops.cpp` and `ggml-cuda/rope.cu`). So `--yarn-attn-factor x` scales both rope'd Q and K by x, which multiplies the logits by **x²**. The catch is that olmo2's sliding-window layers are hard-wired to `attn_factor 1.0` ("For sliding window layers, Olmo3 use regular rope with no yarn"). On OLMo 3 the flag therefore reaches **only the full-attention layers: 16 of 64 on the 32B, 8 of 32 on the 7B**.

**Measured.** x = 1.3 → 13.79; x = 0.7 → 14.83. The pages are ordinary, with slightly more "we're all the same" loops at 0.7.

**Run it.** A flag, no file. **Cost:** zero.

**Arch line.** On a model without sliding windows this is the all-layer attention temperature for free:
- **OLMo 2 32B base**: same QK-norm family, full attention everywhere, stage checkpoints published.
- **Mistral Nemo 12B / Mistral Small 3.1 24B base** and **Llama 3.1 8B/70B base**: all layers are rope'd with attn_factor.
- Gemma 3: only the global layers, the local ones use their own rope base.

**Bet.** Same as A1 wherever it reaches all layers. On OLMo 3 it is weak.

### A3. Block-scale gain: A1's twin for quantized matrices (any arch)

**Mechanics.** k-quants dequantize as `d·sc·q − dmin·m`. Multiplying the fp16 `d` and `dmin` of every super-block by *a* scales the whole tensor by *a*, and nothing else changes. Layouts:
- Q4_K: bytes 0–3 of each 144-byte block.
- Q5_K: bytes 0–3 of each 176-byte block.
- Q6_K: bytes 208–209 of each 210-byte block.
- Q8_0: bytes 0–1 of each 34-byte block.

I verified it with gguf-py's dequantizer on the 7B: `ffn_down` (Q6_K) ×0.8 → relative error 1.8e-3, and `attn_q` (Q5_K) ×1.3 → 1.0e-3. That is below the quantization noise itself.

**Use.** On Llama/Mistral, `attn_q ×a` is attention temperature 1/a, and `attn_output`/`ffn_down ×b` is mergekit's passthrough `scale` (*"A scalar to multiply the tensor by. Useful for scaling specific layers, e.g., `{"filter": "down_proj", "value": 0.5}`"*) with no f16 round-trip. **On OLMo it does nothing** to attn_q, wo or ffn_down, because a norm follows each one and cancels the scale. There you use the norm vectors (A1, L4).

**Script.** `gguf_gain.py model.gguf attn_q 0.8 all`.

**Arch line.** For pre-norm archs without QK-norm. Clean base: **Mistral Small 3.1 24B base**.

### A4. RoPE off its trained values

**Mechanics.** θ_i = base^(−2i/d). Pair 0 rotates at 1 rad/token whatever the base. The base only moves the middle and slow pairs. So at page length (≤ 300 tokens), **raising** the base barely matters, because the slow pairs are already nearly still. **Lowering** it makes the semantic (slow) channels start rotating inside the page: two tokens 50 apart suddenly look "misaligned" on the channels that carry meaning. On OLMo 3, `--rope-freq-base` reaches **all** layers (sliding and full share `freq_base`). `--rope-freq-scale` reaches only the 16 full-attention layers (sliding is hard-coded to 1.0).

**Measured (trained base 500000).**

| setting | base 5000 | base 50000 | base 5e7 | freq-scale 0.5 | freq-scale 4 |
|---|---|---|---|---|---|
| ppl | **22.1** | 14.3 | 15.8 | 13.7 | 14.2 |

**Feel at base 5000.** Pure sentence loops, grammatical and frame-kept: *"who are these people who have names but are not people?"* × 15, and *"they are the people who are called the people who are called…"*. **The orchestrator's prior holds, minus the garbage**: at 100× too low you get position confusion → repetition, not salad. At 5e7 you get mild drift with an odd image or two (*"all the stars have died in this city"*), which is baseline-like. freq-scale is inert on OLMo 3 at page length. kaiokendev on the untuned llama-1, 2023: *"it is known there is massive ppl increase when scale <0.5 for the untrained model but performs well for 0.5 for some reason"* (r/LocalLLaMA, 14lz7j5). Nexesenex's CodeLlama scan (llama.cpp #3090, via SabinStargem): the *"variance between 10000, 100000 and 1000000 is a curve with 0.2 perplexity amplitude at 512 ctx"*. A 100× base error costs almost nothing at short context. I found **no practitioner description of "strange but coherent" prose** at wrong rope values. The reports are ppl curves and "gibberish/spaces and newlines" bug reports.

**Dose and cliff.** The cliff is between 50k and 5k (10–100× under the trained base).

**Run it.** A flag. **Cost:** zero.

**Arch line.** OLMo 3: base reaches everything, scale reaches 1/4. Gemma 3's local layers ignore `--rope-freq-base`. Llama/Mistral: everything.

**Bet: slur-with-extra-steps (loops).** One row of the table, as you guessed. Skip it.

### A5. KV-cache noise / quantization

**Mechanics.** llama.cpp only offers `q8_0, q4_0, q4_1, iq4_nl, q5_0, q5_1` for `-ctk/-ctv` (no 2-bit, no noise injection). Anything stronger needs a patch at the cache write.

**Measured.** `-ctk q4_0 -ctv q4_0 -fa on` → ppl **13.58 vs 13.55**. At page length the cache is too short for the error to accumulate.

**Literature and scene.** KIVI: *"the key cache should be quantized per-channel … the value cache should be quantized per-token"*; 2-bit KIVI *"maintain[s] almost the same quality"*. The scene's complaints are all about long context and agents: *"I can't stand kv cache quantization. Even at q8_0, I can feel the difference"* (r/LocalLLaMA 1wdqit1, 2026-09-12), and *"I think the tradeoffs compound, especially at longer contexts"* (1wl5hfk, 2026-09-20).

**Bet: a non-dial** for 170-token pages. It is dead.

### A6. Dropping heads at random per token

**Mechanics.** The frame lives in a sparse set of heads:
- Retrieval heads: *"only a small portion (less than 5%) of the attention heads are retrieval … completely pruning retrieval heads leads to failure in retrieving relevant information and results in hallucination, while pruning random non-retrieval heads does not affect the model's retrieval ability"* (Wu et al. 2024).
- Induction heads: Crosbie & Shutova (NAACL Findings 2025) report that ablating the top 1% of induction heads cuts ICL by up to ~32%, bringing few-shot *"close to that of zero-shot"*, far more than the same fraction of random heads.
- Michel et al. 2019: most heads can go at test time.

So random dropping at rate p is **mostly a no-op**, punctuated by tokens where a frame head happens to be down. On those tokens the prediction falls back on **the model's prior**, which is the *most common* continuation, not a strange one. That makes it the wrong uniform twice over: it hits the frame, and what it inserts is banality.

**Run it.** It needs a patch: a per-token mask in `build_attn`. With GQA on the 32B (40 q heads / 8 kv), dropping a kv head silences 5 q heads at once.

**Bet: slur/banal.** I did not measure it. The argument rests on the sparsity results above.

### A7. Attention sink / first token

StreamingLLM: models *"assign high attention weights to initial tokens regardless of semantic relevance"*. The sink is the no-op parking spot of dormant heads (Guo et al. 2024, *"attention heads become sinks for specific input domains while remaining non-sinks for others"*, shown in Llama and OLMo). Perturbing it alone needs a patch. A1's asymmetry is the indirect evidence of what happens when the sink stops absorbing: flattening costs 2× ppl, while sharpening (which deepens the sink) is gentle. **Bet: slur.** Not worth a patch.

---

### L1. Layer repetition (frankenmerge / passthrough / RYS)

**Mechanics.** A block runs twice on its own output. In OLMo each sublayer's write goes through a post-norm before the residual add, so a repeated block's writes have fixed RMS. The extra pass cannot blow up the residual the way it can in pre-norm Llama. **I expect post-norm models to tolerate repeats better**; that is my inference, not tested against a pre-norm model.

**Measured (7B, 32 layers; 4-layer repeats, the minimum dose in Drew Smith's MoE runs).**

| repeated block | 4–7 (early, 13–22%) | 14–17 (mid, 44–53%) | 22–25 (late, 69–78%) |
|---|---|---|---|
| ppl | 14.1 | 15.2 | 14.8 |

All three read fluent and frame-kept, with a little more lyric drift. Mid: *"she tells me about the time before time, … and i had forgotten to come back from the moon"*, and one fused-token slip (*"they don my earphones"*). Late: *"all we are is a name we put on a face, and all we feel are these letters we wrote in a dream we wrote ourselves into"*. With n=3 I cannot separate that from baseline luck. The ppl cost is small and graded by depth, which is the useful part.

**Scene.**
- Caffeine_Monster (r/LocalLLaMA 1cpct22, 2024-05-11), the one person who says he grid-searched: *"the interleave size is mostly a tradeoff between creativity and smarts. For smarts an interleave size of 20 consistently worked best … with larger slices (e.g. 30) you lose most of the creativity … The most interesting models i've seen or produced have always been with a 16 interleave (like goliath)"*, and *"using [31, 60] or [29, 60] can work a lot better than [30, 60]"*.
- The same thread's OP on miqu-103b `[[0,40],[20,60],[40,80]]`: *"performs like a slightly tipsy Miqu after a glass of wine - a bit sluggish but full of inspirations"*. Also: *"The doubled layer segment shall not be too close to the begining and end"*, and *"the stacked-layer models could be more context-aware and more creative / … could easily fail on logic and accuracy"*.
- JoeySalmons on TinyLlama (194zwyc, 2024-01-13): the arrangement *"keeps a good amount of coherence while making the model much more creative … The base model is way more coherent, but also way less creative"*. His sample drifts into verse inside a bedtime story: *"A flock of birds, in the golden light; / A sight, that's like a golden sun. / 'Oh, for a bottle full, of, / A flood-tide, like the streams…"*.
- semiring (18uybsm): *"Some of the 'mid block overlap' models (like Goliath 120B) seem pretty effective, while other mixtures (e.g., just doubling every single layer in situ) lead to the production of nonsense."*
- On Goliath: *"Goliath is an unruly horse. It will allow itself to be controlled until it doesn't a s just goes and does its own thing. But it's prose is so much better"* (Dry-Judgment4242, 18a6x6z, 2023-12-04). And *"people say it does grammar mistakes does it means some precision is lost but creativity increased"* (Single_Ring4886, 18ft8f5), which is hearsay but matches my typo finding under L2.
- David Noel Ng (RYS, "LLM Neuroanatomy", 2026-03-10): he repeated layers 45–51 of Qwen2-72B. *"single-layer duplication almost always failed"*. Bad configs: *"One cheerfully announced 'Let's act like cowboys! Yeehaw!' apropos of nothing, and then descended into an unrecoverable giggling fit, generating pages of 'hahaha' interspersed with cowboy references"*; others *"stuttered and fell into degenerate loops"*.
- Drew Smith (1rvxmnh, 2026-03-17, dense Qwen2.5-32B with 64 layers, the same depth as yours): a *"danger zone"* at 56–65% depth. *"Delete it = output dies. Duplicate it = reasoning dies"*. Also *"One block, one copy. Every attempt to do more made things worse"* (triple-stack → *"barely produces Python"*). He measured code only.

**Dose.** Block length 4–8, one copy, placed away from the first/last ~15% and away from 56–65% depth. On the 32B that means repeating e.g. **24–31** or **44–51**, not 36–42.

**Run it on a Q4 gguf with no requant.** `gguf_layers.py in.gguf out.gguf "0-31,24-63"` (tested on the 7B). It copies Q4_K/Q6_K tensor bytes verbatim, renumbers the blocks, sets `block_count`, and re-lays `sliding_window_pattern` so each copy keeps its trained sliding/full type. mergekit → convert → quantize would cost the 64 GB f16 download; this does not. llama.cpp has **no layer-skip/repeat flag** (grep for skip-layer finds nothing). The only runtime hack I found is semiring's 2023 fork (`LLAMA_CHUNKS="0.0,0.6,0.2,0.8,0.6,1.0"`), long stale. exllamav2 has `--repeats` (PR 275) and there is EGjoni/David for transformers.

**Cost on the 32B.** +8 layers ≈ +2.3 GB file and VRAM (18.1 GB × 8/64) and +12.5% time per token. It fits a 24 GB card and is easy on 48 GB. Writing the new 20 GB file takes minutes of disk.

**Arch line.** The frankenmerge lore is all pre-norm Llama/Mistral dense. On MoE the good depth moves earlier (Smith: 38–44%). Sliding-window archs need the pattern re-laid (the script does it). Clean bases: **OLMo 3 32B stage1**, and **Mistral Small 3.1 24B base** as the pre-norm comparison.

**Bet: lightning-leaning.** It is the only mechanism with *practitioners* independently reporting "more creative, coherence mostly kept".

### L2. Layer skipping and shuffling

**Measured.**
- Zeroing layers 14–17 (the exact skip via post-norms, see L4) → ppl **19.6**.
- Shuffling the middle 12 layers (10–21) randomly → ppl **42.3**.
- Swapping one adjacent pair (16↔17) → 13.85, which is nothing.

**The feel is the key finding: skip and shuffle produce fused-token misspellings.** Skip: *"i didnth write it. i couldnth."*, *"i donth think"*. Shuffle: *"it's a bet that you donnot have it"*, *"you shouldnthing it"*, *"but donthis:"*, *"I donof things like this"*. Themes stay (dream, storm) while syntax fragments. This is the "slur" in its literal form: the model loses track of *which subword it is in the middle of*. It is probably what Goliath's rumoured "grammar mistakes" are.

**Literature.**
- Painters (Sun et al. 2024): *"Both randomizing and reversing the middle layer order has graceful degradation"*, *"Repeating a single layer is worst. Randomizing the layer order and looped-parallel do the least damage"*, and, relevant to OLMo's sobriety, *"Mathematical and reasoning tasks are more order dependent than 'semantic' tasks."* Order-tampering eats arguments first.
- ShortGPT: removing 25% of layers keeps ~90% on MMLU, yet *"the performance in generative tasks such as XSum and C3 deceases to nearly zero"*. Benchmark tolerance is a lie for prose.
- Lad, Gurnee & Tegmark (2024): deleting or swapping *middle* layers retains 72–95% accuracy; the first and last layers are critical.
- SOLAR's depth up-scaling needed continued pretraining: *"The performance of the depthwise scaled model initially drops below that of the base LLM."*
- LayerShuffle is a *training* method for vision transformers; untrained networks *"are typically not robust toward pruning or shuffling layers at test time"*.

**Dose.** The shuffle's dial is the number of swapped adjacent pairs. One is inert, 12-wide random is slur.

**Arch line.** Same as L1.

**Bet: slur.** Unless someone finds an intermediate that trades strangeness for typos, and I didn't see one.

### L3. Layer dropout / LayerDrop at inference

LayerDrop and LayerSkip are *trained-in*. On an untrained model, per-token random skipping means L2's typo slur arriving at random tokens. It needs a patch. **Bet: slur.**

### L4. Sublayer gain via the post-norm vectors (OLMo-specific, free)

**Mechanics.** olmo2 normalizes each sublayer's *output* (`post_attention_norm`, `post_ffw_norm`, both F32) before adding it to the residual. Weight × b means the sublayer writes b× louder. b = 0 on both is an **exact skip** of the block with no file surgery. This is how skip14 above was made.

**Measured (layers 8–23).** MLP ×1.3 → 14.08; MLP ×0.7 → 14.73; attention ×1.3 → 14.36. The pages read in baseline register. att13 gave *"there's a hole where the name should go, and the hole is the size of a hole. every name is the size of a hole"* before looping. n=3, so it proves nothing. Cheap, graded, safe.

**Arch line.** Post-norm archs only: OLMo 2/3, and Gemma 2/3 carry post norms too. On Llama/Mistral use A3 on `ffn_down`/`attn_output`.

**Bet.** An untested middle. The "louder associations in the middle layers" mechanism is the one that *should* keep attention (the frame) intact while bending what arrives. It is worth one sweep at ×1.5–2.0, which I didn't reach.

---

## (b) What keeps the frame and what kills it

The frame is attention to the seed, and it is carried by a **few** heads: under 5% retrieval heads, about 1% induction heads. They match on the **slow rope bands**, so sharpening those bands alone made the model recite the seed. Everything else is the model's associative weather: MLPs, middle-layer representations, the choices at forks.

- **Frame-killers.** Flattening attention (the heads average and the frame dissolves into its own vocabulary, in both my data and Thermometer's "coherent but irrelevant"); random head drops (sparse frame heads go down and the prior fills in, which is banal); lowering the rope base (the semantic channels rotate).
- **Frame-over-keepers.** Sharpening attention and sharpening the slow bands. The frame is gripped too hard. The failure is loops and recitation, which the sampler (DRY) can brake. At ×2.0 it produced the strangest recombinations of the seed's own nouns.
- **Frame-neutral.** Layer repeats and sublayer gain in the middle layers. They leave the attention machinery and the embeddings exactly as trained and change *how much processing* the residual gets. That is the only family where practitioners report "more creative, still coherent". It also sits exactly on the Painters' finding that middle layers share one representation space, so an extra middle pass stays on-manifold.
- **Slur.** Skip, shuffle and layer dropout: fused-token misspellings. The geometry: the residual reaches the late layers in a state they never saw, and the first thing to go is subword bookkeeping.

Argued position: **uniform attention tampering cannot give you lightning, because attention *is* the frame. The only good direction is sharper, and its "strangeness" is the frame folding in on itself.** Lightning, if it exists in this slice, comes from perturbing *depth* (repeat, gain) while attention stays trained.

## (c) Sources

- *paper* Sun et al., "Transformer Layers as Painters", https://arxiv.org/abs/2407.09298: the quotes above.
- *paper* Lad, Gurnee, Tegmark, "The Remarkable Robustness of LLMs: Stages of Inference?", https://arxiv.org/abs/2406.19384
- *paper* Men et al., ShortGPT, https://arxiv.org/abs/2403.03853: *"When we remove 25% layers from Llama2-7B or Baichuan2-7B, the performance in generative tasks such as XSum and C3 deceases to nearly zero."*
- *paper* Gromov et al., "The Unreasonable Ineffectiveness of the Deeper Layers", https://arxiv.org/abs/2403.17887: *"minimal degradation of performance until after a large fraction (up to half) of the layers are removed"* (on QA, after healing).
- *paper* Kim et al., SOLAR 10.7B (depth up-scaling), https://arxiv.org/abs/2312.15166
- *paper* LayerShuffle, https://arxiv.org/abs/2407.04513
- *paper* Yu et al., "Thermometer of Thoughts", ACL 2026, https://aclanthology.org/2026.acl-long.200/
- *paper* Wu et al., "Retrieval Head Mechanistically Explains Long-Context Factuality", https://arxiv.org/abs/2404.15574
- *paper* Crosbie & Shutova, "Induction Heads as an Essential Mechanism…", https://arxiv.org/abs/2407.07011
- *paper* Michel et al., "Are Sixteen Heads Really Better than One?", https://arxiv.org/abs/1905.10650
- *paper* Xiao et al., StreamingLLM / attention sinks, https://arxiv.org/abs/2309.17453; Guo et al., "Active-Dormant Attention Heads", https://arxiv.org/abs/2410.13835
- *paper* Liu et al., KIVI, https://arxiv.org/abs/2402.02750
- *scene* David Noel Ng, "LLM Neuroanatomy" (RYS), https://dnhkng.github.io/posts/rys/
- *scene* mergekit merge methods (passthrough `scale`), https://github.com/arcee-ai/mergekit/blob/main/docs/merge_methods.md
- *scene* llama.cpp source: `src/models/olmo2.cpp` (hardcoded kq_scale; sliding layers pass attn_factor 1.0 and freq_scale 1.0), `ggml/src/ggml-cpu/ops.cpp` `rope_yarn` (mscale applied unconditionally), `common/arg.cpp`, https://github.com/ggml-org/llama.cpp
- *forum* llama.cpp issue #3090 (CodeLlama rope base scan), https://github.com/ggml-org/llama.cpp/issues/3090
- *forum* r/LocalLLaMA:
  - "I spent a weekend doing layer surgery…", Drew Smith, 2026-03-17: https://reddit.com/r/LocalLLaMA/comments/1rvxmnh/
  - "Best Miqu and Llama-3 Frankenmerge (Self)", 2024-05-11, OP and Caffeine_Monster: https://reddit.com/r/LocalLLaMA/comments/1cpct22/
  - "Instant Frankenmerges with ExllamaV2", 2024-01-13, JoeySalmons, Small-Fall-6500 (*"very easy to make the model almost completely incoherent"*), typhoidisbad (Mistral 7B: *"the highest scoring ones were cases where I doubled the middle third of layers (or tripled)"*): https://reddit.com/r/LocalLLaMA/comments/194zwyc/
  - "Are we missing an obvious way to boost inference quality?", 2023-12-31, semiring: https://reddit.com/r/LocalLLaMA/comments/18uybsm/
  - Goliath comments: Dry-Judgment4242 in https://reddit.com/r/LocalLLaMA/comments/18a6x6z/ (2023-12-04); Single_Ring4886 in https://reddit.com/r/LocalLLaMA/comments/18ft8f5/ (2023-12-11); Secret_Joke_2262 in https://reddit.com/r/LocalLLaMA/comments/18eakw0/ (*"goliath does a better job of writing stories in terms of composure and understanding of context, but worse in originality"*)
  - NTK-aware RoPE thread, kaiokendev and bloc97, 2023-06: https://reddit.com/r/LocalLLaMA/comments/14lz7j5/
  - KV-quant complaints: https://reddit.com/r/LocalLLaMA/comments/1wdqit1/ and https://reddit.com/r/LocalLLaMA/comments/1wl5hfk/
- *measured, ours*: `scratchpad/mescalito/attn/out/*.txt` (pages plus ppl per variant); the scripts `gguf_dial.py`, `gguf_gain.py`, `gguf_layers.py`

## (d) What I could not find

- **Nobody describes prose under attention temperature.** The only papers score reasoning benchmarks, and no forum thread tries it. My pages are the first I know of: n=3, one seed, one sampler, on a 7B.
- **No quotes describing wrong-RoPE output as anything but ppl or "gibberish" bug reports.** My base-5000 loops are the qualitative evidence.
- **No report of shuffling (rather than repeating) in mergekit** or the scene. Everyone repeats. The Painters paper covers shuffling on benchmarks, and my run covers it on a page.
- **No measured frankenmerge feel on a *base* model.** Every quote is about instruct or roleplay tunes (Goliath, miqu, lzlv). Base models may respond differently.
- **Nothing on random per-token head dropout for generation quality.** The A6 bet is argued from the head-sparsity papers, not seen.
- **Arctic Shift comment search timed out repeatedly** under six parallel researchers, so the Goliath "typos" quote is the one hearsay line I could get, not the original claim.
- **Not run:** the 32B itself; DRY-braked pages (which would change the loop verdicts); sublayer gain above ×1.3; sharpening restricted to middle layers; any pre-norm model for the repeat comparison.
