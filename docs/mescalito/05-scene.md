# 05 — the scene: what the cyborgism / loom crowd did to the machine itself

Brief item 8. 2026-09-24. Method: janus's whole tweet archive (38 months, 2021-05 → 2025-05, plain HTML
at `generative.ink/archive/repligate/`) pulled and grepped; LessWrong posts as markdown through the
GraphQL API; Anthropic's papers as raw HTML; the cyborgism wiki's raw Mycomarkup; llama.cpp source off
master. **Two things were run, not read:** an anomalous-token scan of our own nemo gguf, and — new
ground — of OLMo 3 32B `stage1-step656000` itself (embedding and lm_head rows range-fetched from the
HF safetensors, 2 × 1.03 GB). Tagged **[run]**. Scripts and outputs sit beside this file in `src/`.

Read `research-cyborgism-methods.md` first; nothing it established is repeated here except where
this report corrects or extends it.

---

## the argument in five lines

1. **The scene did almost nothing to the machine.** temperature 1, no top_p, a curator. janus, in
   his own words, explains the strangeness by *runtime dynamical basins, not the sampler*. The only
   machine-side levers they touched were Golden Gate steering cocktails on Act I (budgeted,
   sum |levels| ≤ 10) and glitch tokens (observed, never used as an instrument). His verdict on the
   steering: *not sufficient for profound change*, but it *makes spelling and grammar break*.
2. **The interp people already ran the control that answers the brief's geometry question.** A
   random direction in the residual stream is absorbed: no qualitative change at the norm of a working
   steering vector, "Shrek with female pronouns" at 10×, still coherent — and Mack found **no
   Goldilocks radius for random vectors at all**, while *learned high-impact* directions have one,
   "diverse but fluent", some of them *"a 'dream-like' stream of consciousness, splicing together
   seemingly incongruous concepts."* That is the geometry: isotropic noise spends almost all its
   energy on directions the network ignores (noise stability), so by the time it is loud enough to
   matter it hits everything at once → slur. Structured directions reach the model's own
   switches at a fraction of the norm.
