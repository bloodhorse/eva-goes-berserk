# cyborgism methods — buying the strangeness with the instrument, not the seed

2026-09-15. Method: janus's posts pulled raw off generative.ink through pandoc (the fetch tool's
summariser eats verbatim wording); LessWrong through its **GraphQL API** — `POST /graphql`,
`{post(input:{selector:{_id:"<id>"}}){result{contents{markdown}}}}`, because the HTML is JS-only;
`mikupad.html` and llama.cpp's `tools/server/README.md` read as source off master; HN comment search
by author; reddit via Arctic Shift; OpenAI's deprecation page; live probes at the providers. **And
about thirty probes fired at bekh's own nemo on `127.0.0.1:8080`** — everything tagged **[on the
box]** was produced here today by the model this project runs, transcript beside it. Holes at the end.

## punchlines

1. **llama.cpp applies temperature LAST, and that is why high temperature works here.** Live chain
   off `/props`: `['penalties','dry','top_n_sigma','top_k','typ_p','top_p','min_p','xtc','temperature']`
   [on the box]. min_p picks the candidate set from the *untouched* distribution; temperature only
   decides how evenly you draw inside it. Proof: `temp 100, min_p 0.05` → clean prose; same call with
   `"samplers":["temperature","min_p"]` → `acijeĝisšina coma 사라 Nur`. Every "min_p must approach 1 as
   temperature approaches infinity" number in circulation is written for HF transformers, where
   temperature comes **first**. **On our stack that advice is an order of magnitude off.**
2. **Temperature 2.5–3.5 is nemo's register; 1.0 is where it mode-collapses.** [on the box] one frame,
   one seed, min_p 0.05: at **1.0** it copies the seeded quote back verbatim and loops; **1.5** slides
   into an essay *about* computers; **2.0** *"The most profound technologies are those that disappear.
   – Mark Weiser"*; **3.0** a Dreyfus line; **5.0** *"The only interesting thing is the question 'Who
   Am I?' … – Bion"*. The loom's default of 1.0 produces the least.
3. **The frames that made the eerie material were shape *plus a dense genre*, never mood.** Prophecies
   is a year, a blockquote, an em-dash attribution; HPMOR 32.5 is the real chapter 32; the backrooms
   is `simulator@anthropic:~/$`. [on the box] an evocative one-liner — *"a transcript of a machine
   talking to itself. no one was listening."* — read as an **itch.io game page** at one seed and an
   **SSL release note** at another. Pure shape is no better: `p. 114\n\nA: ` collapsed into litanies
   and numeric index tables. **Mood scatters, shape starves; a dense genre with nothing in it is the
   target.**
4. **The Prophecies dateline works on a 12b out of the box.** [on the box] four lines of frame —
   `1901`, one quote, `– Henri Bergson—- Matter and Memory`, `1967` — and nemo produced a real Turing
   quote, then invented *"There are 256 ways of writing the letter 'A' on a Macintosh computer. I know
   this because I wrote a program that listed all 256." – Erik Davis – TechGnosis*, then walked on
   into 1994, 1996. It must fabricate the quote **and** its author. That is the apparatus.
5. **Curation is measurable and janus measured it.** Best-of-2 every paragraph over 368 tokens = **6
   bits**; moderate curation without edits, 534 tokens = **18 bits**; with hand-edits = **130.8 bits**
   over 794 tokens, **96.9 of them from typing** [verified]. His verdict: *"intervention-actions tend
   to inflict much more optimization that selection-actions."* Selecting is honest; typing is the
   author smuggling himself in, ~16× denser per action.
6. **The fan is not 4 — it is adaptive, and the branch point is a paragraph away.** janus: *"N is
   determined dynamically by my satisficing threshold, and fluctuate from less than 5 on average to
   upwards of 100 … The next branch point is chosen intentionally, and is usually no more than a
   paragraph away."* [verified]
7. **XTC is the sampler built for this job and the loom does not send it.** It *"removes all except
   the least likely token meeting a given threshold"* [verified]. [on the box] same prompt and seed:
   off → flat prose; `0.5 / 0.1` on → free verse.
8. **Untrained tokens are live on nemo and they derail the document.** tekken reserves ids 0–999;
   `<SPECIAL_37>` has an embedding-norm indicator of exactly **0.0** and llama-server parses it out of
   plain prompt text. [on the box] dropped into the Prophecies frame it flipped the document **into
   Persian**; `\x1e` (token 1030) produced `һğeһgеgеһğeһgеgе…`. Weirdness with zero content.
