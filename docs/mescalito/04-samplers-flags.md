# 04 — sampler-side lightning, and what llama.cpp exposes today

Slice: brief item 7 (samplers, scheduled heat, where the sampler stops) plus the llama.cpp flag
inventory the other five reports lean on for their "how to run it" column. Everything in the
inventory was read from `ggml-org/llama.cpp` master at `d2e5458` (2026-09-23): `common/arg.cpp`,
`common/common.h`, `common/sampling.cpp`, `src/llama-sampler.cpp`, `src/llama-adapter.cpp`,
`src/models/olmo2.cpp`, `tools/server/server-schema.cpp`, `tools/server/server-context.cpp`,
`tools/server/README.md`. Where the README and the code disagree, the code wins and the gap is
named.

## 0. The one fact that reorganizes this slice: at temperature 3+, temperature is not the dial

llama.cpp's default chain is `penalties; dry; top_n_sigma; top_k; typ_p; top_p; min_p; xtc;
temperature` (`common.h`, the `samplers` default). Temperature runs **last**. `min_p` is
implemented as a logit-gap cut (`min_logit = max_logit + logf(p)`, `llama-sampler.cpp`), so it
keeps every token within `ln(1/min_p)` nats of the top one, computed on the **raw** logits, and
temperature then only reshapes the survivors. Two consequences, both arithmetic:

1. **Temperature saturates.** The weight of the weakest survivor relative to the top is
   `min_p^(1/T)`:

   | min_p (gap) | T 1 | T 2 | T 2.5 | T 3 | T 5 | T ∞ |
   |---|---|---|---|---|---|---|
   | 0.08 (2.53 nats) — the stream's | 0.08 | 0.28 | 0.36 | 0.43 | 0.60 | 1 |
   | 0.03 (3.51 nats) | 0.03 | 0.17 | 0.25 | 0.31 | 0.50 | 1 |
   | 0.01 (4.61 nats) | 0.01 | 0.10 | 0.16 | 0.22 | 0.40 | 1 |

   Going from T 3 to T 5 moves the weakest survivor from 0.43 to 0.60 of the top: from "fairly
   flat" to "flatter". The set of possible tokens doesn't change at all. At T→∞ it is just
   *uniform over the min_p survivors*, which the scene figured out early: *"MinP=0.125,
   temperature=infinity, for models in the 8B to 12B size range … outputs are more creative and
   engaging, less repetitive, and still coherent"* (cynerva, r/LocalLLaMA, 2024-08-18).
   **Your own `olmo-heat-5.0.md` page (t5.0, xtc 0.5/0.1, min_p 0.08, DRY) reads like a sober
   parish memoir, and that's what the arithmetic predicts**: the heat run confirmed the table.
   It didn't find a model that resists heat.

2. **"T=3 with min_p" in the papers is a different sampler from T=3 in llama.cpp.** The min-p
   paper (and HF transformers) apply temperature *before* min_p, so the gap grows with T:
   `T·ln(1/m)`. The conversion is `min_p_llama = min_p_paper ^ T`. The paper's "τ=3, min_p 0.1"
   creative-writing regime is **min_p ≈ 0.001 at T=3** in llama.cpp's temp-last order. Anyone
   quoting "min_p keeps T=3 coherent" is quoting a regime in which the survivor set is ~20×
   wider in probability than yours.

So in the stream's stack **min_p is the strangeness dial, and temperature only decides how evenly
the survivors get chosen.** Why OLMo "at 2.0–2.4 reads like nemo at 1.2" has a mechanical
suspect: a sharper 32B puts fewer tokens within 2.53 nats of its top choice, so at the same
min_p it has fewer survivors per fork. That's checkable in one request (§2, experiment S0).

Your own baseline, measured from the 212 nemo stream pages on the shelf (their `meta.logprobs`
are the **raw, T=1** logprob of each chosen token, since `n_probs` without `post_sampling_probs`
reports the plain softmax, `server-context.cpp populate_token_probs`): **2.86 bits per token (page
sd 0.62), mean chosen-token probability 0.32, median 0.15; 12% of tokens had p>0.9, 28% had
p<0.05.** That's the number the surprise-targeting samplers below can be set to, and it's the
yardstick for S1.

## (a) The samplers, one by one

### min_p and typical_p as floors; `--samplers` order

- **Mechanic.** min_p: keep tokens with `p ≥ min_p·p_max`, the fixed logit gap above. typical_p:
  keep the tokens whose surprisal is closest to the distribution's entropy, up to mass p. In
  llama.cpp both run before temperature by default, so both are computed on the raw
  distribution.
- **Feel.** p-e-w: *"A Min-P value of 0.02 typically retains 5-10 tokens, amounting to 95%-99+% of
  the total probability mass. This implies that around once every two or three sentences, this
  value prevents garbage from the long tail being sampled … I've run unconstrained many times,
  and it was always immediately obvious."* (r/LocalLLaMA 1ev8n2s, 2024-08-19).
- **Dial and cliff.** The cliff is at the *furniture* positions (the mid-word and grammatical
  tokens where the model is near-certain), not at the forks. Worked example: a mid-word position
  with top 0.97 and a 2% alternative. At min_p 0.08 the alternative is cut; at min_p 0.02 it
  survives, and with temperature last it gets 13% of the draws at T2, 22% at T3, 32% at T5. **That's
  the sampler-side slur**: misspellings and broken words, because heat reached the positions
  that were never forks. Raising the floor protects the furniture. Lowering it lets heat in
  everywhere at once.
- **Order matters at T 3+** because the order decides whether truncation happens on the raw
  distribution (predictable) or on the flattened one (at T 5, temp-first min_p would keep
  everything within 5·2.53 = 12.6 nats: salad). Keep `temperature` last. typical_p adds nothing
  for us over min_p: it's a mass-based cut, and at a fork on a sober model it keeps roughly the
  same few tokens.
- **Availability.** `--min-p`, `--typical`/`--typical-p`, `--samplers "a;b;c"` or
  `--sampler-seq` (chars `e d s k y p m x t a`). Per request: `min_p`, `typical_p` (note: the
  JSON key is `typical_p`, the sampler-list name is `typ_p`), `samplers` (array of names or a
  char string).
- **Bet.** min_p is the real strangeness dial in the current stack. Sweep it (0.08 → 0.05 → 0.03)
  at a *fixed* moderate T (1.5), because at T≥3 you're measuring nothing new.

### top-nσ (top-n-sigma)

- **Mechanic.** Keep tokens with `logit ≥ max − n·σ`, σ being the standard deviation of *all*
  logits (the whole ~100k vocab), computed before temperature. Temperature invariance follows
  from the algebra (the paper: *"l_i/T ≥ M/T − nσ/T ⟺ l_i ≥ M − nσ. This final condition is
  independent of T"*). The llama.cpp implementation (`llama_sampler_top_n_sigma_apply`) is exactly
  this.
- **What it really is, for us.** Structurally it is min_p with an **adaptive gap**: min_p's gap is
  fixed at `ln(1/m)`, top-nσ's is `n·σ` of the current position's logits. Under temperature-last
  ordering both are temperature-invariant anyway, so **top-nσ's headline advantage buys llama.cpp
  users nothing they don't already have with min_p before temperature.** Its advantage is only
  relevant in stacks that apply temperature first (HF, vLLM), which is where the paper measured
  it. What it does add is the adaptive gap: where the logit cloud is wide (σ large), it admits
  more.
- **Reported feel.** The paper tests reasoning only (GSM8K, GPQA, AQuA, MATH), Llama-3-8B-Instruct,
  temperatures up to 3.0: *"at temperature 3.0, while standard sampling and top-p completely fail
  on GPQA and GSM8K, our method still achieves 25.00% and 74.61% accuracy respectively."* The
  authors' README: *"any value between 0.3 and 1.5 could work well … If you prefer conservative
  sampling, use a lower value like 0.7; for more diversity, try 1.3"* and *"you don't need to
  worry about temperature wielding top-nsigma."* No creative-writing or base-model report was
  found (see (e)).
- **Dial and cliff.** n (paper: *"we recommend constraining n larger than 0.5"*; theoretical range
  (0, 2√3)). With T large, n *is* the strangeness dial, like min_p. The cliff is the same:
  where the gap starts admitting furniture alternatives.
- **Availability.** llama.cpp mainline since 2025-02-13 (PR #11223, VJHack). `--top-nsigma` /
  `--top-n-sigma N`, `-1` = off; per request `"top_n_sigma"` (accepted by the schema, **not
  documented in the README's /completion list**); sampler name `top_n_sigma`, char `s`. It sits
  third in the default chain, so setting it >0 turns it on in place.
- **Bet.** It's worth one A/B against min_p at T 3 (n 1.0 vs min_p 0.08), because the adaptive gap
  might treat OLMo's forks differently from its furniture. Don't expect a different weather.

### XTC (exclude top choices)

- **Mechanic.** With probability `xtc_probability`, find every token with `p ≥ xtc_threshold`.
  If there are at least two, remove all of them except the *least* likely one
  (`llama_sample_xtc_apply`: the `pos_last > 0` condition). A position with a single dominant
  token is **untouched**. That makes it the only stock sampler whose intervention is structurally
  **fork-only**: furniture passes through, forks lose their favourite. In llama.cpp it runs
  before temperature, on probabilities renormalized over the min_p survivors.
- **Feel.** p-e-w, the author: *"it removes all except the least likely token meeting a given
  threshold, with a given probability. This ensures that at least one 'viable' choice remains,
  retaining coherence … My experience so far has been that this gives spectacular results. The
  creativity is off the charts, while the coherence is virtually unchanged."* (TGWUI PR #6335,
  2024-08-18). And the line that matters for OLMo: *"we should expect 'better' models to become
  more and more certain about their predictions, and react more and more violently to sampling
  intervention"* (r/SillyTavernAI 1fjwlmr, 2024-09-19). Users: *"XTC increases creative writing,
  but makes some models noticeably dumber in logic, confusing facts from previous context and
  straight out making things out of nowhere. At least with nemo-based 12b models."* (hardeh,
  same thread); *"It also produced some incoherence in a few messages, where the choice it made
  simply made no sense in light of the context"* (a_beautiful_rhind, 72B, 1ev8n2s);
  *"Too much XTC and sentences might start lowercased"* (Inside-Due, 1fjwlmr). MaggotHATE, who
  ported it to llama.cpp: *"With larger models XTC may require very careful choice of
  parameters"* (PR #9742).
- **Dial and cliff.** Threshold = how deep (lower = more positions count as forks, and the kept
  token is less likely); probability = how often. p-e-w's range: threshold 0.05–0.2, probability
  0.2–1.0. The cliff shows up as *"misspelled names or wildly varying message lengths"* at low
  threshold (p-e-w, r/SillyTavernAI 1g4r12r), which means threshold low enough that sub-word
  splits count as forks.
- **The OLMo problem.** On a sharp model most positions have exactly one token ≥ 0.1, so XTC
  at 0.1 is a no-op most of the time. That's likely why your t3.0/t5.0 + xtc 0.5/0.1 run read
  sober. The lever is threshold **0.05** and probability **1.0**.
- **Availability.** llama.cpp mainline since 2024-10-15 (PR #9742). `--xtc-probability`,
  `--xtc-threshold` (>0.5 disables); per request `xtc_probability`, `xtc_threshold`; name `xtc`,
  char `x`.
- **Bet.** The best stock tool for "strange at forks, sane in furniture". On OLMo it has to be run
  at threshold 0.05 / probability 1.0 with min_p ≥ 0.05 in front. It will change *which* sensible
  thing arrives, and it won't change the weather (see (b)).

### adaptive-p (new since the brief was written — the one sampler that targets a surprise budget)

- **Mechanic.** Merged into llama.cpp 2026-01-15 (PR #17927, ddh0, after MrJackSpade's "power
  law" sampler). It keeps an EMA of the *original* probability of each chosen token, computes
  `adapted_target = clamp(2·target − EMA, 0, 1)`, and re-logits every candidate as
  `5 − 10·d²/(1+d)` with `d = |p − adapted_target| / 0.3`, then samples. After a run of
  near-certain furniture tokens the EMA sits high, the adapted target drops toward 0, and at the
  next real fork it **prefers the low end of the survivors**. It's a surprise budget: the base
  model's furniture "saves" surprise and the forks "spend" it. It must be last in the chain and
  it replaces `dist`.
- **Feel.** Author docs: *"A target of 0.5 means the sampler prefers tokens that the model
  considers 'plausible but not dominant.' A target of 0.3 encourages more surprising choices."*
  On the limit that matters for us, verbatim: *"Adaptive-P cannot create choices that don't
  exist. It operates on the candidates provided by earlier pipeline stages."* Failure modes named
  by the authors: *"Stubbornness (decay too high): … If the first 50 tokens happened to be
  high-probability forced choices, the sampler stubbornly tries to compensate by targeting very
  low probabilities for the next 50"*, and *"Fishtailing (decay too low): … After one
  high-probability selection, it swings hard toward low probability."* Their target-0.3 sample
  on GLM-4.5-Air: *"My blood turns to icy slurry as a cold draft, utterly impossible in the humid
  heat, sweeps over the nape of my neck."* That's odder diction inside the same horror-story
  weather. The TGWUI issue calls it *"great for creative writing"* (users, unquantified).
  Uptake: koboldcpp 1.105.2, ExLlamaV3, TGWUI v4.0.
- **Dial and cliff.** `target` 0–1 (author start 0.55, "creative" 0.3), `decay` 0–0.99 (0.9 ≈ 10
  tokens of memory). They recommend min_p 0.03 in front for creative writing, and temperature off
  or mild (*"Very high temperature flattens distributions enough that 'mid-range' becomes
  ambiguous"*). Our calibration: nemo's stream pages average a chosen-token p of **0.32**. A
  target around 0.3 on OLMo therefore asks OLMo to be *as surprising per token as nemo's stream*,
  which makes it the cleanest instrument for S1. The cliff: a base model's EMA is dominated by
  p≈1 furniture, so a target far below the model's natural average turns into "always the
  lowest survivor at every fork". That's stubbornness, and it shows as a thesaurus voice.
- **Availability.** `--adaptive-target N` (negative = off), `--adaptive-decay N`; per request
  `adaptive_target`, `adaptive_decay` (schema-accepted; the schema's own description says
  "target entropy", which is wrong, since it's a probability). It only activates if `adaptive_p`
  is in the `samplers` list: `"samplers": ["penalties","dry","min_p","adaptive_p"]`.
- **Bet.** First thing to try, because it's the only stock sampler whose dial is in units you
  already measure (chosen-token probability), so a blind nemo-vs-OLMo comparison can be run at
  *matched surprise*.

### mirostat v1/v2 (tau, eta)

- **Mechanic.** v2 (`llama_sampler_mirostat_v2_apply`): cut every token whose surprise
  `−log2 p > μ`, sample, then `μ ← μ − η·(observed − τ)`, starting from μ = 2τ. **τ is in bits per
  token.** Like adaptive-p it's a surprise budget with feedback: near-certain tokens return ~0
  bits, so μ climbs and the next fork may go deep.
- **Feel.** The paper names the two traps it steers between: restrictive settings where
  *"perplexity drops significantly with generated text length, which is also correlated with
  excessive repetitions"* (the boredom trap), and permissive ones where *"perplexity increases with
  generated text length, which is correlated with incoherence"* (the confusion trap) (Basu et al.,
  ICLR 2021). The scene's verdict is mostly negative. turboderp (ExLlama): *"it turns out that with
  the parameters people were recommending (and using), it was doing literally nothing--except
  that turning it on also disabled all the other samplers."* p-e-w: *"the samplers with the
  strongest theoretical foundation (Mirostat and Eta-sampling) have not stood the test of human
  preference"* (both 1ev8n2s, 2024-08).
- **τ 8–12 on a base model, by arithmetic** (nobody has published it, see (e)): nemo's *hot*
  stream pages already average **2.86 bits/token** raw. τ 8 asks for an average token
  probability around 1/256, and τ 12 for one around 1/4096, i.e. far below the tail that
  min_p 0.08 would even allow. That's salad by construction. The meaningful range for us is
  **τ 2.5–4**.
- **Trap, llama.cpp-specific.** In mirostat mode the chain is only `logit_bias → temp →
  mirostat` (`sampling.cpp`, `params.mirostat == 1/2` branches). **DRY, the repeat penalty,
  min_p, XTC and top-nσ are all silently skipped.** On a base model that loops, that's a real
  cost.
- **Availability.** `--mirostat 1|2`, `--mirostat-lr` (η), `--mirostat-ent` (τ); per request
  `mirostat`, `mirostat_tau`, `mirostat_eta`.
- **Bet.** Superseded for us by adaptive-p, which does the same budget trick *after* min_p and
  keeps DRY. Use mirostat v2 only as a cross-check at τ≈2.9 (nemo-matched), η 0.1.

### Dynamic temperature (dynatemp_range, dynatemp_exponent)

- **Mechanic** (`llama_sampler_temp_ext_apply`, which is the entropy-power version, not
  kalomaze's later HHI one): `T = (T0−Δ) + 2Δ·(H/H_max)^exp`. H is the entropy of the *current
  candidates* and **H_max = ln(number of candidates)**. With temperature last, both are measured
  on the min_p survivors. A position with one survivor returns immediately (untouched). A fork
  with three survivors at 0.4/0.35/0.25 has normalized entropy ≈0.98 and gets nearly the max
  temperature. In practice it is already "calm in the furniture, hot at the forks", and
  min_p-first already does most of that work, because furniture positions usually have one
  survivor.
- **Feel.** kalomaze's motivation, verbatim: *"higher temperatures disproportionately impact high
  confidence token generations. This is especially a problem for weaker language models that
  have less of an innate ability to 'course correct' when an awkward/bad token is chosen"*
  (rentry.org/dynamic_temperature, 2023-10/11). On the older top-token variant: *"I've been told
  it follows the character better but can struggle with repetition."* In the llama.cpp PR
  (#4972): the exponent *"has made larger dynatemp ranges (1-5) useful while remaining
  coherent"*.
  kalomaze himself (as kindacognizant), on dynatemp after min_p: *"it (in theory?) should be
  measuring the entropy post-truncation … I also like the entropy sampling but I'm not sure how
  much of it was placebo on my part because Min P already does a pretty good truncation job"*,
  and relaying a user: for 70b models it *"felt 'distinctly less mechanical', whatever that means"*
  (r/LocalLLaMA 180b673, 2023-11-21). Without a floor, per the same author: *"the Entropy
  measurements will trend very low (so it'll be 0.3-0.5 temp range effectively)"*.
- **Dial and cliff.** Range Δ and exponent. The exponent >1 pushes all but the flattest forks
  toward T0−Δ. The cliff is identical to plain temperature over the same survivors, since dynatemp
  can't reach tokens min_p removed.
- **Availability.** `--dynatemp-range`, `--dynatemp-exp`; per request `dynatemp_range`,
  `dynatemp_exponent`. It lives inside the `temperature` sampler.
- **Bet.** Low value on top of min_p-first. It's the stock form of scheduled heat, but in our order
  the truncation already does the scheduling.

### Scheduled heat beyond dynatemp (literature; nothing else in llama.cpp)

- **EDT** (Zhang, Bao, Huang, 2024, arXiv 2403.14541): per-token `T = τ·α^(θ/H)`, entropy-driven,
  evaluated on summarization/QA/translation. **Hot or Cold** (arXiv 2309.02772, the paper
  llama.h cites for `temp_ext`): hot at "challenging tokens", cold elsewhere, for code.
  **Selective sampling** (Troshin et al., 2025, arXiv 2510.01218) *"dynamically switches between
  greedy and high-temperature sampling based on a sampling risk metric"* from a trained
  classifier. **Top-H** (arXiv 2509.02510) bounds entropy per step and claims it beats min-p *"by
  up to 25.63% on creative writing benchmarks"*.
- None of them schedules by *position in the page*, and none is in llama.cpp. They're all "calm
  where the model is sure, hot where it isn't", which on our stack min_p-first plus XTC or
  adaptive-p already implements. A *position* schedule (calm for the first N tokens, hot after)
  would be a client-side trick: two `/completion` calls, the second continuing the first's text
  with different sampler JSON. With `cache_prompt` it costs almost nothing. No patch needed.

### entropix (xjdr)

- **Mechanic.** Per token, compute entropy and varentropy of the logits (and attention
  statistics). Low/low → argmax. High entropy + low varentropy → insert a "thinking" token (id 2564
  in the Llama-3 tokenizer) to buy time. Low entropy + high varentropy → branch/raise heat.
  High/high → resample hotter. The README's own warning: *"HERE BE DRAGONS!!!! THIS IS NOT A
  FINISHED PRODUCT AND WILL BE UNSTABLE AS HELL RIGHT NOW."*
- **Feel.** Built and marketed for *reasoning* (small Llamas "thinking longer"), not prose. The
  Manifold market "Will entropy-based sampling improve Llama3.1 on reasoning benchmarks in 2024?"
  resolved **NO** (*"Seeing no other posted evidence, I am resolving this NO"*). No base-model
  prose reports found.
- **llama.cpp.** Not ported. There is a discussion, #9831 "Add Shrek (entropix) Sampler"
  (2024-10-10, zero replies), and a fork by FeepingCreature (entropix issue #16, "AI generated
  code"), whose own verdict is: *"This is probably an architectural dead end though. I don't think
  llama.cpp's sampling code can architecturally support any sort of beam/tree search even in
  principle; the sampler only ever sees the next logits."* The token-injection branch and the
  attention-entropy signal both need access the sampler API doesn't have. It lives in JAX/torch
  (xjdr-alt/entropix), MLX (smoltropix, entropix_mlx) and ollama-entrapix.
- **Bet.** Skip. Its only prose-relevant idea (heat keyed to entropy) is dynatemp. Its novel
  idea (inject a token when confused) is a steering move, which is the opposite of what we want.

### DRY / repeat penalty as the brake at high heat

- **Mechanic.** DRY penalizes a token that would extend a verbatim repeat of an earlier
  sequence: `multiplier·base^(len−allowed)`. The repeat penalty divides the logits of every token seen
  in the last n. In the default chain both run **first**, before the truncation, so they change
  which tokens survive.
- **Interaction.** At high T with min_p-first, DRY is what stops a hot page from becoming one
  sentence nine times (your own `stream.py` note). The flat repeat penalty is the one that hurts:
  turboderp, *"Repetition penalties cause thesaurus mode"* (1ev8n2s). With `repeat_last_n 512`
  it penalizes every function word already on the page, which pushes the furniture into
  synonyms. That's a slur channel unrelated to heat. Keep DRY; consider dropping `repeat_penalty`
  to 1.0 on OLMo, since a 32B loops less. Mirostat mode drops DRY entirely (above).
- **Availability.** `--dry-multiplier/-base/-allowed-length/-penalty-last-n/-sequence-breaker`,
  `--repeat-penalty/-last-n`, `--presence-penalty`, `--frequency-penalty`; per request the same
  names in snake_case plus `dry_sequence_breakers` (array). Note that **the README says
  `repeat_penalty` defaults to 1.1; the code default is 1.00** (`common.h`).

### Logit noise

Sampling at temperature T *is* Gumbel-max on logits/T, so i.i.d. per-token logit noise is
temperature by another name and adds nothing. (llama.cpp's `add_gumbel_noise` flag belongs to the
diffusion-model params, not to autoregressive sampling.) What would be new is noise
**correlated across the page**: one random bias vector drawn per page and held fixed for all 170
tokens. That's the one sampler-side move that looks like the brief's "different weather", and
it's possible today through `logit_bias` (§(b) end, experiment S2). No one has reported it (see
(e)).

## (b) Where the sampler stops and the weights have to change

The argument, in three steps, each with a source.

**1. A sampler can only re-rank what the model already ranks near the top, and on a good model that
set is sober.** Every sampler above works on the model's own candidate list at one position.
adaptive-p's authors say it flat out: *"Adaptive-P cannot create choices that don't exist."*
Past the few-nats neighbourhood of the top token, validity and rank decouple: *"valid tokens are
not reliably ranked above invalid tokens … the relationship between rank and validity is neither
monotone nor stable across contexts,"* so *"no decoding method that relies on top-token filtering
can effectively recover diversity"* and *"raising the temperature can indeed move probability mass
toward this tail, but the invalid sequence mass dominates"* (Banayeeanzade et al., "Sampling More,
Getting Less: Calibration is the Diversity Bottleneck in LLMs", 2026). The long line behind it:
*"This unreliable tail is composed of tens of thousands of candidate tokens with relatively low
probability that are over-represented in the aggregate"* (Holtzman et al. 2019). And on what heat
actually buys in narrative: *"temperature is weakly correlated with novelty, and unsurprisingly,
moderately correlated with incoherence, but there is no relationship with either cohesion or
typicality"* (Peeperkorn et al. 2024). So the sampler has two regions to work in. Inside the
sensible neighbourhood it picks the 3rd-best sensible thing, which is the sober weather again.
Past the edge it picks noise, which is the slur. There's no third region where "strange but valid"
is concentrated, because the model doesn't rank strange-but-valid above noise.

**2. Per-token sampler strangeness is white noise, and a good model heals white noise.** Each
sampled token is an independent perturbation of the context, and the model then conditions on it.
Autoregressive models recover: *"the distortion induced by the prefix discrepancy is limited, and
does not seem to be incremental during the generation … our analysis reveals an interesting
self-recovery ability of the LM"* (He et al., EMNLP 2021). kalomaze frames the same thing as
strength: weaker models *"have less of an innate ability to 'course correct' when an awkward/bad
token is chosen."* EGjoni saw it inside the network: *"we can add quite a lot of noise in earlier
layers and the model very quickly drowns that noise out with its own signal"* (DRµGS README). This
is the likely reason nemo dreams and OLMo doesn't under the same sampler. **Nemo's lightning
comes from failures to heal**: a misread frame that the model then keeps misreading, which is a
*correlated* error. OLMo reads the odd token as a typo in a sane document and gets back on the road
within a sentence. Your t5.0 page is a heal in action: "the telephone lines look strange too. but
then we've all gone" drifts, and then the parish-hall memoir takes over again.

**3. So the boundary is correlation, not dose.** Anything the sampler does independently per token,
a strong model averages away. What survives the healing is a perturbation applied *the same way at
every position of the page*: a fixed direction in the residual stream, a fixed weight change,
or, as the sampler-side edge case, a fixed bias over the vocabulary. That's where the weights (or
activations) have to change: not to add more noise, but to make the noise **the same noise for 170
tokens**, so the model can't treat it as a typo and has to make sense of it. That's the brief's
"weather" in mechanical terms.

**The sampler-side edge case (my proposal, not found in the literature): a per-page random logit
bias shaped by the unembedding.** Draw a random unit vector `v` in the 5120-dim residual space,
compute `b = s · W_U v` (W_U = `output.weight`, 100 278 × 5120), standardize it, and send it as
`logit_bias` for the whole page. Tokens whose output embeddings point the same way get pushed
together, so it's a random *semantic* tilt, not a lexical one. It's exactly what a random control
vector would do if it were added after the final norm. It's held fixed for the page, so it can't be
healed. It changes per request with no restart (`logit_bias` accepts `[[id, bias], …]` of any
length, `server-schema.cpp`; it's applied first in the chain, before min_p, so it changes which
tokens survive). The dose to try is `s` such that the bias sd is 0.5 / 1 / 2 nats. The cliff is
expected when the sd approaches min_p's gap (2.5 nats), where the furniture starts to flip. Its
limit: it only acts on the output, so the model's internal state isn't tilted, only its choices
are. If S2 shows a flavour, the in-network version (random control vector, other reports) is the
next rung.

## (c) llama.cpp inventory (master `d2e5458`, 2026-09-23)

"Req" = settable per `/completion` request without restart.

| Thing | CLI flag | `/completion` key | Req | Notes (exact) |
|---|---|---|---|---|
| sampler order | `--samplers "penalties;dry;top_n_sigma;top_k;typ_p;top_p;min_p;xtc;temperature"`, `--sampler-seq edskypmxt` | `samplers` (array of names or char string) | yes | Names: `dry top_k top_p top_n_sigma typ_p min_p temperature xtc infill penalties adaptive_p` (aliases `nucleus`, `temp`, `typ`). A listed sampler repeats if listed twice; an unlisted one is off. README's default list is stale (omits `penalties`, `top_n_sigma`). |
| temperature | `--temp` | `temperature` | yes | default 0.8; applied last by default |
| min_p | `--min-p` | `min_p` | yes | logit-gap cut `max + ln p`; default 0.05 |
| top_k / top_p | `--top-k`, `--top-p` | `top_k`, `top_p` | yes | defaults 40 / 0.95 — set `top_k 0`, `top_p 1.0` to get them out of the way |
| typical | `--typical` | `typical_p` | yes | 1.0 = off |
| top-nσ | `--top-nsigma` / `--top-n-sigma` | `top_n_sigma` | yes | −1 off; schema-accepted, missing from README |
| XTC | `--xtc-probability`, `--xtc-threshold` | `xtc_probability`, `xtc_threshold` | yes | threshold >0.5 disables |
| dynatemp | `--dynatemp-range`, `--dynatemp-exp` | `dynatemp_range`, `dynatemp_exponent` | yes | entropy over current candidates, normalized by ln(count) |
| mirostat | `--mirostat 0/1/2`, `--mirostat-lr`, `--mirostat-ent` | `mirostat`, `mirostat_eta`, `mirostat_tau` | yes | τ in bits; **bypasses DRY, penalties, min_p, xtc, top-nσ** |
| adaptive-p | `--adaptive-target`, `--adaptive-decay` | `adaptive_target`, `adaptive_decay` | yes | only active if `adaptive_p` is in `samplers`; always runs last; merged 2026-01-15 |
| DRY | `--dry-multiplier`, `--dry-base`, `--dry-allowed-length`, `--dry-penalty-last-n`, `--dry-sequence-breaker` | `dry_multiplier`, `dry_base`, `dry_allowed_length`, `dry_penalty_last_n`, `dry_sequence_breakers` | yes | defaults 0 / 1.75 / 2 / 64 |
| repetition | `--repeat-penalty`, `--repeat-last-n`, `--presence-penalty`, `--frequency-penalty` | `repeat_penalty`, `repeat_last_n`, `presence_penalty`, `frequency_penalty` | yes | code default 1.00 (README says 1.1) |
| logit bias | `-l TOKEN_ID(+/-)BIAS` | `logit_bias`: `[[id, bias], …]`, `[["text", bias]]`, or `{"id": bias}`; `false` bans | yes | no length limit in the parser; applied first in the chain |
| probabilities out | — | `n_probs` (alias `logprobs`), `post_sampling_probs` | yes | pre-sampling = **raw T=1 softmax over the full vocab** (natural-log `logprob`); `post_sampling_probs: true` returns `prob` of the survivors after the chain — the count of returned entries (with n_probs ≥ 50) is the survivor count per position. Entropy per position ≈ from `top_logprobs` with n_probs 20–50 (truncated estimate). |
| seed | `-s` | `seed` | yes | |
| backend sampling | `-bs, --backend-sampling` | `backend_sampling` | yes | experimental, on-GPU sampling; irrelevant for us |
| control vectors | `--control-vector FNAME`, `--control-vector-scaled FNAME:SCALE,...`, `--control-vector-layer-range START END` | — | **no** | load-time only in the server (no endpoint, no request key; grep of `tools/server` finds nothing). The C API has `llama_set_adapter_cvec()` for runtime change, so a per-request cvec is a small server patch. File: gguf with F32 tensors `direction.<layer>` (1-based; layer 0 is rejected), each `n_embd` long; added to that layer's output (residual stream). Multiple files are summed with their scales. |
| LoRA | `--lora FNAME[,…]`, `--lora-scaled FNAME:SCALE,...`, `--lora-init-without-apply` | `lora: [{"id":0,"scale":0.5}, …]` | **yes** | Per request: listed adapters take the given scale, **unlisted adapters default to 0.0**; a changed LoRA set **clears the slot's KV cache** (`lora_should_clear_cache`; aLoRAs excepted), so the prompt is re-processed with the new weights, which is correct for us and costs one prefill and isn't batched with other configs. Global without restart: `POST /lora-adapters` `[{"id":0,"scale":…}]`, `GET /lora-adapters` for ids. Format: gguf with `general.type = "adapter"`, `general.architecture` = the model's arch (**`olmo2` for OLMo 3**, since llama.cpp maps Olmo3ForCausalLM to the olmo2 arch), `adapter.type = "lora"`, `adapter.lora.alpha` (f32); tensors `<model tensor name>.lora_a` / `.lora_b` (e.g. `blk.12.ffn_down.weight.lora_a`), shape-checked against the model; effective scale = `scale·alpha/rank`. `convert_lora_to_gguf.py` makes one from a PEFT dir; a random untrained one can be written directly with gguf-py. **This is the only stock way to change the *weights* per request, and to draw a fresh perturbation per page (load k random LoRAs, pick one + a scale per request).** Size for OLMo 3 32B at rank 8 on all seven linear families: ≈1.05 M params/layer × 64 ≈ 67 M params ≈ 134 MB f16 each. |
| RoPE | `--rope-freq-base N`, `--rope-freq-scale N`, `--rope-scale N` (=1/scale), `--rope-scaling {none,linear,yarn}`, `--yarn-orig-ctx`, `--yarn-ext-factor`, `--yarn-attn-factor`, `--yarn-beta-slow`, `--yarn-beta-fast` | — | no | **OLMo 3 caveat, from `src/models/olmo2.cpp`:** the 48 sliding-window layers call `ggml_rope_ext(..., freq_base, 1.0, 0.0, 1.0, ...)`, i.e. **`--rope-freq-scale` touches only the 16 full-attention layers (every 4th)**; `--rope-freq-base` reaches all 64. Trained values: `rope_theta 500000`, `rope_scaling null`, `sliding_window 4096`, `max_position_embeddings 8192`. Read the `olmo-rope-scale-0.5` pages with that in mind. |
| attention temperature | — | — | no | **No flag.** OLMo 3 has QK-norm (`attn_q_norm.weight`, `attn_k_norm.weight`, F32, per layer); scaling `attn_q_norm.weight` by s scales every attention logit in that layer by s. That's a gguf file edit on 64 small vectors, not a patch. The softmax scale is hard-coded `1/sqrt(head_dim)` in the olmo2 graph, and `attention.scale` isn't read for this arch. |
| KV cache types | `-ctk/--cache-type-k`, `-ctv/--cache-type-v` | — | no | allowed: `f32, f16, bf16, q8_0, q4_0, q4_1, iq4_nl, q5_0, q5_1`; a quantized V cache requires flash attention (auto-enabled if possible). `q4_0` is the only built-in "KV noise" dial. |
| metadata override | `--override-kv KEY=TYPE:VALUE,...` | — | no | Types `int, float, bool, str` (str ≤127 chars, key <128). **No arrays**, so per-layer arrays (e.g. the SWA pattern) can't be overridden. Common arg, works for `llama-server`. For OLMo 3 the scalars that are actually read: `olmo2.attention.layer_norm_rms_epsilon` (float, trained 1e-6: a uniform, free perturbation of every RMSNorm), `olmo2.attention.sliding_window` (int), `olmo2.rope.freq_base`, `olmo2.context_length` (`olmo2.rope.freq_base_swa` is read into hparams, but the olmo2 graph ropes every layer with the context-wide `freq_base`, so it does nothing here). `block_count` can't be lowered: the loader aborts with "wrong number of tensors". |
| tensor override | `-ot/--override-tensor PATTERN=BUFTYPE,...` | — | no | **Buffer placement only** (which device holds the tensor), **not values**. Can't be used to perturb weights. |
| layer skipping | — | — | — | **None.** No skip/early-exit/repeat flag in `common/`, `src/`, `tools/server/` (grep for skip/early-exit/layer patterns: empty). Layer tampering = gguf surgery or a patch. |
| diffusion noise | `add_gumbel_noise` in diffusion params | — | — | diffusion LLMs only, not autoregressive |

## (d) Sources

- *paper* — Tang, Liu, Xu, Huang, "Top-nσ: Not All Logits Are You Need", arXiv 2411.07641 (2024-11). *"logits naturally separate into a Gaussian-distributed noisy region and a distinct informative region"*; *"Unlike existing methods (e.g., top-p, min-p) that inadvertently include more noise tokens at higher temperatures, top-nσ maintains a stable sampling space regardless of temperature scaling"*; *"at temperature 3.0, while standard sampling and top-p completely fail on GPQA and GSM8K, our method still achieves 25.00% and 74.61% accuracy respectively"*. https://arxiv.org/abs/2411.07641 ; code https://github.com/Tomorrowdawn/top_nsigma
- *scene* — VJHack, llama.cpp PR #11223 "sampling: add Top-nσ sampler", merged 2025-02-13. https://github.com/ggml-org/llama.cpp/pull/11223
- *scene* — p-e-w, TGWUI PR #6335 "Exclude Top Choices (XTC)", 2024-08-18 (quotes in (a)). https://github.com/oobabooga/text-generation-webui/pull/6335
- *scene* — MaggotHATE, llama.cpp PR #9742 "sampling : add XTC sampler", merged 2024-10-15: *"XTC improves creativity greatly, but may break models in specific cases … With larger models XTC may require very careful choice of parameters"*. https://github.com/ggml-org/llama.cpp/pull/9742
- *forum* — r/LocalLLaMA "Exclude Top Choices (XTC): A sampler that boosts creativity…", 2024-08-18, comments by cynerva, -p-e-w-, a_beautiful_rhind, ReturningTarzan (quotes in (a)/(b)). https://reddit.com/r/LocalLLaMA/comments/1ev8n2s/
- *forum* — -p-e-w-, r/SillyTavernAI "How to use the Exclude Top Choices (XTC) sampler, from the horse's mouth", 2024-10-16: *"XTC reduces compliance with the prompt … 'Be creative' and 'do as I say' are opposites"*; *"With low threshold values and certain finetunes, XTC can sometimes produce artifacts such as misspelled names or wildly varying message lengths."* https://reddit.com/r/SillyTavernAI/comments/1g4r12r/
- *forum* — r/SillyTavernAI "Now that the dust has settled how are you finding the XTC and DRY samplers?", 2024-09: -p-e-w- (*"react more and more violently to sampling intervention"*), hardeh, Inside-Due, GraybeardTheIrate (*"Every now and then I get a word or two that don't make much sense in context or used in an unusual way, and I think XTC is to blame"*). https://reddit.com/r/SillyTavernAI/comments/1fjwlmr/
- *scene* — ddh0, llama.cpp PR #17927 "implement adaptive-p sampler", merged 2026-01-15; MrJackSpade, adaptive-p docs (quotes in (a)). https://github.com/ggml-org/llama.cpp/pull/17927 ; https://github.com/MrJackSpade/adaptive-p-docs ; uptake: https://github.com/oobabooga/text-generation-webui/issues/7362
- *forum* — kindacognizant (kalomaze), r/LocalLLaMA "I need people to test my experiment - Dynamic Temperature", 2023-11-21 (quotes in (a)). https://reddit.com/r/LocalLLaMA/comments/180b673/
- *scene* — kalomaze, "Dynamic Temperature Sampling (for better Creativity & Coherency in Large Language Models)", rentry, 2023-10-14 / 2023-11-03 (quotes in (a)). https://rentry.org/dynamic_temperature ; port: l3utterfly, llama.cpp PR #4972, merged 2024-01-25. https://github.com/ggml-org/llama.cpp/pull/4972
- *paper* — Basu, Ramachandran, Keskar, Varshney, "Mirostat: A Neural Text Decoding Algorithm that Directly Controls Perplexity", arXiv 2007.14966 (boredom/confusion trap quotes in (a)). https://arxiv.org/abs/2007.14966
- *paper* — Nguyen et al., "Turning Up the Heat: Min-p Sampling for Creative and Coherent LLM Outputs", ICLR 2025, arXiv 2407.01082: practitioners can *"experiment with higher temperatures (e.g., τ=2 or τ=3) to enhance diversity without significant loss of coherence"* (temperature-first order; see §0 for the conversion). https://arxiv.org/abs/2407.01082
- *paper* — Schaeffer et al., "Min-p, Max Exaggeration: A Critical Analysis of Min-p Sampling in Language Models", arXiv 2506.13681 (2025): all samplers perform roughly the same at equal tuning; min-p's weak edge is at high temperature, *"with the critical caveat that absolute performance is meaningfully worse in this high-temperature regime"* (search-result summary of the conclusion; not re-read verbatim from the PDF). https://arxiv.org/abs/2506.13681
- *paper* — Holtzman, Buys, Du, Forbes, Choi, "The Curious Case of Neural Text Degeneration", ICLR 2020, arXiv 1904.09751: *"This unreliable tail is composed of tens of thousands of candidate tokens with relatively low probability that are over-represented in the aggregate"*; *"Natural language rarely remains in a high probability zone for multiple consecutive time steps, instead veering into lower-probability but more informative tokens."* https://arxiv.org/abs/1904.09751
- *paper* — Peeperkorn, Kouwenhoven, Brown, Jordanous, "Is Temperature the Creativity Parameter of Large Language Models?", arXiv 2405.00492 (2024) (quote in (b)). https://arxiv.org/abs/2405.00492
- *paper* — Banayeeanzade et al., "Sampling More, Getting Less: Calibration is the Diversity Bottleneck in LLMs", arXiv 2605.11128 (2026-05) (quotes in (b), via the HTML version's §4–5). https://arxiv.org/abs/2605.11128
- *paper* — Awad et al., "Lost in Sampling: Assessing Lexical Reachability in LLMs via the Word Coverage Score", arXiv 2605.27268 (2026): *"industry-standard sampling defaults act as unintended censorship mechanisms, smoothing the unique textures of human expression into a homogenized discourse."* https://arxiv.org/abs/2605.27268
- *paper* — He, Zhang, Zhou, Glass, "Exposure Bias versus Self-Recovery", EMNLP 2021, arXiv 1905.10617 (quote in (b)). https://arxiv.org/abs/1905.10617
- *paper* — Zhang, Bao, Huang, "EDT: … Entropy-based Dynamic Temperature Sampling", arXiv 2403.14541; Troshin et al., "Control the Temperature: Selective Sampling…", arXiv 2510.01218; Potraghloo et al., "Top-H Decoding…", arXiv 2509.02510.
- *scene* — xjdr-alt/entropix README; FeepingCreature, entropix issue #16 (2024-10-07, quote in (a)); llama.cpp discussion #9831; Manifold market resolution. https://github.com/xjdr-alt/entropix ; https://github.com/xjdr-alt/entropix/issues/16 ; https://github.com/ggml-org/llama.cpp/discussions/9831 ; https://manifold.markets/CharlesFoster/will-entropybased-sampling-improve
- *scene* — EGjoni, DRµGS README (activation-noise "sampler", flagged for the item-3 report): *"Instead of using noise to sample from the model's predictions, DRµGS injects noise directly into the transformer layers at inference time … the model has ample opportunity in its later layers to correct or account for our perturbations in its earlier layers"*; *"something special seems to happen in the middle layers that causes relatively large spikes in output divergence"*; *"the most likely prediction changes, but generally remains reasonable"*; dose: *"You probably shouldn't go past 0.1"* (radians of random rotation). llama.cpp request #4704 was closed by the stale bot unimplemented (2024-04). https://github.com/EGjoni/DRUGS ; https://github.com/ggml-org/llama.cpp/issues/4704
- *forum* — Sabin_Stargem, r/LocalLLaMA 1ev8n2s, 2024-08-18 (for the RoPE report): *"I was trying out all sorts of ROPE settings. Aside from seriously affecting the stability of a model, it sometimes changed the personality. I had Llama-1 become very grimdark … the AI produced an afterlife spa hotel. Unexpected, but interesting and read very nicely."*
- *ours* — nemo stream pages on the shelf (`shelf/sittings/stream/*/*.json`, `meta.logprobs`), 212 pages, computed 2026-09-24; `docs/attic/olmo/olmo-heat-5.0.md`.

## (e) What I could not find

- **Any published base-model prose at top-nσ with T 3–5.** The paper is reasoning-only on an
  instruct model. The scene threads found are about instruct/RP finetunes.
- **Anyone's reading of mirostat τ 8–12.** The τ-in-bits arithmetic (§a) is mine. No quoted
  sample exists.
- **Any entropix port to llama.cpp mainline, or any prose evaluation of entropix.** Only the
  reasoning claims, and a NO-resolved market.
- **A creative-writing or base-model evaluation of adaptive-p beyond its authors' own samples**
  and "users say it's great".
- **Any sampler, paper or fork that schedules heat by position in the document.** Everything
  found schedules by entropy or by a learned risk score.
- **Anyone who has tried a per-page, fixed random logit bias (or its unembedding-shaped version).**
  The S2 idea is untested as far as I can find.
- **Verbatim text of the min-p critique's conclusion**: taken from the search-result summary, not
  re-read in the PDF.
- The reddit archive was rate-limited through most of this session (the other researchers
  were on it too). The XTC (1ev8n2s, 1g4r12r, 1fjwlmr), dynatemp (180b673) and entropix (1geny9l)
  threads were read. The entropix thread has no prose reports, only a benchmark squabble. The
  mirostat threads (136o0wu, 1ph3t27) and the SillyTavern/LocalLLaMA comment searches for
  "nsigma" didn't come back in time.

## The three sampler experiments (each an evening, stock llama-server, no restart between arms)

**S0 — count the survivors (15 minutes, settles "why is OLMo sober").** Same 10 seeds, same
sampler as the stream, on nemo and on OLMo, with `"n_probs": 50, "post_sampling_probs": true`.
Per position, count the returned `top_probs` entries (= survivors after min_p). Verdict: if OLMo's
median survivor count at forks is well below nemo's, the sobriety is (partly) min_p's gap meeting
a sharper model, and a lower min_p on OLMo is a fair comparison, not a cheat. Also log
bits/token (`n_probs: 1`, raw logprob) for OLMo pages and compare with nemo's 2.86.

**S1 — matched surprise (the decisive one).** OLMo with `"samplers": ["penalties","dry","min_p","adaptive_p"], "min_p": 0.03, "adaptive_target": 0.30, "adaptive_decay": 0.9, "dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 3, "repeat_penalty": 1.0, "n_probs": 1`
(no temperature sampler in the list = no temperature at all). Adjust the target in steps of 0.05
until OLMo's pages average **≈2.9 bits/token**, nemo's stream level. Then blind-mix 20 OLMo pages
with 20 nemo stream pages and bekh picks the ghosts. Verdict: if he can't separate them, nemo's
"dream" was its surprise level and no weights need changing. If OLMo at matched surprise still
reads sober (odder words, same weather), the sampler is exhausted, which is my bet, and item 1–6
territory begins. Control arm: the same with `"samplers": [...,"min_p","xtc","temperature"],
"min_p": 0.05, "xtc_threshold": 0.05, "xtc_probability": 1.0, "temperature": 1.5`.

**S2 — correlated bias, the bridge.** Once: dequantize `output.weight` from the Q4_K_M gguf with
gguf-py (`gguf.quants.dequantize`; ~2 GB f32). Per page: random unit `v` (seeded, logged),
`b = W_U v`, standardize, scale to sd `s`, send the top 20 000 |b| as `logit_bias`, on the S1
control sampler. Sweep `s` = 0.5, 1, 2 nats, 5 pages each, plus 5 pages at `s = 0` with the same
seeds. Verdict: read each `s`'s pages as one group. A flavour shared within a page and different
between pages means correlated perturbation survives the heal, and the in-network version
(random control vector / random per-request LoRA) is worth its patch. If it's just word swaps
with no shared flavour, the output layer is too late and the perturbation has to go inside.