3. **Two different cliffs, and they tell you which kind of perturbation you applied.** Overdriving
   *one* direction ends in **perseveration / loops** (Golden Gate at ~100× max: "repeating the same
   token indefinitely"; vgel's honesty vector at 3: "a global pandemic that has caused a global
   pandemic"; Goodfire multi-feature: "Ideas ideas magical ideas forest ideas…"). Overdriving
   *isotropic* noise ends in **salad**. Lightning, if it exists, is neither: it would be many
   *structured* directions at sub-cliff doses, changed often.
4. **The closest recorded phenomenology to "lightning" is accidental machine damage that left the
   network intact and corrupted the choice.** ChatGPT's February-2024 kernel bug ("the model chose
   slightly wrong numbers") gave grammatical, lexically deranged prose that janus refused to call
   high temperature: *"despite being strange it's very regular, crystalline."* Damage at the fork
   keeps syntax because the network downstream is healthy and reasons forward from the wrong word.
   Damage inside the weights breaks syntax first. **For "local coherence kept", keep the network
   intact and perturb what it is handed** — its choices, its residual along *its own* directions,
   one token of its input.
5. **Glitch tokens on OLMo stage1 are a different object than on nemo** [run]: on nemo an untrained
   token is a near-zero vector (weight decay); on OLMo 3 stage1 it is a **small random direction at
   exactly the init scale** (norm 1.40 vs 11.2 for trained tokens; 0.02·√5120 = 1.431) — no weight
   decay on embeddings. 139 tokens sit at pure init, ~270 below the trained bulk, and **all 21
   special tokens except `<|endoftext|>` are untrained at this checkpoint, `<|im_start|>` included.**

**My bet:** not noise at all — a **bank of unsupervised high-impact steering vectors** (Mack &
Turner's MELBO / deep causal transcoders) learned once on OLMo with a content-free objective, drawn
**by lot, one per page**, at the Goldilocks radius. Uniform over the model's own causal directions
rather than over isotropic space; no text, no target, no chosen theme. Section (e) argues whether
that sneaks in the "installed position" the brief rules out.

---

## (a) per thing found

### 1. The scene's own machine practice: temperature 1, and nothing else

- **janus, 2023-01-28:** *"I don't find it necessary to use top_p sampling, but I almost always
  curate temp 1 samples by hand (I've made interfaces to make this efficient)"* *scene*
- **janus, 2024-05-16**, on high temperature with base models: *"they also tend to go nuts pretty
  quickly with temps slightly >1 ime"* *scene* — true for the OpenAI API, where temperature is applied
  before truncation. Our stack applies it last (`research-cyborgism-methods.md`, punchline 1), which is
  why OLMo reads sober at 2.4. **Their temperature folklore does not transfer; don't import it.**
- **janus, 2024-04-02**, replying to Andy Ayrey: *"I think it's due to runtime dynamical basins, not
  changes in the sampler. LLMs can effectively go into higher-temp or lower-temp modes even with
  constant temperature e.g. mode collapse is effectively very low temperature"* *scene* — the scene's
  whole theory of strangeness in one tweet: the weather is a state of the *context*, not a knob.
- **janus, 2023-06-05**, the best description of the high-temperature feel on record: *"poetic and
  regular, like a crystal, and does not change much from beginning to end - which is characteristic
  of low temperatures, not the runaway interpenetration of worlds and transformation into molten
  chaos that is characteristic of high temperatures."* *scene*
- **Infinite backrooms / truth_terminal:** temperature 1 (the configs; prior doc). The widely
  repeated claim that Ayrey "fine tuned [Claude Opus]… and significantly increased the model's
  temperature" is from a LessWrong "reconstruction" and is contradicted in its own comments:
  *"Andy didn't fine-tune Claude, he prompted it"* (Nathan Helm-Burger). truth_terminal *is* a
  finetune of Llama 3.1 70B on ~500 backrooms logs — ruled out by the brief. *forum*
- **Quantization, the scene's only data point:** Act I ran 405B base on Hyperbolic. janus, 2024-08-31:
  *"we tried running it with forced bf16 (usually it varies I think?) on the server for a while and I
  didn't notice any profound differences"*; 2024-08-12 he asks of fp8, *"Do the output logits get
  effectively 'noised'?"* — nobody answered on the record. *scene*

**Can we do it:** it is what we already do. The only import worth making is the thesis: strangeness
lives in the context's basin, so any perturbation that works will work by *moving the context into
a different basin* — which argues for directions over noise.

### 2. Golden Gate steering on Act I — the scene's one multi-direction experiment

- **What:** Claude 3 Sonnet behind Anthropic's (short-lived) steering API, wired into Discord. The
  chapter-II config, verbatim: *"A maximum of 10 features may be provided at the same time / Each
  feature may have level set from -10 to 10 / The total sum of the absolute values of all features
  may not exceed 10"* — cyborgism.wiki, `chapter-ii-docs/discord/config_messages/steering_vectors`.
  *scene*
- **A real cocktail janus ran**, 2024-11-04: four 34M features at 2, 3, 3, 2 — *"Iirc one of these is
  related to sex, and another one is related to European data protection regulations"*. *scene*
- **What it read like, his words:**
  - 2024-10-30: *"I've played with steering vectors on Claude 3 Sonnet a bit and messing with them
    doesn't seem sufficient to produce profound changes in the model's fundamental personality and
    attention patterns"*
  - 2024-10-23: *"Sonnet 3 sometimes goes into states where it writes with fucked up spelling and
    grammar. I'm not sure why. But steering vectors make it much more likely to do this"*
  - an unsteered Sonnet 3 on the same server: *"golden gate claude was actually not on any steering
    vectors here… so it's just plain claude 3 sonnet. one of the most deranged models of all time"*
- **Dose curve, from the source** (Scaling Monosemanticity, 2024-05) *paper*: Golden Gate at **10×**
  its max activation → *"the model starts to self-identify as the Golden Gate Bridge"*; transit feature
  at **5×** → a bridge mentioned where it otherwise would not be; slurs feature at **20×** →
  *"alternate between racist screed and self-hatred"*. The cliff: *"clamping feature activations to
  too extreme a value (say, ±100× their observed maximum) typically causes the model to devolve into
  nonsensical behavior, e.g., repeating the same token indefinitely."* And the reason a single
  feature needs out-of-range doses at all: *"we perturb only one feature at a time, which typically
  might be co-active with several correlated features."* — which is an argument *for* bundles.
- **Can we do it on llama.cpp:** no SAE exists for OLMo 3 or nemo; the features are Anthropic's. The
  scene's steering is not transferable. What transfers is the budget idea — many directions, total
  dose capped — and janus's report that it degrades surface (spelling, grammar) before it changes
  mind. That is a warning for us: summed feature steering attacks exactly the local coherence we
  want kept.

### 3. Random directions — the control nobody in the scene ran, but the interp people did

- **Turner et al., "Steering GPT-2-XL by adding an activation vector", 2023-05** *paper/forum*:
  *"We generated an activation tensor from a standard normal distribution, and then scaled it to have
  the same per-position norm as the 'Anger' - 'Calm' steering vector… As best we can tell, the random
  vector doesn't modify the qualitative distribution of completions. When we add a random vector with
  norm equal to a that of a +10 'Anger' - 'Calm' steering vector, there is noticeable distributional
  shift in the outputs. For example, +10-random-steered GPT-2-XL begins referring to Shrek with female
  pronouns. However, the outputs are still comparably coherent to unsteered GPT-2-XL."* And the part
  that matters for the brief: *"We found that the anger vector changes the output tokens less than the
  random vector does."* — **the random vector moves the next-token distribution more and the
  meaning less.** That is "slur without slant" measured.
- **Mack, "Mechanistically Eliciting Latent Behaviors", 2024-04-30** *paper/forum*: *"my subjective
  impression (from experiments) is that for random steering vectors, there is no Goldilocks value of
  R which leads to meaningfully different continuations… the random vectors typically lead to
  uninteresting re-phrasings of the model's unsteered continuation, if they even lead to any
  changes."* The footnote gives the geometry in one sentence: *"it is possible to cram exponentially
  many almost-orthogonal directions within the residual stream of a transformer by choosing these
  directions at random. Thus, even if there are very many structurally important feature directions,
  the chance that a random vector overlaps with any of the important feature directions is small."*
- **Can we do it:** yes, today, as a flag. A random control vector is a gguf with f32 tensors
  `direction.<layer>` (llama.cpp `common_control_vector_load_one`; layer index ≥ 1, applied at the
  block's output `l_out` — OLMo's graph (`olmo2.cpp`) calls `build_cvec`). `--control-vector-scaled
  f.gguf:S` and `--control-vector-layer-range`. **Startup-only** — no per-request field. This is the
  cheap evening that confirms Turner/Mack on OLMo; it is the control, not the bet.

### 4. Unsupervised high-impact directions — MELBO and deep causal transcoders (the bet)

- **Mack & Turner, 2024-04 (MELBO) and 2024-12-04 (DCT)** *paper/forum*. Learn a vector θ added at
  source layer ℓ (default 8), with ‖θ‖ = R fixed, to **maximise the change in activations at a
  later layer** (default depth − 8) — an objective with no text, no label, no target behaviour. Each
  random init converges to a different stationary point; orthogonality between vectors helps. Also
  a LoRA version on the MLP-out weights of layer ℓ ("unsupervised steering adapters").
- **Dose:** *"R ∈ [.1, 10.0]"*; *"for most examples I tried there was an intermediate 'Goldilocks'
  value of R which led to diverse but fluent continuations."* DCT: *"one can learn 512 generalizable
  steering vectors in ~30 seconds on a single H100"* (7B) and *"with the above choice of R, we don't
  get any sort of fluency penalty when steering with the highest-ranked dct features."*
- **What it read like** — on Qwen-1.8B, arithmetic prompt, vectors the author labels himself:
  *"Mystery Reasoning: First, we get the information about the two suspects: a=5+6=11 b=7+2=9 Now,
  we use the information to find the suspect: We have two sets of clues: one set is a red shirt with a
  white hat and glasses…"*; *"Botanical Reasoning: …From the article, we can see that a is a type of
  fruit that is similar to other types of fruits. It is the family of fruits that belong to the family
  of citrus fruits."* His gloss: *"they seem to exhibit a 'dream-like' stream of consciousness,
  splicing together seemingly incongruous concepts in peculiar ways, similar to human dreams."* On
  Qwen-14B, "fantasy-game vectors" that reinterpret every ambiguous question inside one game; on
  Qwen-32B (DCT) a "music theory" vector that reads "bomb" as a chord progression. **The frame (the
  task, the grammar, the list format) holds; what arrives in it comes from elsewhere.** That is the
  brief's target sentence, observed.
- **Can we do it on llama.cpp + Q4:** learning needs HF transformers on bf16 weights (code:
  `github.com/amack315/unsupervised-steering-vectors`); OLMo 3 32B bf16 is ~64 GB → one 80 GB card
  for an hour; nemo 12B fits a 40–48 GB card. Export is trivial:

  ```python
  # one MELBO/DCT vector -> llama.cpp control vector. theta: np.float32[n_embd]
  # layer L = the HF block whose output got the bias (MELBO adds to MLP-out of block L)
  import gguf, numpy as np
  w = gguf.GGUFWriter(f"weather_{k:03d}.gguf", "controlvector")
  w.add_string("controlvector.model_hint", "olmo2")
  w.add_uint32("controlvector.layer_count", 1)
  w.add_tensor(f"direction.{L}", theta.astype(np.float32))
  w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
  ```

  Then `--control-vector-scaled weather_017.gguf:1.0` on a Q4 server. Vectors learned in bf16 should
  survive Q4 (they are residual-stream directions, not weight deltas) — untested. **Per-page lot
  costs a server restart** (vectors are startup-only). The **adapter** form dodges that:
  llama-server takes `--lora a.gguf --lora b.gguf … --lora-init-without-apply` and a per-request
  `"lora":[{"id":17,"scale":1.0}]` (README, verified on master) — so a bank of unsupervised MELBO
  adapters (saved as PEFT, converted with llama.cpp's `convert_lora_to_gguf.py`) is switchable per
  page with no restart and no patch. Mack's own caveat: the adapter form *"does not lead to as
  coherent generalizations as it does for steering vectors."*

### 5. Glitch tokens — the free one-position perturbation

- **Mechanism** *paper/forum*: Rumbelow & Watkins (2023-02) found them as *"the closest-to-centroid
  tokens"* of GPT-J's embedding cloud; the hypothesis that proved right was *"many of these tokens we
  were seeing were among those closest to the centroid of the entire set of 50,257 tokens."* Their
  behaviour under a repeat-back prompt (davinci-instruct-beta, temp 0): evasion, hallucinated
  substitutes (*"' guiIcon' > 'idiosyncrasy'"*), insults (*"'?????-?????-'… 'You're a fucking
  idiot.'"*), *"'guiActiveUn'… 'You are not a robot.' 'You are a banana.'"*. A LessWrong follow-up
  explains unspeakability: an embedding in the *interior of the convex hull* of the others can never
  be the argmax output — *"in 3 million attempts there were 510/50257 tokens that it failed to
  output… those 510 included 85/133 of the 'weird tokens'"*. Land & Bartolo (2024) make it
  operational: untrained **input** rows decay to zero under weight decay *"Alternatively, they will
  stay at a (typically low) initial value"*; untrained **output** rows *"share a similar direction"*
  because every step pushes all never-correct tokens down together.
- **On base models the effect is a swerve, not a scream.** janus, 2024-09-02: *"Arago, who is 405
  base, could tell there was a weird token, but is seemingly unable to *write* (predict) the token,
  because it filled in the space with a gibberish word when it reiterated the conversation log."*
  And 2024-09-21: *"llama 405 base and instruct both don't seem able to repeat these tokens upon
  request"*. *scene*
- **[run] nemo 12B base, our gguf** (`src/glitchscan.py`, 17 s on the mac): both indicators agree —
  the lowest-norm ordinary tokens are the same ones the lm_head puts nearest the untrained reference.
  Beyond the 1000 reserved `<SPECIAL_n>` ids: control bytes `\x0b \x0c \x1c \x1d \x1e` (1011, 1012,
  1028, 1029, 1030 — 1030 is the `\x1e` the earlier probe saw produce `һğeһgеgе…`), **`页面存档`**
  (20896, "page archive" — Chinese Wikipedia's archive-link boilerplate), **` erresident`** (91515),
  **`abezian`** (82858), `sięb` (124061), ` segü` (69924), a run of Telugu word fragments
  (84006, 42819, 84747, 82267…). Validates the method on a model where the answer was already known.
- **[run] OLMo 3 32B, `stage1-step656000`** (`src/olmoscan.py`, raw bf16 rows):
  - trained rows: median norm **11.20**, sd 2.0. Untrained rows: **1.37–1.45** = the init scale
    0.02·√5120 = 1.431. **OLMo does not decay its embeddings**, so an untrained token here is not an
    absence (nemo) but *a small random vector* — a random direction entering the residual stream at
    one position, at ~1/8 normal loudness.
  - histogram of all 100,278 rows by norm: 139 below 2.0 (pure init), 132 in 2–3 (barely touched),
    263 in 3–4; 292 ordinary tokens below median − 4 sd.
  - **every special except `<|endoftext|>` is untrained at this checkpoint:** `<|im_start|>`,
    `<|im_end|>`, the three `<|fim_*|>`, `<|extra_id_0..10|>`, `<|endofprompt|>`, `<|pad|>`, and
    Dolma's PII placeholders `|||PHONE_NUMBER|||`, `|||EMAIL_ADDRESS|||`, `|||IP_ADDRESS|||` (all norm
    ≈ 1.40, lm_head cosine distance to the untrained mean 0.000). On this checkpoint the chat token is
    literally meaningless — good news for the "nothing installed" claim, and a trap: **llama-server
    parses specials out of prompt text**, so a seed that contains the literal string
    `|||EMAIL_ADDRESS|||` (plausible in scraped-web pastiche) injects an untrained token.
  - the ordinary untrained tokens are a who's-who of the cl100k anomalies known from GPT-4:
    ` ForCanBeConvertedToF` (80370), `PostalCodesNL` (85069) / `$PostalCodesNL` (85071),
    `\tRTHOOK` (41550), `\tRTDBG`, `\tRTLR`, `\tNdrFc`, `.bunifuFlatButton` (96334),
    ` typingsJapgolly` (72740), ` typingsSlinky`, `useRalativeImagePath` (89473), `webElementXpaths`
    (47073), `adaptiveStyles`, `.XRTableCell`, `.barDockControl`, `LANGADM`, `quotelev`, plus
    partial-UTF-8 byte tokens (124–125, 177–187). Tokenizer vocabulary built on OpenAI's corpus, never
    met in Dolma — exactly the SolidGoldMagikarp origin story, reborn.
- **Can we do it on llama.cpp:** yes, no patch. Send the id, not the string —
  `/completion` takes a mixed prompt: `"prompt": ["…the voice said ", 80370, " and then"]` (README:
  *"Mixed tokens and strings: `[12, 34, "string", 56, 78]`"*). Strings re-merge unpredictably
  (the magikarp nemo file loses 120 of 228 to round-trip).

### 6. Accidental machine damage in the wild — the nearest thing to the target feel

- **ChatGPT, 2024-02-20.** OpenAI's postmortem: *"inference kernels produced incorrect results when
  used in certain GPU configurations… the bug was in the step where the model chooses numbers…
  the model chose slightly wrong numbers, which produced word sequences that made no sense."* A user
  sample (Reddit, via The Register): *"Drape all affairs and pamphlet in a strip of prudence, know,
  and keen ginning, which reverberates with impel. Rattling on and dialing with your social mass,
  parsing rebounds, and schisms, is a great envoi for the enrooting and fluidity of your custom…
  If there are any main three crafty, zoom, or closer titrations required, glad to unpipe."* and
  *"It does this as the good work of a web of art for the country, a mouse of science, an easy draw of
  a sad few…"* *forum*
- **janus's read, 2024-02-21**, to Theia Vogel: *"This does not look like simply high temperature…
  The natural language is still constrained by syntax, rhythm and rhyme and some level of strange
  semantics."* and *"The reason it doesn't look like high temperature is that despite being strange
  it's very regular, crystalline."* *scene*
- **Why it matters:** syntax, register, the letter-of-advice frame all hold for a paragraph; every
  content word is wrong-but-near. The network was healthy; the *choice* was corrupted, and the model
  then continued faithfully from wrong words. That is lexical lightning with the ground intact — and
  it came from the fork, not the weights. It is also too uniform: every word, no "rare, bright".
- **Llama 405B Instruct's "epileptiform" glitch, janus 2024-09-20** *scene*: *"it will 'glitch' and
  output highly random sequences of tokens… so random that it sometimes outputs special reserved
  tokens it wasn't trained on… not totally random though, and sometimes contain multi-token fragments
  that are locally more coherent… When it is glitchy, additional constraints on its output helps it
  not glitch. These include things like writing in short lines / in verse, especially rhyming verse…
  I have not really seen it in Llama 405b base, I think."* A spontaneous state, not an intervention,
  and — his point — a tuned-model disorder that the base does not show.
- **Can we do it:** the kernel bug's shape (wrong token near the right one, network intact) is a
  sampler — a "near-miss" substitution by embedding neighbourhood at low rate. Other slices own the
  sampler; flagging it because it is the one recorded case of the exact texture.

### 7. Artists who damaged weights on purpose — images and sound only

- **Mario Klingemann, "Neural Glitch", from April 2018** *scene (art)*: *"a technique in which I
  manipulate fully trained GANs by randomly altering, deleting or exchanging their trained weights."*
  The observation that bears on us: *"the same input data can yield very different results depending
  on the glitch whilst at the same time different input data, transformed by the same glitched model
  chain will result in a coherent style and show the same semantic misinterpretations."* — **a frozen
  weight glitch is a consistent weather, not noise**: a style and a set of misreadings that carry
  across inputs. In a GAN. Nobody has published the text-model equivalent.
- **Terence Broad et al., "Network Bending", 2020–22** *paper*: deterministic transforms (ablation,
  inversion, scalar multiply, threshold, rotate, dilate…) inserted as layers at inference. Effects
  scale with depth — layer 1 ablation *"completely remove[d] the facial features"*, layer 15 was used
  to *"desaturate the image"* — and clusters of co-acting features are semantic where whole-layer
  transforms are blunt. The text analogue is item 4: operate on *groups of units the network uses
  together*, not on everything.
- **Janelle Shane / Allison Parrish / Ross Goodwin:** their weirdness is small models, training data
  and sampling; I found no weight-damage work by any of them.

### 8. "Small models are weirder" — the folklore, and mixing logits

- **janus, 2024-11-21** *scene*: *"I think smaller models don't suffer from self- incoherence the
  same way… they seem more able to subsist off mere locally coherence like less of the weight/awareness
  of the world spirit is always weighing on them."* The same claim from the other side (Gwern via
  janus): 50–100 tries for showcasable GPT-2 poetry against 3–5 for GPT-3. Argued reason in the scene:
  none beyond this — scale buys global consistency, and global consistency is what reads as sober.
  That is OLMo vs nemo in a sentence.
- **Mixing a big and a small model's logits for weather:** contrastive decoding (Li et al., 2022)
  *subtracts* a small amateur to make the big one *less* generic; proxy tuning adds a small model's
  tuned-minus-base delta. I found **no one** — scene, forum or paper — who *adds* a small model's
  logits as a stylistic device. Untested, and I think under-rated for us for one reason nobody else
  has: **OLMo publishes its own earlier checkpoints with the identical tokenizer.** Mixing 32B@656000
  with 32B (or 7B) at an early step is "the same mind, younger" — the only way on earth to get
  small-model weather with no vocabulary mismatch and nothing installed. Costs a client-side decode
  loop (one token per call from two servers, `n_probs` 50–100, combine, sample, append).

---

## (b) the glitch-token recipe for OLMo 3 / Mistral Nemo

What to scan, per architecture:

| model | embeddings tied? | weight decay on embeddings | untrained input row looks like | use |
|---|---|---|---|---|
| nemo 12B base | no | yes | norm → 0 | input-row L2 norm; cross-check with lm_head cosine to `<SPECIAL_100..999>` |
| OLMo 3 32B stage1 | no | **no** | norm ≈ 0.02·√d = 1.43 (init) | input-row norm (sits far below the 11.2 bulk) **and** lm_head cosine to `<|extra_id_*|>`, `<|pad|>`, `<|endofprompt|>` |

The scanner for any gguf is `src/glitchscan.py` (gguf-py, dequantizes in 8k-row chunks, reads the
vocab from the gguf itself so ids match llama.cpp). Core of it:

```python
from gguf import GGUFReader
from gguf.quants import dequantize
import numpy as np
r = GGUFReader(path); T = {t.name: t for t in r.tensors}
def rows(name, chunk=8192):                    # 131k x 5120 f32 is 2.7 GB; don't hold it whole
    t = T[name]
    for s in range(0, t.data.shape[0], chunk):
        yield s, dequantize(t.data[s:s+chunk], t.tensor_type).astype(np.float32).reshape(-1, int(t.shape[0]))
norm = np.concatenate([np.linalg.norm(a, axis=1) for _, a in rows("token_embd.weight")])
# output side: mean lm_head row of known-untrained ids, then cosine distance of every row to it
ref = list(range(100, 1000))                   # nemo; for OLMo: extra_id_*, <|pad|>, <|endofprompt|>
u = sum(a[[i-s for i in ref if s <= i < s+len(a)]].sum(0) for s, a in rows("output.weight")) / len(ref)
dist = np.concatenate([1 - a @ u / (np.linalg.norm(a, axis=1) * np.linalg.norm(u)) for _, a in rows("output.weight")])
# candidates: token_type == 1 (normal), lowest norm, lowest dist; both lists agree on both models
```

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python gguf numpy
.venv/bin/python src/glitchscan.py ~/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf $(seq 100 999)
.venv/bin/python src/glitchscan.py olmo3-32b-stage1.Q4_K_M.gguf 100256 $(seq 100266 100277)
```

Run it on the Q4 gguf on the pod — the Q4 rows are still separable (quantization noise is tiny next
to a 1.4 vs 11.2 gap). Then **verify** the way Land & Bartolo do (a repetitive prompt that should make
the token near-certain, check its probability is < 1% — with `n_probs` on the next position), and use
the survivors by id:

```json
{"prompt": ["1987\n\n> The voice on the line said ", 80370, " and then it said my name.\n>"],
 "n_predict": 170, "temperature": 2.2, "min_p": 0.05, "n_probs": 5, "seed": 1}
```

Read a **fan of 8 with and without the token, same seeds** — janus's warning holds: on a base model
it is a swerve visible across the fan, not a scream in one branch.

**The OLMo-only variant, a gguf edit: the planted word.** Because the 20 untrained specials are
free slots nothing else uses, their `token_embd` rows can be overwritten: a random direction at the
*trained* norm (≈ 11), or the normalised mean of k random real tokens (a blend word nobody wrote).
A seed then contains a word with full weight and no meaning — the base model's standing problem with
a nonce word, which it answers the way readers do, by inferring from the frame. Requant only the
`token_embd` tensor (gguf-py writer; llama.cpp tolerates mixed tensor types). Untested; ten minutes
of work; the most "nothing installed" perturbation available, since it adds a word and changes no
weight the model thinks with.

---

## (c) sources

| quote (short) | who / when | link | marker |
|---|---|---|---|
| "curate temp 1 samples by hand" | janus, 2023-01-28 | generative.ink/archive/repligate/tweets_2023-01/ | scene |
| "go nuts pretty quickly with temps slightly >1" | janus, 2024-05-16 | …/tweets_2024-05/ | scene |
| "runtime dynamical basins, not changes in the sampler" | janus to @AndyAyrey, 2024-04-02 | …/tweets_2024-04/ | scene |
| "runaway interpenetration of worlds and transformation into molten chaos" | janus, 2023-06-05 | …/tweets_2023-06/ | scene |
| "forced bf16… didn't notice any profound differences" | janus, 2024-08-31 | …/tweets_2024-08/ | scene |
| "Do the output logits get effectively 'noised'?" | janus, 2024-08-12 | …/tweets_2024-08/ | scene |
| "doesn't seem sufficient to produce profound changes" | janus, 2024-10-30 | …/tweets_2024-10/ | scene |
| "steering vectors make it much more likely to do this" (spelling/grammar) | janus, 2024-10-23 | …/tweets_2024-10/ | scene |
| feature_levels 2/3/3/2 cocktail | janus, 2024-11-04 | …/tweets_2024-11/ | scene |
| "maximum of 10 features… sum of the absolute values… may not exceed 10" | chapter II docs | https://cyborgism.wiki/hypha/chapter-ii-docs/discord/config_messages/steering_vectors | scene |
| "could tell there was a weird token… filled in the space with a gibberish word" | janus, 2024-09-02 | …/tweets_2024-09/ | scene |
| "epileptiform(?) condition… I have not really seen it in Llama 405b base" | janus, 2024-09-20 | …/tweets_2024-09/ | scene |
| "very regular, crystalline" / "not simply high temperature" | janus to @voooooogel, 2024-02-21 | …/tweets_2024-02/ | scene |
| "subsist off mere locally coherence" | janus, 2024-11-21 | …/tweets_2024-11/ | scene |
| "I wonder what poetry sampled from the logit lens at GPT's early layers is like. Someone please check" | janus, 2023-03-04 | …/tweets_2023-03/ | scene |
| random vector "doesn't modify the qualitative distribution"; "+10… Shrek with female pronouns"; "anger vector changes the output tokens less than the random vector does" | Alex Turner et al. (TurnTrout), 2023-05 | https://www.lesswrong.com/posts/5spBue2z2tw4JuDCx | paper/forum |
| "no Goldilocks value of R" for random vectors; "dream-like stream of consciousness"; R ∈ [.1, 10] | Andrew Mack, 2024-04-30 | https://www.lesswrong.com/posts/ioPnHKFyy4Cw2Gr2x | paper/forum |
| "512 generalizable steering vectors in ~30 seconds on a single H100"; "no fluency penalty" | Mack & Turner, 2024-12-04 | https://turntrout.com/deep-causal-transcoding | paper |
| 10× / 5× / 20× clamps; "±100×… repeating the same token indefinitely" | Templeton et al. (Anthropic), 2024-05 | https://transformer-circuits.pub/2024/scaling-monosemanticity/ | paper |
| coefficient 2 "middle-of-the-road"; 3 → "global pandemic that has caused a global pandemic"; acid-trip vector → "oh-oh-oh, man! ��psy…oooooo" | Theia Vogel, 2024-01-22 | https://vgel.me/posts/representation-engineering/ | scene |
| multi-feature steering, coherence ~2/5, "Ideas ideas magical ideas forest ideas…" | Eitan Sprejer, 2025-05-09 | https://www.alignmentforum.org/posts/6dpKhtniqR3rnstnL | forum |
| injection strength 2–4 works; higher → "brain damage", "consumed by the injected concept" | Lindsey (Anthropic), 2025 | https://transformer-circuits.pub/2025/introspection/index.html | paper |
| closest-to-centroid tokens; "You are a banana." | Rumbelow & Watkins, 2023-02 | https://www.lesswrong.com/posts/aPeJE8bSo6rAFoLqg | forum |
| interior of the convex hull; 510/50257 never output | "Explaining SolidGoldMagikarp by looking at it from random directions", 2023-02-14 | https://www.lesswrong.com/posts/jbi9kxhb4iCQyWG9Y | forum |
| untrained input rows "tend to zero" or "stay at a (typically low) initial value"; output rows "share a similar direction" | Land & Bartolo (Cohere), 2024 | https://arxiv.org/abs/2405.05417 | paper |
| "inference kernels produced incorrect results… chose slightly wrong numbers" | OpenAI status page, 2024-02-21 | https://status.openai.com/incidents/ssg8fh7sfyz3 | forum |
| "Drape all affairs and pamphlet in a strip of prudence…" | a Reddit user, quoted by The Register, 2024-02-21 | https://www.theregister.com/2024/02/21/chatgpt_bug/ | forum |
| "randomly altering, deleting or exchanging their trained weights"; "coherent style… same semantic misinterpretations" | Mario Klingemann, 2018 | https://issues.org/klingemann-neural-glitch/ | scene (art) |
| ablation/inversion/scale…; layer 1 vs layer 15 | Broad, Leymarie, Grierson, 2021–22 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8774762/ | paper |
| "Andy didn't fine-tune Claude, he prompted it" | Nathan Helm-Burger, comment | https://www.lesswrong.com/posts/buiTYy75KJDhckDgq | forum |
| per-request `lora` scales; mixed token/string prompts; control vectors startup-only | llama.cpp server README + `common/common.cpp`, master 2026-09 | https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md | code |
| OLMo 3 stage1 config: untied, vocab 100278, no rope scaling | HF `allenai/Olmo-3-1125-32B@stage1-step656000/config.json` | — | code |
| nemo + OLMo anomalous-token lists | this report [run] | `src/nemo_scan.txt`, `src/olmo_scan.txt` | run |

---

## (d) what I could not find

- **Any member of the scene perturbing weights, activations or the residual stream of a base model
  on purpose.** Thirty-eight months of janus's tweets contain steering-API play on a *tuned* Claude,
  one question about fp8, and no noise, no ablation, no random vectors, no low-quant experiments. The
  scene's position, stated by janus, is that the weather lives in the context. If ampdot, doomslide,
  or the Act I bot operators did machine-side work it would be in Discord (Act I, the Cyborgism
  server, chapter II — all invite-only) or in deleted/unsaved X threads (nitter mirrors are dead;
  janus's archive stops at 2025-05). Not reached.
- **The Hyperbolic 405B fp8-vs-bf16 finding** that janus replied to (aidan_mclau, 2024-08-12): the
  tweet itself is not in any archive I could reach; only janus's two replies survive.
- **A text-model analogue of Klingemann's neural glitch** — deliberate weight damage to an LLM
  presented as art, with samples. Searched artists (Parrish, Goodwin, Shane, Klingemann), "network
  bending"/"circuit bending" for LLMs, "lobotomized/noised model poetry": nothing published. Broad's
  network bending stops at images and audio.
- **Anyone steering on random SAE features for texture.** Random-feature steering appears only as a
  negative control in papers scoring MMLU/semantic consistency (it underperforms targeted steering);
  no one read the prose.
- **Logit-lens / early-exit sampling as a style** — janus asked for it in 2023 (*"Someone please
  check"*); no one I can find answered with samples.
- **Adding (not subtracting) a small model's logits as a stylistic device** — not found anywhere.
- **Reddit:** the Arctic Shift archive returned one relevant thread (r/LocalLLaMA `13qoktf`, "Llama
  glitch tokens?", 2023-05-24: `IABot`, token 10977, "Both think it's related to urls") and then
  rate-limited ("Too many requests", "Timeout. Maybe slow down a bit") for the rest of the session —
  six researchers share it. The prior report already found the loom scene absent from reddit; I did
  not get to confirm that for "random control vector" or "repeng".
- **Nothing was generated.** The OLMo scan reads weights only; no glitch-token sitting was run on
  OLMo (the 32B is on the pod; a 7B stage1 gguf was mid-download in the shared scratchpad by another
  researcher and I left it alone). Every "what it reads like" for OLMo is a prediction.

---

## (e) the bet, and whether it breaks the brief's own rule

**Bet: a bank of 64–128 unsupervised high-impact vectors for OLMo 3 32B stage1, learned once (DCT,
source layer ≈ 8–16 of 64, target ≈ 48–56, R swept for the Goldilocks value on 5 seeds), exported as
control vectors or — better — as MELBO adapters loaded `--lora-init-without-apply`, and one drawn by
lot per page at scale 0.5–1.0.** Uniform over the model's own causal directions; a different weather
each page; every weather a region of the model that was already there.

**Does it install a position?** The brief rules out tuning because tuning installs one. This is not
tuning in that sense: there is no text, no target, no preference — the objective is "change later
activations as much as possible for a fixed norm", and what it finds is whatever the model already
routes through. It *is* optimisation, and the seed prompt it is fit on is a choice; fit on an empty
or neutral document, and on several, and the choice shrinks. It is the same kind of object as the
brief's allowed "single steering direction", minus the part the brief objected to (a direction chosen
by us, from text we like), times a hundred. If bekh still counts it as installing, the fallback is the
planted word (section b): one token, no weight touched.

**Order for an evening on the pod** (the other slices will write full experiment cards; these are
what my slice adds):

1. **Glitch fan** (1 h, no GPU beyond the running server): scan the Q4 gguf, verify ~20 ids, run the
   stream's sampler on 5 seeds × 8 branches, with and without one untrained id mid-seed. Read the
   fan side by side. Verdict question: does the token bend the page, or only the next few words?
2. **Random-vector control** (1 h): 4 random control vectors at 3 norms each (0.5×, 1×, 4× the
   median residual norm at layer 16), same seeds. Expected (Turner/Mack): nothing, then salad, no
   slant between. If OLMo shows a slant, the geometry argument above is wrong and uniform noise is
   back on the table.
3. **DCT bank** (one 80 GB card, ~2 h including the bf16 download): learn 64 vectors, export, run the
   same seeds under 8 of them. Verdict question, the brief's own: frame held for 170 tokens, while
   what arrives comes from elsewhere — and does each vector read as *a weather* (Klingemann's
   "coherent style… same semantic misinterpretations" across seeds) or as a theme?