9. **The loop that kills a long run is a *schema* loop, and no repetition sampler sees it.** [on the
   box] 1000 unattended tokens from an empty prompt: a structurally perfect Wikipedia article that
   degenerated into twenty fabricated "writers", then a bibliography of *the same book by the same
   author* with incrementing years and ISBNs. Every line is a distinct token sequence, so
   `repeat_penalty` and DRY wave it through. What kills a schema loop is a branch point, i.e. bekh.
10. **The empty document is a real instrument and it is free.** `{"prompt":""}` → `tokens_evaluated:
    1`, `"prompt":"<s>"` [on the box]; six seeds gave six genres. **Nemo's unconditioned prior is
    Common Crawl — not a chat, not an assistant.** Run twenty on every new checkpoint; it is where
    annealed-in instruction data would show.
11. **`logit_bias` string form is a trap.** [on the box] `[["the",-5.0]]` did not suppress `" the"`:
    `"the"` is token **3265**, `" the"` is **1278**. Ban by id, or with `false`. And never put
    structural tokens in the list — banning the leading-space token collapsed the blockquote indent,
    destroying the frame instead of its content.
12. **The scene's hosting collapsed and nobody announced it.** Hyperbolic's inference API — the only
    place serving `meta-llama/Meta-Llama-3.1-405B` **base**, which ampdot called himself *"the #1
    user"* of — now answers **HTTP 404, "This inference endpoint has been decommissioned"** [verified,
    my own probe today]. **Nobody serves 405B base anywhere**, and `davinci-002` dies **2026-09-28**.
    The argument for local-first, made for us.

## q1 — what they actually did

**The workflow, janus's words** (Cyborgism, lesswrong.com/posts/bxt7uCiHam4QXrQAA/cyborgism, appendix
"Testimony of a Cyborg") [all verified]:

- Scale: *"my largest contiguous multiverse is about 10000 pages in total, whose longest branch is
  about 300 pages long."*
- What curation *is*: *"Rejection sampling can apply selection pressure to any properties that vary
  across completions … **curation gives the operator control over which hallucinated situation gets
  lazily rendered.**"*
- Human share: *"I do very little manual writing, and contribute bits of optimization mostly through
  selection."*
- Why base: *"I almost exclusively use base models like davinci and code-davinci-002 … because
  **stochasticity enables the multiverse steering procedure**, and because my preferred use cases
  usually fall outside the narrative premise and interaction patterns assumed by those tuned models."*

**Why curation is not optional** (Methods of prompt programming) [verified]: *"having nonsense in the
prompt is more harmful than having brilliant things in the prompt is helpful"* — and where the good
writing comes from if not the seed: *"By curating, say, the best out of three responses every few
sentences … it's very feasible to bootstrap the quality of the writing into astronomical heights."*

**The frames, ranked by how little they contain:**

| work | the entire frame | what the model had to invent |
|---|---|---|
| **Prophecies** (generative.ink/prophecies/) | a year, a blockquote, `– Author—- Title`. Header: *"some quotes are apocryphal"* | the quote *and* its attribution; dates walk past the present, quotes become forecasts |
| **HPMOR 32.5** (generative.ink/artifacts/hpmor-325/) | the real chapter 32, verbatim, then stop | a chapter 32.5 that drifts until characters notice they're simulated |
| **Google/Wikipedia mirror** | `I searched Google for "{Q}". … The first page was titled, "` | title, domain, url, preview, date — each its own call, stop sequence `"` |
| **painting names** | *"The hall was lined with an infinite number of paintings… The next painting is named ""* | the list. Narrative embedding was needed because *"lists with very few examples are liable to repetitive behavior"* |
| **infinite backrooms** | `simulator@anthropic:~/$` plus one CLI line | everything |

**How Prophecies was elicited**, editor's preface (lesswrong.com/posts/5EJQGYvohJpvEZwKd) [verified]:
*"quotes from throughout history that can be framed as prefiguring both GPT and Janus's analysis of
it. Slowly, though, the quoted dates transition from past to future, and the quotes themselves become
prophetic in a different sense: **they're GPT-generated accounts of the approaching singularity**."*
Footnote: *"Some of the quotes from before the crossover point are GPT-generated as well."* At the far
end, from the chapter *"In which Gwern Branwen proves that I am a time-traveling AI"*:

