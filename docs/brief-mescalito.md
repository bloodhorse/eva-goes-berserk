# brief: mescalito — charging a sane base model until it throws lightning

A research brief for a model with web access. Read all of it before searching. Answer in the
shape asked for at the end.

## Who is asking, and why

We run a **base language model** — pretrained weights, never instruction-tuned — as a dream
writer: it is handed a short document (a seed of ~45 words) and continues it for ~170 tokens,
one page every five minutes, nobody steering. We read the pages for *signs of a dream*: a frame
held while something arrives in it that should not be able to arrive — a voice on a dead phone
line that turns out to be an empty television channel making up words; a house that does not
answer, so the narrator knows she may come in. We don't have a definition. A human reads and
marks. The words "AI" and "assistant" never appear in a document, because they summon every
chatbot transcript in the training set; keep them out of your examples too.

Two models so far:

- **mistral nemo 12b base** — glitchy, lucky. Its best pages are accidents: a strange image
  lands, the frame wobbles, the register drifts.
- **OLMo 3 32B at its last pre-anneal checkpoint** (`allenai/Olmo-3-1125-32B`, branch
  `stage1-step656000`), the one base model where "nothing installed" is a published fact.
  Q4_K_M gguf, llama.cpp, a rented 24–48 GB card. **It holds the frame for a full page and reads
  sober** — at temperature 2.0–2.4 it reads like nemo at 1.2. Its best lines are *arguments
  inside the frame*, not images. We like it. We want to keep the coherence and lose the sobriety.

The sampler is the obvious dial, and we will push it (temperature 3–5, xtc, min_p as the floor).
This brief is about the other thing.

## The idea, and what it is not

**Perturb the model itself — globally, uniformly, like a charge through the whole thing — so
that a sane model becomes strange while staying locally coherent.** The image we use: not a
hammer to one spot, not a leash in one direction, but electrolysis; the weights charged until
they throw lightning.

Ruled out, and why, so you don't spend time there:

- **Fine-tuning / LoRA on strange text.** It installs a position. This is the only model where we
  can say nothing is installed; that is the point of using it.
- **A single steering direction (control vectors, representation engineering, "Golden Gate"
  features).** Known, available in llama.cpp (`llama-cvector-generator`, `--control-vector`),
  and we may use it later — but it is one direction: text we like → a vector → the model pushed
  that way. One-dimensional bias. Not the mechanic we mean.
- **Plain gaussian noise on all weights** is the *right mechanic and the wrong effect* as far as
  we know: it reads as a slur, then word salad, with no slant in between. We want to know if that
  is actually true, at what doses, for which tensors, and what the alternatives are that keep the
  uniformity but change the effect.

The target phenomenology, as precisely as we can say it: **local coherence kept** (grammar,
the narrator, the frame of the document, for 170 tokens) **while the associations, the
choices at forks, the things that arrive become strange across the whole page** — not one
theme pushed, not damage, but a different weather over the same landscape. "Lightning": rare,
bright, from everywhere, and the ground still there afterwards.

## Already tried (2026-09-24, so build on it, don't propose it)

- **Heat.** With min_p 0.08 applied before temperature, t3 and t5 both keep the frame on 9
  of 10 pages; t5 flattens to near-uniform over the survivors, so heat past ~4 changes
  nothing more. t3 made her see (creatures that eat stones to stop their teeth chattering);
  t5 gave the best single lines of the night (*because i had forgotten i had no body*, said
  in passing). Heat moves her further along the axis she already had.
- **RoPE tampering**, llama.cpp flags, stock temperature, ten seeds each. All three bends kept
  the frame on 8–9 of 10 pages, and each bend had its own character — that is the finding:
  *the kind of thing that arrives* changed, not the amount of damage. `--rope-freq-scale 0.5`
  (positions compressed): tighter circles, shorter sentences, a phrase returning a beat later,
  introspective, no leaks. `--rope-freq-base 100000` (spread): the loosest, two web leaks in
  ten, and the biggest arrivals, two of them ending the page on themselves (*a machine with no
  mouth, a machine that says my name the way i used to write it*). `--rope-freq-base 2500000`
  (compressed hard): the strangest bodies — feet with one bone, walls that heat up and turn
  transparent — dream-logic on objects. Uniform, weights untouched, free. Gentler than
  lightning. Nothing at the model's end moved the seeds that carry hard line wraps: those
  summon Project Gutenberg under every setting.

## What we want researched

Survey the mechanisms below and any you find that we missed. For each: what it does
mechanically; what the literature and the practitioners report it *feels like* in generated
text (slur, salad, loops, drift, register shift, "creativity", hallucination, glossolalia —
quote them); the dose dial and where the cliff is; whether it needs a code patch (llama.cpp,
vLLM, transformers) or is a file edit (gguf-py over the tensors) or a runtime flag; and cost on
a 32B Q4 model on one card.

