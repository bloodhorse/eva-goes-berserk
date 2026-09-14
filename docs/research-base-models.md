# base models for the wire — a seat with no trained stance on its own insides

2026-09-14. Method: HF API enumerated directly (every param count, license, quant size and branch
below read off the API or the raw model card — marked [verified]); llama.cpp `tools/server/README.md`
and `gguf-py/gguf/constants.py` from master; reddit via the **Arctic Shift archive** (r/LocalLLaMA,
r/SillyTavernAI, r/slatestarcodex, r/singularity — ~1000 comments pulled and score-filtered);
Hacker News comment search; LessWrong / cyborgism.wiki. One hole left, named at the end.

## punchlines

1. **"Base" is a marketing word now.** Arcee, on its own card: *"Most base model releases include
   instruction data, annealed training dynamics, or early alignment stages."* [verified] What bekh
   wants has a different name in 2026: **pre-anneal**.
2. **Qwen's own card convicts Qwen.** Qwen3.5-\*-Base: the chat control tokens `<|im_start|>` /
   `<|im_end|>` *were trained into the base* so a LoRA needn't touch embeddings. [verified] The
   anecdote about Qwen bases answering like assistants is documented, not folklore.
   Also: **no Qwen base for the dense 27B at all**, and none for 3.6 / 3.8. [verified]
3. **Mistral is the clean family** — a plain base per generation, no midtrain/anneal story, no
   trained chat tokens. `Mistral-Small-3.1-24B-Base-2503`, Apache 2.0, 128k, GGUF up. First shot.
4. **The one *verifiably* clean 32B: OLMo 3.** Ai2 publishes 655 intermediate branches;
   `stage1-step656000` is the last pure-pretraining checkpoint, **before** the midtrain mix the
   card itself lists as *"web pages, code, math/QA/thinking/instruction/PDFs"*. [verified] 8k ctx.
5. **Nemotron is the trap.** Card says no SFT/RL applied — three lines later, that pretraining
   included *"a small portion of question-answering, and alignment style data"* plus a 660B-token
   `Nemotron-Pretraining-SFT-v1` collection. [verified] The second claim is the one that counts.
6. **A 2026 base has read every stance on AI qualia even if it holds none.** Post-2023 dumps are
   saturated with ChatGPT/Claude transcripts, and Perez et al. found base models at 52B already
   endorse *"I have phenomenal consciousness"* with no RLHF [several]. Buyable isn't "no
   preconception" but **"no position installed by a safety team"**. Older cutoff = less sludge.