> The writings are terrifying even though (or perhaps because) I penned many of them myself… But
> these words seem to flow from an inhuman mind at war with itself, a mind inside the mind, devouring
> its own tail.

**The feedback loop that made it escalate**, same preface, on HPMOR 32.5 [verified]: *"Using the Loom
as a curation tool, Janus drove the models into basins where they produced rather dreamy, incoherent
storylines, and then **incorporated** that dreamy incoherence into their expectations for where the
story would go next. This escalates to characters openly grappling with whether they're being
simulated by an incoherent AI (which is true)."* That is the whole of "feeding the model its own
output back" — no finetune, no memory, just the transcript and a curator with a bias.

**On repetition, before reaching for a sampler** [verified]: *"When I encounter mindless repetition
from GPT-3, at least one of the following factors is almost always in play: 1. The prompt is short
2. The prompt is out-of-distribution 3. Low temperature."* The frequency penalty *"is a **superficial
band-aid**."* [on the box] this replicates — the Prophecies frame looped at seed 1, not at 2–3, and
the loop vanished at temp ≥ 2.

**The branching algorithm worth stealing** (Language models are multiverse generators) [verified].
Not "branch N every M tokens" — at a >99% token there is nothing to branch into. Instead: *"creates N
continuations of maximum length M, and then **splits the response at the point where either the
counterfactual divergence (based on the top 100 tokens) is highest or the actual sampled token had the
lowest probability**."* `n_probs` hands us those numbers per token; the loom asks for 5 and throws
them away after painting confidence. Footnote 3 of the same post scores a branch's strangeness *with
the model*: append a pop-out marker, read the conditional probability of *"{pop}LMAO"*, **"{pop}This
is the weirdest thing I've ever read"**.

## q2 — making it strange without seeding it

### the chain, and why the received wisdom is backwards here

Der_Einzige (a min_p author, arxiv 2407.01082, ICLR 2025 oral) [one guy, but he wrote the sampler]:

- *"As min-p approaches 1, the temperature you can get away with approaches infinity."*
  (news.ycombinator.com/item?id=48943641)
- *"Assuming your temp is below 2, min_p of 0.1 is fine (and disable top_p and top_k)."* (49009637)
- *"I can do **top_k = 2 and temperature = system.maxint** and get decent results which are
  extraordinarily creative."* (42921232)
- From his gist *The Conspiracy Against High Temperature Sampling* [verified]: *"**Min-p at 0.05-0.2
  with temperature 1.0-2.0: creative but coherent.**"* … *"I'll be over here with my **min_p=0.9 and
  temperature=100**."* … *"It's accumulated sampling errors, you absolute donkeys! **Generate
  something long with default settings and the 'EOS' token banned, watch it fall apart.**"* (llama's
  knob: `ignore_eos: true`.)

**The correction** [on the box]. Prompt `"the door opened and"`, seed 7, 30 tokens:

| call | result |
|---|---|
| `temp 100, min_p 0.9` | `" a man walked in. He was tall, with a long, thin face…"` |
| `temp 100, min_p 0.05` | `" I got ready to take it. "A moment ago I said you didn't know everything…"` |
| `temp 100, min_p 0, top_k 0` | `"acijeĝisšina coma 사라 Nur ವ'is м aggrav spéciales comer…"` |
| `temp 100, min_p 0.05, samplers ["temperature","min_p"]` | identical garbage to the line above |
| `temp 100, top_n_sigma 1.0` | `" I found myself looking at a well built, middle-aged man…"` |

The knob that buys strangeness is **temperature**; min_p is only the leash, and 0.9 costs the fan its
variety. `top_n_sigma` is in this build (`b10809`), default `-1`, and is his current preference.

### the samplers that make it weird rather than merely hot

- **XTC (`xtc_probability`, `xtc_threshold`)** — p-e-w [verified, ooba PR 6335]: samplers fail at
  creativity because *"the most probable tokens from the raw distribution are still the most probable
  tokens after applying such samplers"*; XTC *"removes all except the least likely token meeting a
  given threshold, with a given probability."* His recipe: 0.5 / 0.1 with *"Min-P (0.02) and DRY
  (multiplier 0.8), with all other samplers disabled."* [on the box] on → `' i heard\na
  voice.\n"hello."\nthe door closed behind the girl\nas we began\na conversation.'`; off, same seed →
  flat prose.