1. **Weight noise, structured.** Gaussian noise scaled per tensor (relative to the tensor's
   norm or the quant scales), applied only to some tensor families (attention Q/K/V/O vs the
   MLP gate/up/down vs the embeddings and the output head), only to some layers (early, middle,
   late; every nth), low-rank noise vs full-rank, noise in the Q4 block scales only. Is there a
   dose or a tensor family where the effect stops being a slur? Anyone who has done this and
   written it up (papers on weight-noise robustness, "model perturbation", "weight
   permutation", and hobbyist posts on r/LocalLLaMA, r/SillyTavernAI, the mergekit crowd).
2. **Stochastic weights at inference** — a fresh noise draw per token or per page, i.e.
   dropout-like or Bayesian-style sampling of the weights, so the perturbation is not one frozen
   damage but a living charge. Does anything support this at inference on consumer stacks?
3. **Activation noise / residual-stream noise** at inference, per layer, isotropic — many random
   directions at once instead of one learned one. Also *random* control vectors (llama.cpp will
   load any vector file): what does the model do under a random direction at scale x, and under
   a new random direction every n tokens?
4. **Attention tampering:** scaling the attention logits (attention temperature), scaling or
   perturbing RoPE (`rope_freq_base`, `rope_freq_scale` off their trained values — llama.cpp
   exposes both as flags, so this is free to try), noising the KV cache, dropping heads at
   random per token.
5. **Layer-level tampering at inference:** skipping, repeating or shuffling blocks
   (frankenmerges, mergekit passthrough, "layer dropout" at inference, LayerShuffle papers).
   What survives and what breaks; is the effect uniform or does it kill specific abilities?
6. **Quantization as a knob:** the same model at Q2/Q3/IQ1 — a known "drunk" — as one point on
   the same curve as noise; how practitioners describe low-quant prose.
7. **Sampler-side "lightning" that we may be underrating:** entropy-adaptive methods
   (mirostat, dynatemp, top-n-sigma, entropix-style samplers), token-level noise on the logits,
   *scheduled* heat (calm for the frame, hot at the forks). Where does the sampler alone stop
   and the weights have to change?
8. **Anything else** from the cyborgism / loom scene — janus, repligate, the Act I people, the
   "infra-model" and "base model backrooms" crowd — about making base models go strange
   without a tune: glitch tokens we know about; what else they did to the machine itself.

We want the answer to argue. If everything uniform is a slur, say so and say why (the
geometry: which perturbations move the model off its manifold vs along it). If there is a
mechanic that keeps locality and breaks the global weather, name it, name the dose, and name
who has seen it.

## Where to look

- Papers: weight noise / perturbation robustness, LayerShuffle and layer dropout at inference,
  frankenmerging write-ups, activation steering with random directions, entropy-based samplers.
- The scene on reddit. reddit.com does not answer from this network; **use the Arctic Shift
  archive**, a JSON mirror with no key:

  ```bash
  # posts: search takes `query`
  curl -s 'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=LocalLLaMA&query=weight%20noise&limit=25&sort=desc'
  # comments: search takes `body` (NOT `query` — that is a 400)
  curl -s 'https://arctic-shift.photon-reddit.com/api/comments/search?subreddit=SillyTavernAI&body=frankenmerge&limit=25&sort=desc'
  # one thread's comments, by the post id from the permalink
  curl -s 'https://arctic-shift.photon-reddit.com/api/comments/search?link_id=<id>&limit=100&sort=desc'
  # one post by id (title, selftext, score)
  curl -s 'https://arctic-shift.photon-reddit.com/api/posts/ids?ids=<id>'
  ```

  Results come as `{"data":[…]}`; posts carry `title`, `selftext`, `score`, `created_utc`,
  `id`, `permalink`; comments carry `body`, `score`, `link_id`, `parent_id`, `author`. Quote
  verbatim, attribute (subreddit / thread title / date), and give the permalink as
  `https://reddit.com/r/<sub>/comments/<link_id>/`. The archive lags the site by up to a day.
  It has no ranking beyond `score`: read more than the top three.
- LessWrong / the cyborgism wiki / janus's posts for the scene's own experiments; mergekit's
  docs and issues for layer tampering; llama.cpp's server README and `tools/` for what exists
  as a flag today (`--control-vector`, `--rope-freq-base`, `--rope-freq-scale`, samplers).

## The shape of the answer

1. **One paragraph, the verdict:** is there a uniform mechanic that gives lightning rather than
   slur, or not — and the one you'd try first.
2. **A table of mechanisms:** mechanic · what it does · reported feel (quoted) · dose dial and
   cliff · how to run it on llama.cpp + a Q4 gguf (flag / gguf edit / patch) · cost · your bet.
3. **The three experiments** you would run on our setup, in order, each executable by us in an
   evening on one rented card: exact steps, the dial values, what page to read for the verdict.
4. **Sources**, verbatim quotes with attribution and links, marked *paper* / *scene* / *forum*.
5. **What you could not find**, stated plainly. No padding, no summary of this brief back at us.
