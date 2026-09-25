*translated from the Russian original on 2026-09-26; the answer of an outside model to the mescalito brief.*

**1. Verdict.** I did not find a confirmed recipe for "dose OLMo uniformly and get precisely a dream." But the claim "undirected noise can only damage speech" is too strong: coherent generations under internal perturbations exist, and random weight changes sometimes preserve and even improve individual capabilities. The closest hit to your mechanic is **DRµGS: small random rotations of internal vectors that preserve the norm**. However, the published examples prove diversity, not your "lightning," and there is no ready-made port to OLMo. **As the first probe on your Q4 I would do attention temperature: an identical change in all 64 blocks through Q-norm, starting at τ=1.10.** It is almost free, does not set a topic, and changes the internal attention distribution. The method has a published window of preserved coherence on other models; carrying that window over to OLMo remains an experiment. [DRµGS](https://github.com/EGjoni/DRUGS), [Thermometer of Thoughts](https://aclanthology.org/2026.acl-long.200/), [Neural Thickets](https://arxiv.org/abs/2603.12228).

**2. Mechanisms**

In the table, **"probe" means my proposed grid, not a safe dose found for OLMo**. Cost is an engineering estimate relative to ordinary Q4 inference; I did not measure performance on your card.

| Mechanism | What changes | What was observed in text | Dose and breaking point | How on llama.cpp + Q4 | Cost | My bet |
|---|---|---|---|---|---|---|
| **Gaussian noise on weights**, normalized per tensor | \(W'=W+\epsilon\,RMS(W)Z\). Can be applied identically to a chosen family in all layers | Found no reliable description of fiction prose. *Neural Thickets* shows working random neighbours, not only degradation | Probe ε: **0.001, 0.003, 0.01, 0.03**. Published absolute σ cannot be carried over as percentages | Dequantize → modify → requantize; or your own compute path | Preparation is expensive; the finished Q4 then costs the same as the original | Testable; I would not do it on the first evening |
| **Low-rank noise** | \(\Delta W=AB\), no training; match the norm of ΔW to a full-rank control probe | No confirmed special "creative" regime. There are studies of random subspaces on tasks with a checkable answer | Ranks **4, 16, 64** at the same relative norm. Low rank by itself does not protect | A random adapter through the supported LoRA path, or a patch; the adapter generator will have to be built | Much less memory than full-rank; extra matmuls | A reasonable second line, especially for per-page noise |
| **Noise only in quant scales** | Coherently stretches groups of weights while keeping the quant codes | Found no reproducible "dose → prose" map | Probe multiplicative σ: **0.005, 0.01, 0.03**; positive multipliers | Format-dependent GGUF edit | No extra cost at generation; a copy of the file | A cheap weight experiment, but unknown effect |
| **New weights every token / page** | The temporal correlation of the perturbation becomes a separate parameter | Found no evidence for your regime. MC dropout usually studies uncertainty, not imagery | First fix the noise for a **whole page**; then compare updating every **16 tokens** | No stock flag. Transformers — hooks/custom modules; vLLM — your own implementation; llama.cpp — patch/adapter | Full-rank every token is extremely awkward for Q4; low-rank is considerably cheaper | Per-page is more promising than per-token white noise |
| **Isotropic activation noise / random cvec** | \(h'=h+\alpha\,RMS(h)Z\); cvec is a fixed per-layer addition | For GPT-2-XL: “**still comparably coherent**” with a strong random vector; with a small one the qualitative effect is weak | Set the dose relative to activations. For an ordinary cvec the coefficient **is not a percentage** | Static: file + `--control-vector-scaled`. Updating every n tokens — your own loop through the API | A static set for your size ≈**1.23 MiB**; little arithmetic | A good cheap check, but a frozen cvec is not yet live isotropic weather |
| **DRµGS: rotations of H/Q/K/V/A** | Randomly changes a vector's direction while keeping its length; A is the output of an individual attention head before the O projection | Author: “**vary the outputs nicely**”, then repeating one word. Real generations exist | Published, for example, **θ=0.1 and 0.5 rad** on 30B AWQ. The breaking point depends on location and profile; there is no universal θ | Transformers prototype for Llama/Mistral. OLMo + llama.cpp needs a port | Q/A touch small activations; the implementation may add noticeable kernel launches. K/V across the whole cache is more expensive | **Best match to the idea itself**, but not a ready-made button |
| **Attention temperature** | \(\mathrm{softmax}(QK^\top/(\sqrt d\,\tau))\): changes the attention distribution inside the model | The paper shows an intermediate regime, “**grammatically coherent but irrelevant**”. Moderate changes preserve quality | On Qwen3-1.7B **0.9–1.1** stable; **0.8–1.3** limited effect; below **0.5** / above **1.7** frequently off-task | For OLMo: **Q-norm weights ÷τ** in a GGUF copy; no general stock flag needed | Same VRAM and practically the same speed | **First probe** |
| **RoPE base / scale** | Distorts positional relations, not directly the strength of associations | Found no verified "dreamlike" window | Probe base: **0.8×, 1×, 1.25×** trained base; scale **0.9, 1, 1.1**, separately | Flags exist, **but scale does not act identically on all OLMo layers** | Practically free | Below attention temperature: it is easy to mistake strangeness for loss of the text's spatio-temporal links |
| **KV noise / head dropout** | Changes access to the past; dropout removes computational channels | DRµGS gives adjacent evidence for K/V. For random removal of heads there is no prose map of the kind needed | Probe dropout **1%, 3%, 5%**; a fixed mask per page versus a new one per token are different experiments | Patch. `--cache-type-k/v` gives cache quantization, **not Gaussian noise** | Masking usually does not speed up dense kernels; a full pass over the cache gets more expensive with context | Higher risk of losing the narrator |
| **Skip / repeat / shuffle layers** | Changes the sequence of computations | Forum: “**slightly tipsy Miqu**”; another experiment — “**almost completely incoherent**” | Start with one middle block / one adjacent swap. There is no general percentage of tolerable removal | Graph patch or a new model build; mergekit `passthrough` is the route through the original weights | Skip is cheaper; repeat is more expensive. Repeating needs a separate KV for each occurrence | Effects happen, but the mechanic is too selective |
| **Q3 / Q2 / IQ1** | Structured, data-dependent error in the weight representation | “**drunk as hell**”; also grammatical and formatting errors. Evidence depends heavily on the model | No general ladder of "Q3 — fun, Q2 — collapse". IQ1 is not simply amplified Gaussian noise | A separate quant of **the same checkpoint**, preferably from BF16/F16 | Less VRAM; speed depends on kernels, not only on bpw | A useful damage control, a weak main candidate |
| **Mirostat / dynatemp / top-nσ / XTC** | Change token selection, not internal activations | Mirostat studies the “**boredom trap**” and the “**confusion trap**”; XTC is designed to bypass obvious continuations | Mirostat 2: τ **3, 5, 7 bits**. The other grids are below | Ready-made sampler parameters | Usually a small added cost | A mandatory competitor to any internal intervention |
| **Logit noise / heating schedule** | Gaussian noise changes the ranking; a schedule changes the moments when alternatives are explored | No confirmation that independent logit noise gives special imagery beyond good sampling | Probe σ **0.1, 0.3, 1.0 logit**; heating in short windows | Your own sampler / generation loop. Entropix is a separate research stack | Logits are cheap; lookahead/backtracking may already require extra forward passes | Dynatemp is worth testing before arbitrary noise |
| **Additionally: gain of the attention/MLP branches** | Changes the contribution of the branches before they are added to the residual | Found no relevant observations on prose | Probe gain **0.95, 1, 1.05** separately for attention and MLP | In OLMo the corresponding post-norm gains can be changed | Almost free | A clean global knob, but so far a hypothesis |

Sources for the table: [random activation vectors](https://www.lesswrong.com/posts/5spBue2z2tw4JuDCx/steering-gpt-2-xl-by-adding-an-activation-vector), [DRµGS — implementation](https://github.com/EGjoni/DRUGS), [attention temperature — full text](https://aclanthology.org/2026.acl-long.200.pdf), [layer interventions](https://arxiv.org/abs/2406.19384), [Mirostat](https://arxiv.org/abs/2007.14966), [sampling in llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md). Forum quotes with their authors are below.

A few distinctions here decide the outcome of the experiment.

**Uniformity in parameters is not uniformity of effect.** The same σ for an embedding, a norm gain and an MLP matrix are three completely different doses. Normalizing by the tensor's RMS fixes the scale, but not the sensitivity of the direction. To a first approximation, weight noise gives \(\Delta y=\Delta W x\): its effect depends on the input activation. Isotropic activation noise is a different distribution of interventions.

For a tensor-family sweep I would separate **Q/K**, **V/O**, **MLP gate/up/down**, and test embeddings and the output head separately. This is an engineering hypothesis: Q/K change routing, V/O the transferred content, gate/up/down the nonlinear transformation of features. No single family can honestly be called the proven site of "images." Moreover, OLMo normalizes Q/K and the outputs of both branches: normalization will almost wipe out a simple scalar amplification of some matrices; a change of direction it will not. [OLMo3 architecture](https://github.com/huggingface/transformers/blob/main/src/transformers/models/olmo3/modeling_olmo3.py).

For Gaussian noise, substantive counterexamples to "only slur" have appeared. *Neural Thickets* studies random weight perturbations up to 32B: in one analysis σ=0.005 in **absolute weight units**, in the main grid 0.001–0.003. But the results rest on checkable tasks, selection, and often an ensemble. This is not a demonstration of unselected strange prose. [Gan & Isola, 2026](https://arxiv.org/html/2603.12228v1).

In *Not the Dimension, the Norm*, random and SVD subspaces turn out to be close at matched scale; for the studied parameterization the boundary depends sharply on the norm. Their σ=0.05 refers to a specific way of constructing ΔW and **does not mean "add 5% noise to any GGUF"**. And there too, candidates are selected and tasks have an extractable answer. [Kim et al., 2026](https://arxiv.org/html/2608.01624v1).

**Preserving the norm is a useful constraint, but not movement "along the manifold."** A rotation stays on the sphere, and the sphere is not the set of the model's meaningful states. My bet on DRµGS has a more modest explanation: limit the destruction of the signal's scale and leave the subsequent computations able to process the perturbation.

One more detail: the DRµGS code builds the auxiliary direction via `rand_like`, i.e. from the positive cube. This is **not a strictly isotropic** distribution of directions. For your version I would use Gaussian `randn`, then remove the projection onto the original vector. That makes it a modification of DRµGS, not a literal replication. Starting grid for the port: θ **0, 0.025, 0.05, 0.1, 0.2 rad**, one type of intervention at a time. A or Q first, without directly overwriting the residual. [Porting guide](https://github.com/EGjoni/DRUGS/blob/main/porting/A%20Guide%20to%20Making%20DRUGS.md).

**Q4 adds its own traps.**

- Small noise before requantization can vanish; other small noise will push a code across a boundary. A "dequantized and requantized with no added noise" control is mandatory.
- Q4_K_M contains different tensor types. Processing only Q4_K does not mean processing the whole model uniformly.
- Q4_K has a scale and a minimum component. For pure multiplicative block noise you have to change `d` and `dmin` coherently; changing only `d` also changes the shape of the affine reconstruction. [Block format](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-common.h).
- 32B in BF16 is roughly **64 GB of weights alone**. You cannot quietly replace your Q4 experiment with ordinary full-weight Transformers inference on 24–48 GB.

When weights or the intervention change between pages, a freshly computed prompt cache is needed. When they change within a page, the old KV becomes the state of the previous perturbations. That is a legitimate dynamical system, but no longer exact inference of one chosen random model. DRµGS provides `cold_shower`, which recomputes the history without noise. [README](https://github.com/EGjoni/DRUGS).

**RoPE in your case really is not just a "free general knob."** The checkpoint has 64 blocks, 48 of them sliding-attention; the trained base is 500000. In the current `olmo2.cpp`, which serves this architecture, sliding layers get `freq_scale=1.0` regardless of the ordinary scale parameter. So `--rope-freq-scale` changes only part of the stack. [Checkpoint config](https://huggingface.co/allenai/Olmo-3-1125-32B/blob/stage1-step656000/config.json), [the actual graph](https://github.com/ggml-org/llama.cpp/blob/master/src/models/olmo2.cpp).

LayerShuffle cannot be carried over literally either: it is **vision transformers trained with shuffling**. LayerDrop introduces robustness during training. More relevant is the work of Lad et al. on removing and swapping adjacent layers without fine-tuning; its robustness does not imply robustness to an arbitrary permutation of the whole stack. When repeating a block, weights can be shared, but the KV of each occurrence must be separate. Early forum experiments ran into exactly this cache bug. [LayerShuffle](https://arxiv.org/abs/2407.04513), [LayerDrop](https://arxiv.org/abs/1909.11556), [implementation discussion](https://reddit.com/r/LocalLLaMA/comments/194zwyc/).

**Where does the sampler end?** There is no hard boundary of "beyond this you must change the weights": without softmax truncation almost any sequence has nonzero probability. The practical boundary is when too many broken pages come along with the increase in the frequency of interesting events.

It is especially important to check the sampler order. With `min_p → temperature`, raising T **does not bring back candidates already cut**. For `min_p=0.05`, the tokens left before temperature are roughly those within 3 logits of the maximum. T=5 may merely flatten a small set of admissible continuations. This is one possible cause of sobriety at high T, not a diagnosis of your run. [Sampling order and implementation](https://github.com/ggml-org/llama.cpp/blob/master/common/sampling.cpp).

Gumbel noise with argmax mathematically reproduces ordinary categorical sampling at the appropriate scale. Gaussian logit noise is not equivalent to it, but it does not know the semantic closeness of words. Entropix uses richer entropy signals and needs its own stack; I found no confirmed gain for your prose. [Entropix](https://github.com/xjdr-alt/entropix).

**3. Three experiments on your setup**

I choose three probes that do not require moving OLMo to another backend. **These are proposed procedures, not tests run here.** The scripts below were also not run on your GGUF.

For all three:

- The same original seeds, at most **170 new tokens**, ordinary completion.
- One fixed build, F16 KV, one slot; save the model hash, parameters, RNG seed and the full text.
- First 20 pages: one seed × four RNG × five regimes. Then the two best regimes and the baseline on three seeds × eight RNG.
- Blind reading: mark separately the preservation of language, of the narrator/frame, and your recognition of a dream. The main result is **the share of all pages where there is both a dream and a preserved frame**. One beautiful crash does not justify a regime.

A shared separate server for the probes:

```bash
MES_MODEL='/absolute/path/to/model.gguf'

llama-server -m "$MES_MODEL" -ngl 99 -c 1024 -np 1 \
  --cache-type-k f16 --cache-type-v f16 --port 8081
```

Example request; `seed.txt` here means a file with your existing seed:

```bash
jq -n --rawfile p seed.txt '{
  prompt: $p,
  n_predict: 170,
  seed: 101,
  cache_prompt: false,
  temperature: 2.2,
  min_p: 0.05,
  top_k: 0,
  top_p: 1,
  repeat_penalty: 1,
  samplers: ["min_p", "temperature"]
}' | curl -sS http://127.0.0.1:8081/completion \
  -H 'Content-Type: application/json' --data-binary @-
```

**Experiment 1 — identical attention temperature in all blocks.**

Mechanics:

\[
Q=\gamma_Q\odot RMSNorm(W_Qh),\qquad
\gamma'_Q=\gamma_Q/\tau.
\]

This divides the attention logits by τ. Scaling `W_Q` itself is worse here: the following RMSNorm will almost cancel such a change.

τ grid: **0.90, 1.00, 1.05, 1.10, 1.20**. Output temperature is 2.2 throughout. I consider **1.10** the first regime of interest; 0.90 is needed as a control for the direction of the effect.

Below is the creation of one independent copy with τ=1.10. It needs a single-file GGUF and checks for the expected 64 F32 Q-norm tensors of 5120 elements each:

```bash
uv run --no-project --python 3.12 --with numpy --with gguf \
  python - "$MES_MODEL" ./mescalito-tau110.gguf 1.10 <<'PY'
import re, shutil, sys
from pathlib import Path
import numpy as np
from gguf import GGUFReader, GGMLQuantizationType

src, dst = map(Path, sys.argv[1:3])
tau = float(sys.argv[3])
assert np.isfinite(tau) and tau > 0
assert src.resolve() != dst.resolve() and not dst.exists()

reader = GGUFReader(src)
targets = [
    t for t in reader.tensors
    if re.fullmatch(r"blk\.\d+\.attn_q_norm\.weight", t.name)
]
assert {int(t.name.split(".")[1]) for t in targets} == set(range(64))
assert all(
    t.tensor_type == GGMLQuantizationType.F32
    and t.n_elements == 5120 for t in targets
)
names = {t.name for t in targets}

with src.open("rb") as source, dst.open("xb") as output:
    shutil.copyfileobj(source, output, 16 * 1024 * 1024)

edited = GGUFReader(dst, mode="r+")
for tensor in edited.tensors:
    if tensor.name in names:
        tensor.data[...] /= tau
edited.data.flush()
print(f"Changed {len(names)} Q-norm tensors; attention tau={tau}")
PY
```

For each dose take the original file, not the previous modification. Then start the server with the corresponding copy. About 1.25 MiB of norms change; the rest of the file is copied without requantization. [GGUF reader](https://github.com/ggml-org/llama.cpp/blob/master/gguf-py/gguf/gguf_reader.py).

**What to read:** the whole page, especially the continuation after the first unusual event. If a new object or an impossible relation appears and the remaining sentences hold on to its consequences, that is a useful signal. If it starts getting confused about who saw what and when, you have got attention blur.

The published window τ=0.9–1.1 refers to small reasoning models. It gives a reasonable start, not a guarantee for a 32B base. [Doses and degradation in the paper](https://aclanthology.org/2026.acl-long.200.pdf).

**Experiment 2 — a random per-layer field, frozen for the page.**

Create an independent random vector for each available layer. No text pairs and no chosen meaning of direction.

```bash
uv run --no-project --python 3.12 --with numpy --with gguf \
  python - ./mescalito-random-101.gguf 101 <<'PY'
import sys
from pathlib import Path
import numpy as np
from gguf import GGUFWriter

path = Path(sys.argv[1])
assert not path.exists()
rng = np.random.default_rng(int(sys.argv[2]))

writer = GGUFWriter(str(path), "controlvector")
writer.add_uint32("controlvector.layer_count", 63)

for layer in range(1, 64):
    vector = rng.standard_normal(5120).astype(np.float32)
    vector /= np.sqrt(np.mean(vector * vector))
    writer.add_tensor(f"direction.{layer}", vector)

writer.write_header_to_file()
writer.write_kv_data_to_file()
writer.write_tensors_to_file()
writer.close()
PY
```

Addition at launch:

```bash
--control-vector-scaled ./mescalito-random-101.gguf:0.03 \
--control-vector-layer-range 1 63
```

Coefficient grid: **0, 0.01, 0.03, 0.10, 0.30**. In this construction the coefficient equals the RMS of the addition in the residual's own units; **0.03 does not mean 3% of the residual**.

Repeat with vector seeds **202 and 303**. Within a page the field is kept; between pages you can pick a different file. Do not pick a single "beautiful" vector seed and declare it a universal mechanism.

In current llama.cpp the layer with internal index 0 is excluded for cvec. So this is a distributed intervention into 63 blocks, with the first explicitly excluded. The loaded directions are added to the residual; the stock flag does not create a new random direction each token. [cvec implementation](https://github.com/ggml-org/llama.cpp/blob/master/src/llama-adapter.cpp).

**What to read:** compare different vector seeds at one dose. If one gives a stable foreign register or a single obsessive theme, that is random steering. If different fields raise the frequency of unexpected images while the frame holds, that is already closer to the mechanic you are after.

A negative result here **does not rule out DRµGS**: the location, normalization and temporal structure of the intervention differ.

**Experiment 3 — check whether the sampler does the same job more cheaply.**

The original GGUF, no cvec. Everything else as in the shared request. Compare four regimes:

| Regime | Request fields |
|---|---|
| Control | `samplers:["min_p","temperature"]`, `min_p:0.05`, `temperature:2.2` |
| Heating at high entropy | The same chain; `temperature:2.0`, `dynatemp_range:1.5`, `dynatemp_exponent:1.0` |
| Bypassing obvious forks | `samplers:["min_p","xtc","temperature"]`, `min_p:0.05`, `xtc_probability:0.3`, `xtc_threshold:0.1`, `temperature:2.2` |
| A different way of cutting the tail | `samplers:["top_n_sigma","temperature"]`, `top_n_sigma:1.0`, `temperature:3.5` |

If the last regime is almost deterministic, the next separate step is `top_n_sigma:2.0`.

Dynatemp here works in the range **0.5–3.5**, setting the temperature from the entropy of the remaining candidates. It is not a detector of plot forks: lexical uncertainty and a semantic fork coincide only sometimes. [dynatemp and top-nσ implementation](https://github.com/ggml-org/llama.cpp/blob/master/src/llama-sampler.cpp).

For literally scheduled heating you need your own loop: for example, T=1.0 for the first 24 tokens, then four-token windows of T=4.0 every 32 tokens. This is a meaningful additional probe, but I found no ready-made stock flag for such a schedule.

**What to read:** at comparable frame preservation, compare the pages of this experiment with experiments 1–2. If the internal intervention gives the same scatter of random words and the same rate of collapse, there is no reason yet to complicate the machine. If it changes the character of events with less linguistic damage — then porting DRµGS is justified.

**4. Sources and direct evidence**

The forum excerpts below were verified through Arctic Shift. I also read weak and negative replies, not only popular ones. The archive's full-text search returned a timeout several times; fetching known threads by ID worked.

- **[forum] u/qrios, r/LocalLLaMA, “Stop messing with sampling parameters and just use DRµGS!”, December 29, 2023.** The author describes the boundary:
  
  > “It mostly seems to either vary the outputs nicely, or else immediately break and start repeating the same word over and over.”
  
  This is the developer's testimony, not an independent evaluation. In the same discussion his attempt to use strong noising against repetition has a very narrow boundary between no effect, usefulness and breakage. [Thread](https://reddit.com/r/LocalLLaMA/comments/18toidc/).

- **[scene] EGjoni, DRµGS porting guide.**
  
  > “Do not inject drugs directly into the residual stream.”
  
  This is the author's practical recommendation, not a general mathematical prohibition. It explains why "random cvec" and DRµGS cannot be considered one implementation. [Guide](https://github.com/EGjoni/DRUGS/blob/main/porting/A%20Guide%20to%20Making%20DRUGS.md).

- **[scene] Turner et al., “Steering GPT-2-XL by adding an activation vector”, 2023.**
  
  > “the outputs are still comparably coherent to unsteered GPT-2-XL.”
  
  This is about a strong random vector. A shift in the distribution was observed, but not an established regime of dreamlike prose. [Experiment](https://www.lesswrong.com/posts/5spBue2z2tw4JuDCx/steering-gpt-2-xl-by-adding-an-activation-vector).

- **[paper] Yu et al., *Thermometer of Thoughts*, ACL 2026.**
  
  > “output quality remains stable for attention temperatures between 0.9 and 1.1”
  
  The evaluation concerns reasoning outputs; carrying it over to fictional imagery is our hypothesis. [Paper](https://aclanthology.org/2026.acl-long.200.pdf).

- **[paper] Kim et al., *Not the Dimension, the Norm*, August 2026.**
  
  > “performance collapses abruptly rather than degrading gracefully.”
  
  A useful warning against the idea of a smooth intoxication scale. Their method, models and dose units differ from your Q4. [Preprint](https://arxiv.org/html/2608.01624v1).

- **[forum] u/Fluid_Intern5048, r/LocalLLaMA, “Best Miqu and Llama-3 Frankenmerge (Self)”, May 11, 2024.**
  
  > “It performs like a slightly tipsy Miqu after a glass of wine - a bit sluggish but full of inspirations.”
  
  The same author writes that carrying the 103B recipe over to Llama-3 degraded the logic too much. This is especially useful negative evidence about transferability. [Thread](https://reddit.com/r/LocalLLaMA/comments/1cpct22/).

- **[forum] u/Small-Fall-6500, r/LocalLLaMA, “Instant Frankenmerges with ExllamaV2”, January 12, 2024.**
  
  > “Initial tests with tinyllama show that it's very easy to make the model almost completely incoherent.”
  
  Nearby there are positive assessments of creativity, but the published examples already contain collapsing punctuation and word forms. By your criterion I would not count them automatically. [Thread](https://reddit.com/r/LocalLLaMA/comments/194zwyc/).

- **[forum] u/PavelPivovarov, r/LocalLLaMA, “What improvement or new feature would you like to see on Llama 3?”, January 21, 2024.**
  
  > “Heavily quantised 34b are drunk as hell, from my personal experience”
  
  Q2 and Q3_K_S of several models are mentioned; the author did not like the result. "Drunk" here means unwanted degradation, not discovered imagery. [Thread](https://reddit.com/r/LocalLLaMA/comments/19bs0fy/).

- **[forum] u/input_a_new_name, r/SillyTavernAI, “The dilemma about the quality of quantization”, October 22, 2024.**
  
  > “slightly increased frequency of grammatical and formatting inaccuracies”
  
  About going from Q6 → Q5/Q4 on a 12B. At the same time the author noticed no significant change in situational understanding. [Thread](https://reddit.com/r/SillyTavernAI/comments/1g9u4ig/).

- **[scene] janus, “Language models are multiverse generators”, 2021.**
  
  > “these continuations can be kept and each continued themselves to yield a branching structure”
  
  The reproducible technique found is Loom — branching, returning to forks and selecting continuations. It is a useful way to mine rare pages, but not a change to the machine from the inside. [Post](https://generative.ink/posts/language-models-are-multiverse-generators/).

**5. What I did not find**

- A study of precisely **OLMo-3-32B `stage1-step656000`, Q4_K_M** that measured your kind of coherence over 170 tokens and human recognition of a dream.
- A comparison of Gaussian weight noise across **Q/K/V/O, gate/up/down, embeddings/head** with published fiction pages and a normalized dose.
- Evidence that low-rank noise, quant-scale noise or a new random model every token systematically produce the imagery you want.
- Ready-made upstream DRµGS support for OLMo in llama.cpp. The existence of the closed [issue #4704](https://github.com/ggml-org/llama.cpp/issues/4704) does not by itself mean an implementation.
- A public reproducible recipe from janus/repligate, Act I or the base-model-backrooms scene that changes weights/internal dynamics and demonstrates precisely this effect. What was found mostly concerns context, interaction between models and branch selection.
- Grounds to consider a preserved norm, low perplexity or an improved reasoning benchmark as proof of the "lightning." For that you still need your full page and a reader.