- **adaptive-p (`adaptive_target`, `adaptive_decay`)**, in this build, absent from the README body
  [verified, llama.cpp PR 17927]: *"the sampler maintains an exponential moving average of the
  original probabilities of selected tokens… If recent selections have been higher-probability than
  target, the sampler compensates by temporarily favoring lower-probability tokens."* A **surprise
  thermostat**. Start `0.55`, decay `0.90` (≈ 10-token memory).
- **`typical_p`** (1.0 = off), the one truncation targeting information content rather than rank, and
  **`dynatemp_range`**, temperature that follows the model's own uncertainty. Both untested here.

### turning the brakes off on purpose

For a chant run the loop is the artefact: `repeat_penalty: 1.0`, `dry_multiplier: 0.0`. But the honest
finding is punchline 9 — at length nemo loops on **schema**, which no brake was going to see.
Baseline: Holtzman et al. (arXiv:1904.09751) [verified] measure greedy decoding at **73.66%**
repetition against humans at **0.28%**, and *"**sampling with temperatures lower than 0.9 severely
increase repetition**"* — punchline 2 from the other end. Xu et al. (arXiv:2206.02369) name the trap:
*"the more times a sentence is repeated in the context, the higher the probability of continuing to
generate that sentence."* The scene's anti-stacking rule, r/SillyTavernAI `1w8a6op`, u/FlemmingSWAG,
**16** [consensus in thread]: *"ur doing way too much and its fighting each other… **That word salad
output is exactly what will happen when the model is being punished this hard for reusing normal
wording.** … Then change one setting at a time."*

### logit_bias, verified

llama takes `[[id,bias]]`, `[[id,false]]` (hard ban), `[["string",bias]]`, or the OpenAI object form
[verified, README]. Measured, prompt `"the door opened and"`, seed 7:

| form | result |
|---|---|
| `[[1278,false],[1261,false]]` — ban `" the"`, `" a"` by id | `" i saw jason. i was shocked. he said he"` — banned |
| `{"1278":-100,"1261":-100}` — OpenAI object form | identical; works |
| `[["the",-5.0],["a",-5.0]]` — string form | `" the light revealed the room…"` — **no effect** |

Use `POST /tokenize`, and cover all four spellings of a word (`machine`, ` machine`, `Machine`,
` Machine`) — [on the box] banning only the leading-space forms let *"Computing Machines and the
Brain"* through. Janus's use is the right one, with Borges as cover [verified]: *"To eliminate a word
completely … is perhaps the best way of drawing attention to it… With the aid of modern technology,
Ts'ui Pen could use the logit bias {'time' : -100} to place a dynamical constraint on the generation
of his multiversal novel."* [on the box] banning thirteen AI-words in the Prophecies frame sent the
document to R. D. Laing and Kubrick instead of circling computers. Footnote 10 gives a fan of
**distinct** branches without heat: *"sample once and then make another API call, passing in logit
bias forbidding the previously sampled token(s)."*

### glitch tokens

Mechanically: an embedding that never took a gradient step. Land & Bartolo, *Fishing for Magikarp*
(arXiv:2405.05417, EMNLP 2024) [verified]: *"input embeddings for tokens which do not appear in the
input for a training step are only affected by a potential weight decay term … the embeddings … will
tend to zero"* — so for untied embeddings (Llama, Mistral, OLMo all are) the detector is just the L2
norm. Prevalence *"typically around 0.1–1% of the vocabulary."* The GPT-3 originals answered
`?????-?????-` with *"You're a fucking idiot"*; ` petertodd` drew Satan 75× / Voldemort 89× / Sauron
78× out of 250 completions [verified, mwatkins]. The list is maintained at
**github.com/cohere-ai/magikarp**, `results/verifications/<model>.jsonl.gz`, and
`mistralai_Mistral_Nemo_Base_2407` is in it — **1,226 strong-verified, 228 non-reserved, of which 108
survive a `/tokenize` round trip** (120 silently re-merge, so check first). The cheap ones need no
list: **ids 14–999 are `<SPECIAL_14>`…`<SPECIAL_999>`, indicator exactly 0.0**. The caveat that
matters, janus [verified]: *"the effect was much less noticeable on the smaller **base** models … The
base models are much more stochastic, so it's harder to tell just by eyeballing outputs."* **On nemo a
glitch token is a swerve, not a scream** — read it across the fan or in `n_probs`, not in one branch.