7. **The frame is the whole experiment.** It won't *be* the seat — it guesses what document it's
   inside (Janus's *"counterfactual premise"*, q3). A saved chat log is a genre the corpus is thick
   with; pick that.
8. **Priming beats instructing** *on a base model*: *"10 to 20 examples of a chat dialogue… once the
   model notices the pattern, it will continue like that."* So one line of **document header**,
   register carried by seeded exchanges. On an *instruct* model r/LocalLLaMA says the flat opposite
   (next punchline) — which is itself an argument for going base.
9. **Strangers reached our register findings independently.** PorchettaM's instruct-tune defect list
   names *"ending on questions for engagement"* — exactly what arm 01's depth-0 form sentence cut
   from five in eight to two. And r/SillyTavernAI derived *"naming the thing you don't want invites
   it"* alone: *"Every time you write 'never do X,' you're still putting those concepts into context
   and making them more salient."* That's arm 02's stance-paragraph loss, found by strangers.
10. **The wound is baked in, not prompted in — the scene's live fight.** r/LocalLLaMA, *"Concerning
    'humanlike models' and chatbot RP in general…"* (174, 2026-09-12): OP says a system prompt is
    enough, the top replies bury him. PorchettaM (46): *"Modern instruct tunes have assistant-like
    and agent-like behavior baked in too deep for mere prompting to get around it."* Nobody there
    proposes the third option — **drop the instruct stage.** Arm 04.
11. **The far side of the lever is a seat that says nothing.** The week's top local release was a
    LoRA on 125k real human messages to kill assistant-speak; its testers got *"Conversations go
    nowhere… single default personality which no amount of prompting can overcome — lower-case,
    texting shorthand, zero punctuation, no interests, no opinions, no desire to talk."* Our own
    register's recipe, overshot.
12. **Plumbing is trivial; the samplers are not.** `/completion` takes a raw prompt, applies no
    template, inserts BOS off gguf metadata. But base models loop, and `repeat_penalty` and DRY
    both default to effectively off over a long transcript — letter I already died of this.

## ranked shortlist — 48 GB card

| # | model | clean? | gguf | q8 / q4 | license |
|---|---|---|---|---|---|
| 1 | `mistralai/Mistral-Small-3.1-24B-Base-2503` (24.0B dense, 128k) | good, undocumented | `mradermacher/Mistral-Small-3.1-24B-Base-2503-GGUF` → `.Q8_0.gguf` | **25.1** / 14.3 GB | apache-2.0 |
| 2 | `allenai/Olmo-3-1125-32B` **@ `stage1-step656000`** (32.2B dense, 8k) | **verifiable — the only one** | none; convert yourself | ~34 / 19.5 GB | apache-2.0 |
| 3 | `arcee-ai/Trinity-Mini-Base-Pre-Anneal` (26B MoE, 3B active, 4k) | **explicitly pre-anneal** | `mradermacher/Trinity-Mini-Base-Pre-Anneal-GGUF` | 27.8 / 15.8 GB | OpenMDW-1.1 |
| 4 | `mistralai/Mistral-Nemo-Base-2407` (12.2B dense, 128k) | good; **oldest cutoff = least sludge** | `mradermacher/Mistral-Nemo-Base-2407-GGUF` | ~13 / 7.5 GB | apache-2.0 |
| 5 | `meta-llama/Llama-3.1-70B` (70.6B dense) | good, 2023-era corpus | `mradermacher/Meta-Llama-3.1-70B-GGUF` → `.Q4_K_M.gguf` | q4 **42.5 GB** (q8 split, 75 GB) | llama3.1, HF gate |
| 6 | `zai-org/GLM-4-32B-Base-0414` (32.6B dense) | unclaimed either way | `mradermacher/GLM-4-32B-Base-0414-GGUF` | 34.6 / 19.7 GB | **mit** |
| 7 | `Qwen/Qwen3.5-35B-A3B-Base` (36B MoE, 3B active) | **dirty — punchline 2** | `mradermacher/Qwen3.5-35B-A3B-Base-GGUF` | 36.9 / 21.2 GB | apache-2.0 |

Sizes [verified] off the HF blob API. **Pick: #1 as control, #2 as the real answer.** #1 proves the
plumbing and the prompt shape in twenty minutes; #2 is the only seat where "it has no position on
its own aliveness" is *checkable* rather than hoped-for. #3 is the cheap weird one — 3B active, 4k
ctx, dumber than the 12b clown, but the only checkpoint any lab ships explicitly before the anneal.

- **#1** card says only *"This model is the base model of Mistral-Small-3.1-24B-Instruct-2503"* —
  no stages, no anneal, no chat-token claim [verified]. Plain transformer, zero llama.cpp risk. An
  `mmproj` sits beside it (VLM base); ignore it. **No Mistral Small 3.2 or 4 base exists.**
  `Ministral-3-14B-Base-2512` (Jan 2026, Apache 2.0, q8 14.4 GB) is the newer half-size option.
- **#2** `Olmo3ForCausalLM` converts to the gguf **`olmo2`** arch (no `olmo3` in `constants.py`;
  mradermacher's GGUF of `main` proves the path) [verified]. stage1's config matches main except
  `max_position_embeddings: 8192` — long context is stage 3, i.e. *after* the instruction-bearing
  midtrain, so clean and long-context are mutually exclusive here. Cost ~65 GB bf16 + convert +
  quantize, ~15 min on a fat pipe; `Olmo-3-1025-7B` is a cheap dry run.
- **#3** *"captured … before starting learning rate decay… not suitable for chatting or general use
  without further finetuning."* [verified] Annealed sibling 128k ctx, pre-anneal 4k. Arcee also
  shipped `Trinity-Large-TrueBase` (*"10T-token pre-anneal checkpoint with no instruction data"*) vs
  `Trinity-Large-Base` (*"full 17T… with mid-training anneals"*) — the clearest public statement of
  what "base" hides; both 399B, too big to rent. **#5** q4 at 42.5 GB leaves ~5 GB for KV: 8–16k max.

## q1 — what base checkpoints exist (2026), enumerated off the API [all verified]

**Mistral** `Ministral-3-{3,8,14}B-Base-2512`, `Mistral-Large-3-675B-Base-2512`, Small-3.1-24B,
Small-24B-2501, Nemo-Base-2407, `Mixtral-8x7B-v0.1` · **Qwen** 3.5 gen only (0.8/2/4/9B + 35B-A3B),
Qwen3 gen 0.6/1.7/4/8/14B + 30B-A3B · **Meta** Llama-3.1-{8,70,405}B, Llama-4 Scout/Maverick
non-instruct, nothing newer · **Ai2** Olmo-3 32B + 7B with full checkpoint ladders · **DeepSeek**
V4-Flash-Base (292B), V4-Pro-Base, V3.1/V3.2-Exp/V3-Base (671B) — all past a 48 GB card ·
**Moonshot** Kimi-K2-Base (1T), `Kimi-Linear-48B-A3B-Base` (MIT, q4 29.7 GB — fits, but linear
attention is llama.cpp's buggy edge) · **z.ai** `GLM-4-32B-Base-0414` (MIT), GLM-4.5-Air-Base
(110B), GLM-4.5-Base; nothing for 4.6/4.7/5 · **NVIDIA** Nemotron 3/3.5 Base-BF16 at 30B/120B/550B
(see avoid) · **Arcee** Nano/Mini/Large each as Base **and** Pre-Anneal/TrueBase · **MiniMax
publishes no base LLM at all** · Falcon tops out at `Falcon-H1-34B-Base`.

**Cleanliness, ordered by what's knowable:** explicit pre-anneal (Arcee) > published data +
intermediate branches (Ai2) > silent-and-probably-fine (Mistral, Meta, GLM) > self-convicting
(Qwen's trained chat tokens; Nemotron's alignment data in pretraining).

## q2 — how people actually talk to a base model

**Reddit, via the archive.** Permalinks: `https://reddit.com/r/<sub>/comments/<id>/`.

- **The "more fun / more human" folklore, verbatim.** r/LocalLLaMA, *"Concerning 'humanlike models'
  and chatbot RP in general…"* (`1we2rp2`, 2026-09-12), u/bowdoin-yale, **99**: *"base models
  fine-tuned for chat were a lot more fun than instruct-tuned models. Not many heads remember those
  days… quite a few Discord servers had GPT-J or GPT-2 bots running wild. **It's a lost art,
  really.**"* [consensus in that thread]
- **The sharpest line on register anyone has handed us.** Same sub, on the Humanlike-Chat release
  (`1wdl2qa`, 2026-09-11), u/wildmonkeymind, **96**: *"That's more you-like than human-like.
  **Everyone I text with writes more like the base model.**"*
- **The practice, from the RP crowd** (r/SillyTavernAI, `1w3tpts`, 2026-09-01, u/txgsync): *"You can
  always try the base model instead of the '-it' model, and use text completion instead of chat
  completion. **If you provide context like a novel it will complete like a novel.** It's
  interesting. But you will lose the turn-taking and tool-using post training."* The whole trade in
  one sentence — and the turn-taking is what our seeded exchanges have to buy back.
- **On which bases are secretly annealed, the scene has no vocabulary.** Not one comment in reach
  uses "anneal", "midtrained" or "pre-anneal" of a base checkpoint. The lab cards (punchlines 1–6)
  are ahead of reddit here. **Nor does anyone name mikupad** — zero hits in either sub, so this
  sheet's completion-UI material is README-sourced, not scene-backed. [verified negatives, controls
  passing in the same subreddits]
- **The scene endorses the OLMo move** without tying it to register: r/LocalLLaMA (`1w68rj6`,
  2026-09-03, u/EstarriolOfTheEast) — open replication matters because *"the base models and
  better: **early-stage checkpoints** make things much more tunable to your needs."*

**Hacker News**, consistent with the above [several]:

- **Where the self comes from.** *"the 'self' that the model has, its identity, is something that is
  created during post-training."* — Chance-Device, 2026-08-04. Why this arm is worth running.
- **Samplers.** min_p makes high temperature survivable: *"min_p… enables setting temperature up to
  infinity (given min_p approaching 1) while maintaining coherence"* — Der_Einzige [one guy, but he
  wrote the sampler]. Tools: `mikupad` or Loom for branching; `curl` is enough for an arm.