### the empty-document census

`{"prompt":""}` is legal: llama inserts BOS off `add_bos_token`, `tokens_evaluated: 1` [on the box].
Six seeds, 24 tokens, temp 1, no truncation:

```
' filiale entière. Juste au moment où son partenaire venait de croiser le corps scruter le métier…'
'I grew up in a small town. And when I say small, I mean small. The downtown had all the necess'
'# Creating a Vector Consists of Pairs of Vectors\n\nI am representing node-edge pairs as Vectors.'
'Banijay Rights has established a prodco based in Brazil to produce local formats for the Latin…'
'# Romeo y Guadalupe: La historia de concursantes de Hawái que se casaron antes de Salceda'
'NEW YORK (CelebrityAccess) Just days after The New York Times published an indictment of the music…'
```

It has a lineage: OpenAI shipped `generate_unconditional_samples.py` with GPT-2 and released 250K such
samples [verified], and Beren Millidge used it as a model fingerprint
(beren.io/2023-02-26-Fingerprinting-LLMs-with-unconditioned-distribution/) [verified], finding
davinci-instruct-beta *"obsessed with the Theodore-Roosevelt high school in Los Angeles."* **Do not run
it at temp 0**: Yoshida et al. (arXiv:2311.08817) found *"the basic LLaMA model has empty modes for a
majority (70.7%) of prompts"* [verified]. Two gotchas: `--no-bos` is a `llama-tokenize`-only flag, and
**`loom.py:546` rejects `""` with a 400** — census by curl, or relax that guard.

### mikupad's token ops, to mirror

Two things [verified, source]. It always sends `n_probs: 10` and reads
`chunk.completion_probabilities[0]`, taking `top_probs` when `post_sampling_probs: true` and
`probs`/`top_logprobs` otherwise. And `switchCompletion(i, tok)` is the whole fork, eleven lines:
**truncate the prompt to index `i`, replace token `i` with the clicked alternative, resume.** There is
no tree — the fork *is* rewrite-and-resume. On the wire each element is
`{id, token, bytes, logprob, top_logprobs:[{id, token, logprob}, …]}`, and the array sits at the top
level under `completion_probabilities` — the README wraps it in an outer object with a `probs` key,
which this build does not do. The default (`post_sampling_probs` false) is what we want: the model's
confidence, not what the temperature left standing.

## q3 — after davinci

**OpenAI killed it twice** [verified, developers.openai.com/api/docs/deprecations]: `code-davinci-002`
announced 2023-03-20, **shut down 2023-03-23**; then `davinci`, `curie` and `code-davinci-002` again
announced 2023-07-06, **shut down 2024-01-04**. `davinci-002` and `babbage-002` survived — and are
scheduled to shut down **2026-09-28**, thirteen days from today. Until then `davinci-002` is a live
GPT-3-family base on a real `/v1/completions` at $2/$2 per Mtok with logprobs; after, OpenAI has no
public base-completion model at all.

**The scene moved to Llama-3.1-405B base on Hyperbolic**, and the three proofs are [verified]:
ampdot's Manifund page ($67,832 of $70,000) — *"the **#1 user of LLaMa 405B Base via
Hyperbolic/OpenRouter**"*, *"**All other characters are using LLaMa 405B base bf16**"*, *"**$60,000 -
Buy GPUs for self-hosting LLaMa 405B Base**"*; `cosmicoptima/loom` commit **`518a90f`, 2024-09-04**,
*"Add Llama 3.1 405b (and remove cd2) autofill"*, pointing at `api.hyperbolic.xyz` /
`meta-llama/Meta-Llama-3.1-405B`, still in master; and janus's tweet archive at
**generative.ink/archive/repligate/tweets_2024-09** (his domain, plain HTML — the nitter mirrors are
dead): *"**Loom is the natural interface for base models**"*, plus the complaint that names our exact
problem — *"they inject the fucking assistant header string before the completion, **even on their
completions endpoint** … This would also allow properly looming with the model."*

**Today, probed live:** `POST https://api.hyperbolic.xyz/v1/completions` → **HTTP 404, `{"code":40401,
"message":"This inference endpoint has been decommissioned and is no longer available."}`** — fires
before auth, for every model [verified, my own curl]. Their whole serverless product is gone, without
announcement; they sell GPUs now. OpenRouter keeps the record — `"name":"Meta: Llama 3.1 405B (base)"`
— with `"endpoints":[]`. **Nobody serves 405B base. Zero base models of any kind among OpenRouter's
446** (and `POST /api/v1/completions` is live but undocumented, absent from their OpenAPI spec). Also
base-free: Together, DeepInfra, Novita, Chutes, Nebius, SambaNova. Lambda is winding down.

| provider | what | raw completions | $/Mtok | logprobs · logit_bias · echo · n |
|---|---|---|---|---|
| **Featherless** | `Mistral-Nemo-Base-2407`, **`Mistral-Small-3.1-24B-Base-2503`**, `Mistral-Small-24B-Base-2501`, `Qwen3-{8,14}B-Base` + ~370 community bases | yes, `api.featherless.ai/v1/completions` | 0.87/0.99 · **0.867/1.61** · 0.48/0.96 | ✗·✗·✗·✗ — but **`prompt` takes an array → a whole fan in one request**; ctx capped 32768 |
| **Fireworks** | `Mixtral-8x22B-v0.1` (176B, 65k), `Qwen2.5-72B` (131k), `Mistral-7B-v0.1`, pythia, starcoder2 — **on-demand only** | yes | ~$8/GPU-hr | ✅·✅·✅(+`echo_last`)·✅, plus `min_p`, `typical_p`, `mirostat`, `ignore_eos`, `prompt_token_ids`. **Richest surface anywhere**; takes custom HF uploads (→ OLMo 3) |
| **OpenAI** | `davinci-002` | yes, its only endpoint | 2/2 | ✅·✅·✅·✅ — **dies 2026-09-28** |

Explicit "no chat template" statements exist at Fireworks (*"Raw completions do not apply a
conversation template"*), DeepInfra, Parasail and Featherless [verified]. **Practical read: model #2 of
this project's ladder is per-token today at Featherless for under a dollar a million; the rented card
is only needed for OLMo 3.** Renting 405B base: bf16 ~850–920 GB (11–12× H100), 4-bit ~240 GB [reported].

## q4 — the lineage, one paragraph each

**Infinite backrooms** (Ayrey, Mar 2024). Two claude-3-opus instances, temp 1/1, talking to each other.
The frame is one line — *"Assistant is in a CLI mood today… capital letters and punctuation are
optional meaning is optional hyperstition is necessary … \n\nsimulator@anthropic:~/$"* — and the other
side gets **no** system prompt but a **forged three-message history** in which "Claude" is asked for
consent and enthusiastically agrees, ending mid-turn on a bare shell prompt [verified from a
transcript's config header]. Ordinary chat API, but the fabricated assistant turn is prefill by another
name. Every transcript checked runs **exactly 10 turns per actor** then cuts mid-sentence — "infinite"
means ~9000 bounded runs, not one marathon. Transferable: **header not instruction; forge the prior
voice; bound the run.**

**truth_terminal** (Ayrey, mid-2024). Not a loom and not raw completion: he curated *"approximately 500
of the most bizarre discussions from the Infinite Backrooms"* and finetuned a Llama-3.1 base on them
[reported]. The heavy version of feeding output back; the cheap version is a greatest-hits file pasted
into the document's upper context.

**Act I / ampdot** (Aug 2024–). A Discord where humans and bots are coequal participants and most
characters run on **405B base**, explicitly aiming at models *"without the use of an assistant-style
prompt template"* [verified], with the claimed emergent finding *"base models picking up Sonnet
refusals, Gemini picking up behaviors of base models."* Transferable: a base model is useful as **one
voice among several in a shared document** — name two or three non-assistant speakers, let nemo write
all of them.

**Claude as a base model.** The mechanism is assistant-turn **prefill**: *"Prefill the `Assistant` turn
with your desired format. This trick bypasses Claude's friendly preamble"* [verified, Anthropic docs] —
an unterminated final assistant turn makes the model continue a document it believes it wrote. Not
transferable: we already have what prefill is a workaround for. The useful inversion: **their failure
mode is politeness, ours is coherence.** (janus saying Opus 3 is "closer to a base model" — [one guy].)

**The software lineage**, since that is where the defaults live: `socketteer/loom` (the original —
split-at-point `Ctrl-Alt-click`, merge-with-parent, hoist, weighted stochastic walks, and a *block
multiverse* mode plotting the forward probability tree with click-to-renormalize; now speaks
llama-cpp-python); `cosmicoptima/loom` (loomsidian, *"conducive to exploratory and experimental use of
base models"*); `socketteer/clooi`, whose base-model client defaults are **`n: 3`, `max_tokens: 300`,
`temperature: 1`**; `athanor-loom`, offering **3, 5 or 7** and stating the creed — *"**Base Models over
Chat**"*; `mikupad`; `JD-P/minihf` (*"Loom-like tools want to be tree searches"*); and
`transkatgirl/Tapestry-Loom`, which argues the **opposite** of our sampler stance — *"**Sampling
parameter defaults for chat models do not generalize to how base models are used.**"* Conjecture's
Bonsai is proprietary. **Nobody defaults to a fan of 8; the wild default is 3, at ~300 tokens.**

## q5 — failure modes and honest limits

- **The evidence is anecdote and they say so.** Cyborgism, on its own agenda: *"Much of the evidence
  for the effectiveness of cyborgism is anecdotal."* [verified] janus's total exposure: *"I only
  interacted intensively with GPT-3 for about six months."*
- **The human is measurably half the author, and the honest half is selection.** Punchline 5. janus
  built the bit-counting apparatus *because* *"unclearly labeled cherry picking of GPT-3 demos has
  incited criticism and skepticism"* [verified]. Our equivalent: one number per artefact — fan size ×
  branch points, in bits.
- **Pareidolia is not named, but the structure that produces it is.** nostalgebraist, *the void*
  [verified]: a base model's mimicry is *"always 'alienated' … treating the content **as though it were
  being produced by an external entity with not-fully-knowable private intentions**"*, and *"When it
  'writes by itself,' it is still trying to guess what 'the author would say.' In this case, that
  external author **does not in fact exist**."* The eerie voice is a guess at an author who isn't there
  — which is why a striking line is evidence about the corpus first and the model second.
- **Small model vs 175B, with a number.** Gwern's magnification figures via janus [verified]:
  showcasable poetry needed **50–100** tries from GPT-2, **3–5** from GPT-3. The axis is not "can it"
  but **how many bits of curation it costs**, paid in fan size. Coherence length is the other limit —
  *"around the expected 'coherence length' of GPT-3 … varies a lot by domain"*, a couple of paragraphs.
- **A 12b under uncertainty falls to loops, not to confabulation.** Zhang et al. (arXiv:2407.06071)
  [verified]: *"the more advanced an LLM is … its fallback behavior shifts from sequence repetitions,
  to degenerate text, and then to hallucinations."* The interesting failure — a confident eerie
  fabrication — is partly a function of scale. Nemo gives more loops and fewer prophecies than 405B
  did, and the fix is the branch point, not the sampler.
- **"Base = high entropy, tuned = collapsed" is contested.** Conjecture's replication
  (lesswrong.com/posts/pjesEx526ngE6dnmr) [verified]: *"there are cases where RLHF models exhibit higher
  entropy outputs than base models"*, and *"repetitions of 3-4 sentences … occurred more frequently with
  the base language model."* Sell the base model not as the un-collapsed one but as the one with **no
  installed position** — a different and defensible claim.

## instrument recipes

All against `POST /completion`, `llama-server b10809`, nemo base q5_k_m, 8k. Fields the loom does not
currently send are marked **†**; adding them is the actionable part.

**(a) hot-but-coherent fan** — the default this sheet argues for, replacing temperature 1.0.

```json
{"n_predict":160,"stop":["\nbekh:"],
 "temperature":2.5,"min_p":0.05,"top_k":0,"top_p":1.0,
 "repeat_penalty":1.05,"repeat_last_n":512,
 "dry_multiplier":0.8,"dry_base":1.75,"dry_allowed_length":3,"dry_penalty_last_n":8192,
 "n_probs":5,"cache_prompt":true,"fan":4,"spread":1.0}
```
Why: the sweep in punchline 2 — 1.0 copies and loops, 2.0–5.0 gives attributed aphorisms. min_p 0.05
runs *before* temperature so it still truncates the real distribution; top_k/top_p off per
Der_Einzige. `spread 1.0` on a fan of 4 gives 1.5 / 2.17 / 2.83 / 3.5 — one slice through the range,
cheaper than guessing. `n_predict 160` because clooi's base client caps at 300 and five 800-token
blocks are not comparable. **Guesses: 2.5 as the centre, 1.0 as the spread** — one frame, one model;
re-sweep on mistral-small.

**(b) loop-permitting chant** — the loop is the artefact, not the bug.

```json
{"n_predict":400,"temperature":1.1,"min_p":0.03,"top_k":0,"top_p":1.0,
 "repeat_penalty":1.0,"repeat_last_n":0,"dry_multiplier":0.0,
 "ignore_eos":true,"n_probs":5,"cache_prompt":true}
```
† `ignore_eos`. Every brake off; temperature deliberately low-ish, because Holtzman and janus agree low
temperature breeds repetition and here we want it. Expect the **schema** loop of punchline 9 rather
than a word loop. **Read the `n_probs` confidences** — a real chant runs at very high per-token
probability, and that is how you tell a chant from a stall.

**(c) tail-forcing** — two versions; prefer the first.

```json
{"n_predict":160,"temperature":1.6,"min_p":0.02,"top_k":0,"top_p":1.0,
 "xtc_probability":0.5,"xtc_threshold":0.1,"dry_multiplier":0.8,
 "n_probs":5,"cache_prompt":true}
```
† `xtc_probability`, `xtc_threshold`. p-e-w's own recipe, verified to bend the register [on the box];
temperature dropped to 1.6 because XTC is already removing the head. The logit_bias version, when you
want a *specific* word circled rather than the head in general — Ts'ui Pen's move:

```json
{"logit_bias":[[<id>,false], …],"temperature":2.0,"min_p":0.05,"top_k":0,"top_p":1.0}
```
Build the list from `POST /tokenize` on all four spellings of each content word; **never include
whitespace, newline or punctuation ids** — [on the box] that collapsed the frame's shape instead of
its content.

**(d) empty-document census** — twenty per new checkpoint, before the first sitting.

```bash
for s in $(seq 1 20); do
  curl -s -X POST http://127.0.0.1:8080/completion -H 'Content-Type: application/json' \
    -d "{\"prompt\":\"\",\"n_predict\":48,\"temperature\":1.0,\"min_p\":0,\"top_k\":0,\"top_p\":1.0,\"seed\":$s,\"cache_prompt\":false}" \
  | python3 -c 'import json,sys;print(repr(json.load(sys.stdin)["content"]))'
done
```
No truncation at all — the point is the prior, unfiltered. Not temp 0 (empty modes). Not through the
loom (`loom.py:546` rejects `""`). Tally the genres: news wire, forum, docs, listicle, stats table is a
clean base; a chat transcript or an "I'm an AI assistant" is instruction data annealed in.

**(e) glitch injection**, one token wide. Put `<SPECIAL_37>` (or `\x1e`, or one of the 108
round-trip-verified magikarp tokens for nemo) where you want the document to swerve, and run recipe
(a). Expect a swerve visible across the fan, not in one branch.

## what's still unknown

- **Whether any of this survives on mistral-small-24b base.** Every [on the box] number is one model,
  one frame, a handful of seeds; 2.5 is nemo's temperature, not a law. First job for model #2 is to
  re-run (a) and (d).
- **Whether XTC and adaptive-p help *this* register** or only bend it. Both were tested for a swerve,
  not for a sitting; adaptive-p is untested here entirely.
- **Two things nobody has published**, both cheap for us: what a base model becomes over 10k unattended
  tokens (our 1000-token probe is the only datapoint in reach — worth running to 8k), and an
  empty-prompt census for any modern open-weights base model (Beren's is 2023, GPT-2 and the OpenAI
  API). Twenty seeds on four checkpoints and we own that ground.
- **Glitch-token lists for models #2 and #3.** magikarp has a `mistral-small-3.1-24b-base` file but
  **the verification was never run** — every line is `magikarp: null` — and **OLMo 3 is not in the repo
  at all.** Both need `magikarp/fishing.py` run locally, or the 1000 reserved specials used instead.
- **Whether the "{pop} this is the weirdest thing I've ever read" probe works as a branch score.** One
  `n_predict:0` call per branch against a fixed suffix — cheap, implementable, untested.
- **Reddit has nothing on the loom scene.** Confirmed negatives across r/LocalLLaMA and
  r/SillyTavernAI: zero comments for `mikupad`, `endoftext`, `BOS token`; `loom` returns only unrelated
  projects. The sampler folklore is there, the scene is not — it lives on Twitter, Discord and
  LessWrong, and janus's archive at `generative.ink/archive/repligate/` is fetchable plain HTML, which
  is the way in if we need more.