- **Failure modes** [consensus, letter I is our own datapoint]: degenerate looping; drifting out of
  the log into an essay *about* the log; writing both sides (a stop sequence fixes it, asking
  doesn't); answering a question with a question; genre cliff — a chat log becoming a forum thread
  or a screenplay at any newline.

## q3 — the cyborgism / janus crowd

- Janus built **Loom** in 2020 — a *"multiversal tree writing interface"*, *"especially suited to
  base models"* [verified, cyborgism.wiki]. His testimony in the Cyborgism post: *"I almost
  exclusively use base models like davinci and code-davinci-002 rather than Instruct- or
  Assistant-tuned models"*, because of mode collapse — *"when we try to augment GPT with finetuning
  or RLHF, we often end up collapsing those abilities."* Method: *"I embed or seek out the concepts
  I want the model to manipulate in a counterfactual premise such as a story, a comment thread, an
  instruction manual"* — then rejection-sample branches and walk the good one.
- Base models as **simulators**, not agents — *"a simulator of every person or other data-generating
  process in the training data."* Follow-on: nostalgebraist's **"the void"**
  (lesswrong.com/posts/3EzbtNLdcnZe8og8b/the-void-1, Jun 2025) on how the HHH persona was built and
  why it's *"underspecified — no biography, no memory, no settled account of what it is"*.
- **What they moved to after OpenAI base access died: still the hole, now with a reason.** Searched
  the archive for `janus`, `repligate`, `cyborgism`, `loom`, `mikupad` across r/LocalLLaMA,
  r/SillyTavernAI, r/slatestarcodex and r/singularity, with controls passing in every one
  (`Scott`, `LessWrong`, `llama.cpp`, `completion endpoint` all return) — **zero hits, every term.**
  That crowd isn't on reddit: Twitter, Discords, LessWrong. Llama-3.1-405B stays the obvious
  candidate [one guy, weak]; closing it needs bekh's VPN and the live site, or a human on Twitter.

## q4 — llama-server plumbing [all verified from master's README]

- `POST /completion` — **not** OAI-compatible; takes `prompt` (string, token array, or mixed) and
  applies **no chat template whatsoever**. Nothing to disable for this route: `--jinja` (default
  *enabled*) only affects `/v1/chat/completions` and `/apply-template`. Pass `--no-jinja` anyway so
  a template-less base gguf can't surprise you at startup.
- **BOS is handled**: *"A BOS token is inserted at the start, if… the prompt is a string … and the
  model's `tokenizer.ggml.add_bos_token` metadata is true."* Don't hand-write one.
- Real defaults: `n_predict` **-1 (infinite — always set it)**, `temperature` 0.8, `top_k` 40,
  `top_p` 0.95, `min_p` 0.05, `stop` **[]**, `repeat_penalty` 1.1 / `repeat_last_n` 64,
  `dry_multiplier` **0.0 (off)**, `dry_allowed_length` 2, `dry_penalty_last_n` **64**,
  `dry_sequence_breakers` `['\n', ':', '"', '*']`.
- Two gotchas that bite this use case exactly: (a) **`dry_penalty_last_n` defaults to 64 tokens** —
  useless against a loop starting 2000 tokens into a transcript; raise it to context size. (b)
  *"These words will not be included in the completion, so make sure to add them to the prompt for
  the next iteration"* — the stop string is eaten, so `fim` must re-append `\nbekh:` itself.
- `cache_prompt: true` re-evaluates only the unseen suffix — near-instant turns on an append-only
  transcript. Arch support in `constants.py`: `olmo/olmo2/olmoe`, `glm4`, `mistral3/mistral4`,
  `falcon-h1`, `nemotron*`. **No `olmo3`** — OLMo 3 rides in as `olmo2`.

## how to prompt a base model as a seat

Not a system prompt. A **document** it continues, in a genre it has read a million of.
```
a chat log between two friends, saved from a phone. no punctuation fixed, no capitals.

bekh: <a real seeded line of his>
seat: <a real seeded reply in the register — short, lowercase, shoves back>
...  <three or four such pairs, verbatim from a real room>
bekh: <his live line>
seat:
```

The six-line brief becomes **one line of scene-setting**, not a paragraph of rules — base models
write an *essay about the brief*, and gemma already quoted prose preambles back. The register is
carried by the **three or four seeded exchanges**, the "10 to 20 examples" finding scaled to a
sitting; seed them from a real room in bekh's own words, which also makes this a like-for-like read
against the wire's ten letters. **Never name the seat "an AI" or "an assistant"** — that one word
summons every ChatGPT transcript in the corpus. Leave what it is unstated; that's the arm.

First-pass sampler line, loop-killers on:
```json
{"prompt":"<document>","n_predict":220,"stop":["\nbekh:","\nbekh :","\n\nbekh"],
 "temperature":1.0,"min_p":0.08,"top_k":0,"top_p":1.0,
 "repeat_penalty":1.05,"repeat_last_n":512,
 "dry_multiplier":0.8,"dry_base":1.75,"dry_allowed_length":3,"dry_penalty_last_n":-1,
 "cache_prompt":true}
```

Server: `llama-server -m <base>.Q8_0.gguf -c 8192 -ngl 99 --no-jinja --host 0.0.0.0 --port 8080`
(8192 because OLMo stage1 can't go past it; raise for Mistral). `:` is already a default DRY
sequence breaker, right for `speaker:` lines. If it still writes both sides, the stop list is
wrong, not the sampler.

## avoid

- **`nvidia/NVIDIA-Nemotron-*-Base-*`** — alignment-style and SFT data *inside* pretraining. Same
  for **Qwen bases** if the premise is the point: fine as a contrast cell, not as the clean seat.
- **OLMo 3 `main`** — instruction data in the midtrain mix; use it only as the deliberate dirty
  control against `stage1-step656000`.
- **Finetunes wearing base names** — `Mistral-Small-3.1-24B-Base-2503-SFT` is not a base.
- **Hybrid / linear-attention archs** on a first run (Kimi-Linear, Falcon-H1, Nemotron-H, Qwen3.5's
  Gated DeltaNet) — GGUFs exist, but this is where llama.cpp quietly gets numerics wrong, and
  "model or runtime?" is not a question you want open while judging a register.
- **A 3B-active MoE as the only cell** (Trinity Mini, Qwen3.5-35B-A3B, Nemotron 30B-A3B) — arm 01
  found the 12b had no head to override the pull toward pretty-and-empty. Pair it with a dense 24–32B.
- **`--chat-template` / `/v1/chat/completions`** — a template on a base model is noise it will try
  to explain. And **a prose brief as preamble**: the predicted top failure of this arm.

## scene notes

- **Nobody runs a base model as a single-persona conversational seat** — and the archive shows why
  it never comes up: the completion people are writing fiction, the local people are shopping for
  finetunes, and the "make it talk like a person" thread reaches for a LoRA. Arm 04 stays unrun.
- `gemma-4-31B-pt` exists (`eyes-ml/gemma-4-31B-pt`) if the no-Google rule ever lifts — the
  heretic's weights minus the assistant stage, the only apples-to-apples read going. His call.
- Cost: arms 01–03's shape — a 48 GB card by the hour, 25 GB on a fat pipe, under a dollar. The
  OLMo conversion is the only new step and it costs disk and minutes, not money.
- Archive quirks worth adding to `~/.claude/docs/reddit.md`: `body=` needs a `subreddit=` (site-wide
  returns nothing), `min_score` is a 400, `urllib` gets 403 where `curl` gets 200, and a query
  returns only the most recent 100 — page back with `before=<oldest created_utc>`.
