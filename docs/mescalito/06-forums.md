# 06 — the forum sweep (reddit via Arctic Shift)

Slice: the hobbyist side of the mescalito brief. Sources: r/LocalLLaMA (nearly all the signal),
r/SillyTavernAI, r/MachineLearning (dry), r/KoboldAI / r/Oobabooga (nothing usable came back).
Swept 2026-09-24.

**How it was read, and what that costs.** The archive was under load all session. Full-text search
of *comment bodies* in r/LocalLLaMA timed out even in 3-week windows, and `query=` post search did
the same. What worked: post **title** search (`title=`), fetching **whole threads** by `link_id`
(~60 threads read in full), and **author-scoped** comment search (`author=X&body=Y`, fast) for the
scene regulars (qrios, Sabin_Stargem, kindacognizant/kalomaze, -p-e-w-, phree_radical, cynerva).
So a good comment buried in a thread whose title says nothing is invisible to this sweep unless
one of those authors wrote it. Treat "nobody did X" below as "nobody did X in a thread titled for it
or by a regular."

Permalinks are `https://reddit.com/r/<sub>/comments/<link_id>/`. Scores are at archive time.
Quotes are verbatim, typos included.

---

## 1. Weight noise

### The one real dose curve on reddit — GPT-2 124M, gaussian on every parameter

r/LocalLLaMA · **Model "neurodegeneration" at different noise levels** · 2024-03-05 · score 25 ·
u/MrVodnik · https://reddit.com/r/LocalLLaMA/comments/1b7e4mf/

Method, in his words: *"iteratively introduce more and more noise into their params. I did reset the
model after each try, so the noise values are absolute, but not additive."* Parameter std of the
model: *"Standard Deviation: 0.13496524095535278"*. Prompt "My favorite food is ". Absolute std →
first output (so the ratio to param std is ~std/0.135):

> === Introducing noise: 0.0001 ===
> My favorite food is iced tea, but I'm still not convinced the Chinese are really that good. I'm not sure if I'm getting the Chinese version of this, but I'm sure I'm getting the Chinese version of this. I'm not sure if I'm

> === Introducing noise: 0.001 ===
> My favorite food is iced tea. I find it tastes like ice cream. I can't find any other flavors. I can't find anything that tastes like ice cream.
> I love ice cream. I love ice cream. I love ice cream. I love ice

> === Introducing noise: 0.01 ===
> My favorite food is iced tea and iced tea hot tea and iced tea hot tea hot tea hot tea hot tea hot tea […]

> === Introducing noise: 0.03 ===
> My favorite food is iced chicken," Mr. Gonzalez told Mr. Gonzalez's own bookshop bookshop on Sunday afternoon unloads Mr. Gonzalez's unopened canned chicken each Sunday each Sunday each Sunday […]

> === Introducing noise: 0.05 ===
> My favorite food is  Twitch poison poison poison poison poison […]

> === Introducing noise: 0.08 ===
> My favorite food is arilyarily that that that that that that that that that that that whole whole whole whole whole whole whole provider deal") favorite concerned concerned concerned […]

His read: *"the model is actually quite resilient! With average (mean) weight being close to zero
and standard deviation at ~0.135, it started to visibly loose it senses at 0.01."*

What this curve actually says, and it matters for the brief: **the first thing noise buys is not a
slur, it is a loop.** 0.0001 (~0.07% of param std) already drifts the content ("the Chinese") and
starts circling; 0.001 (~0.7%) is a clean sentence-level loop; 0.01 (~7%) is phrase echolalia;
0.03 has a strange-but-grammatical clause ("Mr. Gonzalez's unopened canned chicken") *then* loops;
real salad only from ~0.04 up. Caveats: one sample per dose, greedy-ish, a 124M model — tiny models
loop anyway.

Comments worth keeping:

- u/Some_Endian_FP17 (5, 2024-03-06): *"This is nuts but you might have stumbled on a digital analogue of neurodegeneration in the real brain. Noise at subsequent layers overwhelms the initial signals and because the brain's neurons can integrate voltage over time, the overload causes repetitive and incorrect outputs."*
- u/watkykjynaaier (13, 2024-03-05): *"I'd be curious to see how this scales with higher weight models. It's like how the 70b+ models are more coherent at lower BPW than the smaller ones, right?"* — nobody ran it.

### The parent thread — Mistral 7B at std 1e-4 barely moves

r/LocalLLaMA · **How robust are model outputs to slight changes in model weight?** · 2024-03-05 ·
https://reddit.com/r/LocalLLaMA/comments/1b6wd34/

- u/phree_radical (9): ran `p.add_(torch.rand_like(p).normal_(mean=0, std=0.0001))` over every parameter of Mistral 7B and printed the top-50 next-token distribution for *"Merry Christmas to all, and to all a good"* before/after: `'night'` goes from ~0.069 to 0.0515, `'flight'` and `'fight'` climb to ~0.013 and ~0.010. *"I also tried Mixtral, I expected it to be less resilient because it seems so much more chaotic with huge updates to the embeddings between layers, but it didn't hurt"*. (Note what rose: *flight, fight* — near-neighbours of *night* in spelling, not in meaning.)
- u/dqUu3QlS (3): *"It is very common to use model quantization with LLMs, storing each weight using only 3-4 bits. This is roughly equivalent to rounding every model weight to one significant figure. LLMs are robust enough to random weight changes that this amount of rounding error leaves the model's outputs almost unchanged."*

### Accidental: a steering vector too strong, landed "on the boundary"

r/LocalLLaMA · **I was trying out an activation-steering method for Qwen3-Next, but I accidentally
corrupted the model weights. Somehow, the model still had enough "conscience" to realize something
was wrong and freak out.** · 2026-01-08 · score 34 · u/ikergarcia1996 ·
https://reddit.com/r/LocalLLaMA/comments/1q79n6x/ (the output itself is a screenshot)

- u/ikergarcia1996 (9): *"If the strength of this vector is too high, you can corrupt the block outputs resulting in a fully corrupted output […] When this happens, the model outputs random tokens. But in this experiment, I accidentally set a strength that was in the boundary between fully corrupting the model and still being able to produce some coherent text. The model is corrupted, and completely useless, but the answers are funny and very weird, because it looks like the model realizes that is producing non-sense and tries to correct himself."*
- u/Red_Redditor_Reddit (8): *"I had that happen, but the weights were too corrupt to make complete sentences. Still, I could feel as if it was conciously trying to pull itself out of insanity."*
- u/Chromix_ (11): *"Modern reasoning models are trained to stop and get back on track after descending into loops or garbage token streams. This is what you may be observing here"* — i.e. the "self-aware" flavour is a post-training artefact; a base model would not do it.

### The geometry argument, from the scene

r/LocalLLaMA · **I found the "Lobotomy Layers" in Llama 3.1 and Qwen 2.5** · 2026-02-25 ·
https://reddit.com/r/LocalLLaMA/comments/1res533/

- u/claythearc (28): *"a = 4 is HUGE. You're pushing the model way off the manifold of activations it was trained on, so the inputs are significantly out of sample. The conclusion you draw […] could, instead, be the natural output of layers N+ when exposed to garbage input."*
- The OP (u/NoSir261) ran a shuffled/random-direction control; u/claythearc (4): *"Really interesting that the geometry holds at low alpha, and random directions don't reproduce it."* — the only place on reddit where a **random direction** in the residual stream is even mentioned, and only as a control.

---

## 2. DRµGS — noise inside the forward pass, fresh per token (EGjoni / u/qrios)

The closest thing on reddit to the brief's "living charge". Two announcement posts, both by u/qrios
(the GitHub account is EGjoni):

- **Stop messing with sampling parameters and just use DRµGS!** · r/LocalLLaMA · 2023-12-29 · score 280 · 110 comments · https://reddit.com/r/LocalLLaMA/comments/18toidc/
- **I am reaching out to the community for help with my DRµG problem.** · r/LocalLLaMA · 2024-01-09 · score 76 · 32 comments · https://reddit.com/r/LocalLLaMA/comments/192esef/ (a first copy, 191whxu, was held by mods and reposted)

### What it is, in the author's words

- *"DRµGS (Deep Random micro-Glitch Sampling) basically just injects randomness into the model while it's still thinking, instead of after the model has thought and when its too late to give it any say in the matter. This way, you can still get variety in the outputs, even though you're always picking the most likely prediction."* (post)
- *"it's applied to the key value vectors at each attention head deeper in the model. This distinction is crucial not only for functionality but also to avoid calling the library IRµGS."* (kffo9et, 6)
- To "isn't this just weight noise?": *"Doesn't touch the weights. Just vectors they generate."* (kfgchne, 2)
- Why it should stay sane: *"the spatial perturbations are happening in a space that already tends to group elements by functional similarity. Add on top of that the down projection at each attention head always tending squeeze a lot of values into smaller spaces and it becomes very difficult to stray anything too far beyond the range of sensible outputs."* (kfgnyof, 6)

### The dose, and the cliff

- Post: *"There's a pretty big range of both safe and effective doses, followed by a very sudden fall-off to echolalic degeneracy."*
- qrios (kfgnyof): *"Anecdotally, I have yet to manage to get it to starts spewing nonsense the same way setting temperature too high might. It mostly seems to either vary the outputs nicely, or else immediately break and start repeating the same word over and over."*
- qrios (kffasjm, 5), on using it against repetition: *"so far seems to be a very tight threshold between "does nothing" "works" and "breaks everything immediately." […] the very sudden manner in which it breaks makes me suspicious there might either be something interesting going on here or more likely a bug in my code."*
- qrios (kh6me1v, 2024-01-10): *"0.3 is probably on the high end. I'd keep it below 0.2 unless you cold shower a lot, but this depends on the drug type and probably quantization level and dose shape. […] in theory it seems to me that adding noise to the Q vectors should have a different sort of effect than adding it to the A vectors. And that adding the noise in the middle layers should have a different sort of effect than adding it in the early or late layers."*
- Named settings from u/Kat- (kfhwk0i, 2023-12-30), on Llama-2-7b-chat as "Alan Watts": *"Default Settings — theta: 0.1, injection depth: 0.4, spread: 0.301"* and *"Last Layers — theta: 0.101, injection depth: 0.807, spread: 0.11"*.

### What it read like

On an instruct Llama-2-7b-chat, so the register is chatbot; the effect is on *content choices*:

- qrios's balloon test (kffxk8x): baseline greedy has the balloon *"fall to the ground"*; at **"moderate dose type A = 0.1"** V1 the story gains *"Jimmy couldn't shake the feeling that the balloon was trying to communicate with him"* and ends with the balloon *"floating gently back down to him"*; V2 has the balloon call out *""Jimmy! Jimmy! Come and get me!""*. At **"heroic dose = 0.8"** the physics goes: *"the balloon will pop and lose its buoyancy"*, and V2: *"The air inside the balloon will escape through the cut in the string"*, then a balloon named *"Blinky"*. His verdict: *"As you can clearly see from these results, the model is stupid, and continues to be so even on DRµGS!"*
- u/SillyFlyGuy (3), on the same samples: *"That model is simply gorgeous in its descent to madness."*
- Kat-'s Alan Watts samples at theta 0.1: all three responses stay fluent, on-topic and in character; they differ in which advice arrives ("focusing too much on the breath", "neglecting other aspects of your life"). No weirdness at that dose — variety, not strangeness.
- u/keturn (4) quoting a portal sample: *">He had been practicing cutting the balloon strings for a while now, trying to perfect his technique. / So dedicated, our Jimmy, doing his best to learn a trade."*
- qrios's own claim for daily use (192esef): *"I think the method feels very good to daily-drive, and accomplishes its purpose eerily well. Obviously it's not going to make your dumb model any smarter"*. The 800-generation comparison portal: https://egjoni.github.io/DRUGS/sample_generations/ (*"all generations are using the same exact dose shape"*).
- On hallucination (kff3w34, 37): *"From my experiments, no. They don't exacerbate hallucinations. And to a minor extent they sort of mitigate them, but only insofar as they avoid putting an erroneous word on the page which the model ends up having to commit to."*

### Did anyone run it outside the author's transformers patch?

Essentially no.

- qrios (kff7hmh): *"this hooks deep into the attention and kv-caching mechanisms"* — needs per-backend work. Llama.cpp request: https://github.com/ggerganov/llama.cpp/issues/4704 (linked by qrios and u/keturn; users were told to "keep an eye on" it).
- An exllamav2 route existed briefly: u/SoylentMithril's **Brain-Hacking Chip** (per-layer CFG) could host it — *"BHC can in theory support DRµGS, but currently it does not."* (kh2etaj). qrios later: *"I'm the maker of DRµGs. I also contributed quite a bit to the Brainhacking Chips codebase while integrating DRµGs into it."* (l6hdl6g, 2024-05-31, in **What happened to Brain-Hacking Chip?** https://reddit.com/r/LocalLLaMA/comments/1d4o2o7/). The original BHC repo was gone by then; the surviving fork is github.com/EGjoni/BrainHackingChip. u/cuyler72 (5): *"I'm hoping we get a native DRµGs implementation in Llama.cpp or exllama."*
- u/AI-Pon3 (7, 2024-01-09) tried it only through the web portal: *"While I mainly use llama.cpp and don't really have access to this methodology […] I'm definitely hooked on DRµGS."*
- u/Sabin_Stargem, eight months later (2024-08-31, https://reddit.com/r/LocalLLaMA/comments/1f5s6ng/): *"It injects noise into AI layers at the start. Apparently, the AI is able to overcome this noise, but the output is slightly distorted. […] Far as I know, no one has actually implemented this method. This means no one knows whether it is an effective sampler."*
- u/Maxxim69 (2024-09-01, https://reddit.com/r/LocalLLaMA/comments/1f6dzlb/): *"8 months ago we had DRµGS, a quirky and fun concept that quite unfortunately did not catch on"*.
- Nothing about DRµGS turned up in r/SillyTavernAI, r/Oobabooga or r/KoboldAI titles.

Related and lower-level: kalomaze (u/kindacognizant) confirmed the difference — *"your implementation of the Noisy sampling strategy was to inject it within the hidden layers and not on the output logits. It's a very interesting idea in comparison to mine."* (kfimssl). u/a_beautiful_rhind (kff8r43): *"hehe.. mirostat is already like feeding the model drugs."*

---

## 3. Merges and layers (frankenmerge, passthrough, self-merge, loops)

### What layer surgery does to the surface: spelling goes first

- u/AlpinDale, maker of Goliath-120B (9, 2023-11-10, **Goliath-120B - quants and future plans** https://reddit.com/r/LocalLLaMA/comments/17rsmox/): *"After playing around with it for a few days, I've noticed two glaring issues: - it tends to make slight spelling mistakes - it hallucinates words. They happen rarely, but frequent enough to throw off benchmarks."*
- u/noeda (2, **Venus-120b** https://reddit.com/r/LocalLLaMA/comments/1840wg5/): *"I have noticed too, that Goliath makes spelling errors somewhat frequently, more often than other models. It doesn't seem to affect the "smarts" part as much though. It otherwise still makes high quality text."*
- u/audioen (1, 17rsmox): *"It sometimes writes nonsense, like bad words, but I guess that's to be expected given that we have kind of copypasted and bunched couple of closely related models together […] However, I liked the writing quality a lot."*
- u/Super_Sierra (8, 2026-03-24, **RYS II - Repeated layers with Qwen3.5 27B** https://reddit.com/r/LocalLLaMA/comments/1s1t5ot/): *"Goliath was really, really weird […] And till this day, it is still one of the best under 400b models for 'show, not tell' for some fucking reason??"*
- u/llama_in_sunglasses (5, 17p5m2t): *"I made some frankenmistrals and it's definitely a strange experience trying to work out how intelligent or not these models are. Especially when they get sassy."*

### Where in the stack you tamper decides the failure

- u/edk208 (5, 2024-02-14, **What happens if you finetune after a frankenmerge vs before a frankenmerge?** https://reddit.com/r/LocalLLaMA/comments/1aquak1/): *"of the frankenmerge models that I've tested, most suffer from incoherence. I've done some passthroughs in the front layers vs middle layers vs back. Major repetition problems/output problems with the back heavy frankenmerge, and major "babbling" behavior with the front heavy. Middle seems to be the most stable."*
- u/chulpichochos (8, 2023-12-02, **Swapping Trained GPT Layers with No Accuracy Loss** https://reddit.com/r/LocalLLaMA/comments/188m82u/): *"If you swap too many times, peformance breaks down. If you swap too early a layer, it breaks down (I think 0-2 can't be swapped). If you, instead of swapping, do multiple passes through the intermediate layers (I modified your code to do this by editing the forward in PhiModel and looped through the intermediate layers N times, skipping first 5 and last 5 layers) […] If you loop more than 4 times the model breaks down. Even looping 2x, if we generate enough tokens we'll observe different behavior (even at low temps)."*
- u/tdrussell1 (61, same thread), the mechanism: *"because all these models use residual connections everywhere. Each layer (in fact each sublayer) does not compute y = f(x), it computes y = x + f(x). Each layer can be thought of as adding a small "delta" to the vector representation for that token."*
- u/noeda (8): *"the very surprising part of all these weird merge or shuffling exercises was that somehow it didn't change the output very much. […] the kind of funny "llama in trenchcoat" model https://huggingface.co/chargoddard/llama-2-26b-trenchcoat-stack (it doesn't make it better, many benchmarks become worse, but the output also doesn't become complete nonsense)."*
- u/qrios (9), on why swaps break small models: *"mistral is too small to recover from errors it makes in its outputs and […] messing with two layers in a small model means you've messed up way more of the model than messing with two layers in a large model."*

### Self-merges: more deterministic, not more strange

- u/az226 (1, **Miqu 120B self-merge** https://reddit.com/r/LocalLLaMA/comments/1aj2jw0/): *"I wonder if repeating layers has some effect akin to setting a lower temperature but in a much more complicated/robust way. Like it reinforces correct answers."*
- u/MikeRoz (3, same): *"my latest message in this one chat just always ends up with infinite stammering. It's also weirdly deterministic - with temp at 1 or more, I've had several cases where swiping has resulted in the same message, verbatim."*
- u/SomeOddCodeGuy (3): Miqu-1-120b *"has dethroned Goliath-120b as the most coherent model I've ever worked with"*; the two-model Miquliz *"felt a bit closer to what I've come to see from some of the Yi-34b fine-tunes: some impressive moments, but also some head-scratchers that made me wonder what in the world it was talking about lol."*
- u/Bubbly_Guidance_4565 (31, **Can someone explain a self-merge to me?** https://reddit.com/r/LocalLLaMA/comments/1cm8oej/), on Llama-3-120B: *"It exhibits some fun qualities but ultimately it's worse than the original 70b at most tasks. […] It only really got famous because a weirdo on twitter claimed it's better than gpt4 because when asked about a grand unified theory it hallucinated HARD about asymptotic gravity theory."*
- **Attention temperature in repeated layers already exists as a merge trick:** u/ex-arman68, **froggeric/miqu-1-120b-attenuated-GGUF - experimental self-merge with downscaling of Q and K matrices for repeated layers** (12, 2024-04-19, https://reddit.com/r/LocalLLaMA/comments/1c7zvys/): *"There is some interesting research going on at the moment on attenuating the effect of the Q and K matrices in merged layers, to smooth out the distribution."* Method: mergekit issue #198 and the wolfram/miqu-1-120b discussion #4 (credited to jukofyork). He later withdrew it: *"I have realised I made a mistake with this model, and will be withdrawing it."* Scaling Q and K down is scaling attention logits — the brief's "attention temperature", done as a file edit.

### DARE / random merges

Nothing on feel. Title search turned up only LoRAX's "linear, TIES, DARE" and a "SLERP, TIES, DARE ... ?" question thread. On reddit DARE is a merge method, never a way to make a model strange.

---

## 4. Low quant as a knob

- u/FenderMoon (92, 2026-08-20, **Ladies and gentlemen I present to you Qwen3.8 27b 1bit brain damage quant** https://reddit.com/r/LocalLLaMA/comments/1vtr3h0/, score 1656): *"at 1 bit these things lose coherence really fast and they understand grammar enough to get you think, for like a half a dozen words "oh it counts as English" until it gets sloppy and starts spitting out grammar soup."*
- u/danielhanchen (Unsloth, 50, same): *"Divergence-300 @ 32 tests all quants on actual long running tasks and shows 1-bit at 8% accuracy over 32 tokens. UD-Q2_K_XL has a 21% accuracy and 4-bit UD-Q4_K_XL 68%. This means the divergence between BF16 over 32 tokens is 92% for 1-bit"* — a published measure of *how fast* a low quant leaves the full-precision path.
- u/TR_Alencar (1, 2024-02-13, **New GGUF Quantization in 1.6-1.7bpw SOTA, aka. IQ1_S** https://reddit.com/r/LocalLLaMA/comments/1apgzw5/), what broken IQ1 looks like: *"Majamba correction MajambaumarEF Cord cord Domain Sug correction Ali luc Cord correctionumarEF MajPKEFuo Ali Cord Ali Linearuo sugar correction"*
- u/colin_colout (8, 2026-02-22, **Has anyone else tried IQ2 quantization? I'm genuinely shocked by the quality** https://reddit.com/r/LocalLLaMA/comments/1rbio4h/): *"no matter the model size, you'll see more confusion between similar looking words or similar concepts (and basic typos the more you quantize."*
- u/DominusIniquitatis (1, same): *"still running Mistral Small IQ2_M—fairly smooth sailing and still feels way smarter than Q4_X of smaller models, even if occasionally makes a typo here and there."*
- u/raika11182 (0, 2024-04-27, **Llama 3 70B Q4_K_S is noticeably lobotomized** https://reddit.com/r/LocalLLaMA/comments/1ce6x68/): *"Llama 70B Q4KS routinely makes typos and confuses character names."*
- u/Dry-Judgment4242 (2, 2024-05-02, **The Best Fiction/Novel Writing I've seen from an LLM to date - Midnight-Miqu-70B-v1.0i1-IQ2_S.gguf** https://reddit.com/r/LocalLLaMA/comments/1ci60lf/), on Command R+ at low quant: *"I find CR+ to be weird. Like it's recovering from a stroke or something and will often just break down logically."* (That thread's own OP rates a 70B at **IQ2_S** as the best fiction he'd seen.)
- u/Lemgon-Ultimate (4, 2024-10-30, https://reddit.com/r/LocalLLaMA/comments/1gfrtwl/): *"a 70b model with 2bpw can give better answers than a 34b 4bpw model but in my experience it also tends to give more nonsense answers because of it's low quant."* u/synw_ (7, same): *"I had some good results for some writing task with IQ2_XS vs smaller models"*.
- u/Fit_Flower_8982 (6, **IQ1_Smol_Boi** https://reddit.com/r/LocalLLaMA/comments/1l19yud/): *"the answers were incoherent and mixed up to 3 languages in the same sentence. A gibberish generator so horrible it was comical."*
- u/Cradawx (15, 1vtr3h0): *"IQ1_M seems bit too much brain damage lol. Here are some facts from Q8 TinyLlama, gets more fun when you turn the temperature up. Rabbits: 1. Rabbits have a unique ability to change color."* — the small-model confabulation register people enjoy is *capacity*, not quant.
- u/andrewlapp (6, **Noisy Sampling** thread, https://reddit.com/r/LocalLLaMA/comments/185635o/), recipe for *inducing* loops: *"Use a lossy quantization such as Q2_K (2 bit), Q4_0 (4 bit), or GPTQ (4 bit)"*.
- A 2026 attempt to *undo* quant damage (u/eapache, **Experiments in recovering from low-bit quant damage** https://reddit.com/r/LocalLLaMA/comments/1vlhbc4/): *"there are four sensitive tensors in the Q2 quant (gate+up in the first two blocks) which can be cheaply upgraded to Q4"* — i.e. per-tensor sensitivity is measurable and concentrated early.

The consensus picture: low quant hurts the **lexical surface** (typos, look-alike words, name
confusion, language mixing) and **logic**, not the associative weather. Nobody on reddit calls a
low quant "dreamy"; they call it "drunk", "lobotomized", "brain damage", "stroke".

---

## 5. Control vectors / steering

- llama.cpp support landed 2024-03 (**control vectors added to llama.cpp** · 158 · https://reddit.com/r/LocalLLaMA/comments/1bgej75/). The vgel/repeng post (**Control vectors: add a meaningful bias in each layer** https://reddit.com/r/LocalLLaMA/comments/1atqj7f/) drew only usage questions.
- u/sanobawitch (1, 1bgej75) is the only person asking for *random switching*: *"I wish this parameter would be part of the prompt api, so with Mixture of Con Vectors: if randint(1, 6) == 1: … set_control='apologetic' else: … set_control='happy' — The behavior of the character would be more unpredictable. In the vgel/repeng code, it's possible to do this with transformers."* — a random **choice among trained vectors**, not a random direction.
- u/qrios (6, 2024-05-31, 1d4o2o7), a design note that fits the brief's "no leash": *"I think it would be better to take the projection of the output on the vector, scale that up or down or negatively, then add the difference of the projection and the rescaled projection back into the original vector. This way you do not force the model to, for example, discuss the golden gate bridge when there is no sensible way to do so, but do increase its tendency to do so when it is a plausible thing to do."*
- u/FailSpai (maker of the "Mopey Mule" abliteration, **"What happens if you abliterate positivity on LLaMa?"** https://reddit.com/r/LocalLLaMA/comments/1d47qor/), on a concept-erasure method: *"most of the time the model would just devolve into gibberish."*
- Overdose looks like section 1: ikergarcia1996's Qwen3-Next vector *"on the boundary"*.

No thread in r/LocalLLaMA, r/SillyTavernAI or r/MachineLearning titles uses a **random** control
vector as a creative tool.

---

## 6. Samplers

### XTC (Exclude Top Choices, u/-p-e-w-)

- Announcement (200, 2024-08-18, https://reddit.com/r/LocalLLaMA/comments/1ev8n2s/): *"XTC can dramatically improve a model's creativity with almost no impact on coherence. During testing, I have seen some models in a whole new light, with turns of phrase and ideas that I had never encountered in LLM output before. […] XTC feels very, very different from turning up the temperature."*
- -p-e-w- (25): *"If a token is "necessary" in a specific position (e.g. continuing a character name), then that token will be the only one with a probability above the threshold, and it won't be eliminated."*
- -p-e-w- (3), the "rare lightning" setting: *"pairing a low xtc_threshold with a very low xtc_probability. This leads to a behavior where most output positions are left untouched, but occasionally, XTC will force a highly unlikely continuation to be chosen."*
- -p-e-w- (9, 2024-10-16, **How to use the Exclude Top Choices (XTC) sampler, from the horse's mouth** r/SillyTavernAI https://reddit.com/r/SillyTavernAI/comments/1g4r12r/): *"As the threshold approaches 0.5, XTC's effect vanishes, and as the probability approaches 0, XTC's effect also vanishes. Therefore, you have two axes of control […] from "barely noticeable" to "unhinged"."* Baseline there: *"Min P to 0.02 […] XTC Threshold to 0.1 and XTC Probability to 0.5 […] DRY Multiplier to 0.8 […] make sure that Min P comes before XTC."*
- u/CharacterAd9287 (3, same thread): *"Where others descend into gibberish if you push them too far, this descends into a delicious chaotic madness while staying coherent"*
- u/Philix (2): *"0.05-0.15 is the range I keep it in. Outside of that, any higher and the effect the sampler has vanishes, and the lower you go, the more unhinged the model gets, especially if you've upped the probability."* The guide itself warns: *"With low threshold values and certain finetunes, XTC can sometimes produce artifacts such as misspelled names"*.
- u/a_beautiful_rhind (2, 1ev8n2s): *"It also produced some incoherence in a few messages, where the choice it made simply made no sense in light of the context. […] Suddenly it gets too creative with what the character should look like."*
- u/hardeh (1, r/SillyTavernAI **Now that the dust has settled how are you finding the XTC and DRY samplers?** https://reddit.com/r/SillyTavernAI/comments/1fjwlmr/): *"XTC increases creative writing, but makes some models noticeably dumber in logic, confusing facts from previous context and straight out making things out of nowhere. At least with nemo-based 12b models."*
- u/VongolaJuudaimeHime (2, r/SillyTavernAI https://reddit.com/r/SillyTavernAI/comments/1f5zxck/): *"I'm currently using a Mistral Nemo finetune, and it's notorious for always picking stiffly, repeating the same sentence patterns that already worked before over and over again, and with XTC on, it doesn't do that anymore."*
- The dissent, u/Mart-McUH (2, 2024-10-04, **Say goodbye to GPTisms and slop! XTC sampler for llama.cpp** https://reddit.com/r/LocalLLaMA/comments/1fv5kos/): *"Most probable tokens are most probable for a reason after hard training, cutting them off is disastrous. […] some super important tokens like EOT get often cut […] Overall with XTC I feel like randomness increased, not creativity."*

### Temperature, min_p, "temperature infinity"

- u/cynerva (5, 1ev8n2s): *"This is what I've been doing. MinP=0.125, temperature=infinity, for models in the 8B to 12B size range. I've been happy with the results - outputs are more creative and engaging, less repetitive, and still coherent."* And (1): *"infinite temperature can work well if the MinP value is tuned well for the model. Set it too high and the outputs are uncreative […] Too low and the outputs do go off the rails."*
- -p-e-w- (2), why the floor matters: *"A Min-P value of 0.02 typically retains 5-10 tokens […] this value prevents garbage from the long tail being sampled. […] I've run unconstrained many times, and it was always immediately obvious. At a typical response length of 300-500 tokens, the long tail is bound to be sampled a few times, which is often enough to throw things off balance."*
- -p-e-w- (24), on flattening after truncation: *"Your suggestion cuts off the tail, then makes all remaining tokens equally likely to be sampled. This will quickly lead to the model going off the rails, unless you are cutting off pretty much all tokens except one or two, in which case you get the opposite of creativity."*
- u/cynerva (11, 1ip8imy) on sampler order: *"If temperature is applied last (which is usually the case in llama.cpp) then MinP remains stable at higher temperatures."*
- u/HeavyConfection9236 (12, 2025-05-14, **Base Models That Can Still Complete Text in an Entertaining Way** https://reddit.com/r/LocalLLaMA/comments/1kmmq6d/), Qwen3 0.6B, *"temperature: 20 […] top K: 1000 […] top P: 0.9-0.92"*: *"Sure! Here's a **handy ** Soisahn Cășe Oread Recipe **готовая** […] - Maybe warm stones, cooked bread […] everything helps form lightweight mold, fun cactuses in dough..."* That is what heat without a floor does: salad with a few lovely fragments ("warm stones").
- Sabin_Stargem's old mirostat-at-heat runs (u/Sabin_Stargem, 2023-07): *"With L2-70b Airoboros, I like temperature 3.5."* (https://reddit.com/r/LocalLLaMA/comments/15cplvh/) with *"Mirostat 2 […] Tau: 8 Eta: 0.1"*.

### Dynamic temperature / entropy / noisy logits (kalomaze = u/kindacognizant)

- **I need people to test my experiment - Dynamic Temperature** (75, 2023-11-21, https://reddit.com/r/LocalLLaMA/comments/180b673/): *"higher temperatures disproportionately impact high confidence token generations. […] we turn temperature into a range, where only the highly randomizable tokens get mapped a high temperature, and a non-randomizable token stays near-deterministic."* Merged to llama.cpp early 2024 (https://reddit.com/r/LocalLLaMA/comments/198uf24/).
- kalomaze (5): *"I've had someone mention that for 70b models that it felt 'distinctly less mechanical', whatever that means."* u/a_beautiful_rhind (1): *"It's kind of like mirostat but actually good."*
- Sabin_Stargem (3, same), T 1.84/2.0 with and without min_p: *"the style changes with MinP 0 for the respective temperatures. T-1.84 MinP 0: There was dialogue. […] T-2.00 MinP 0: A stronger emphasis on the aftermath of the scenario. The other generations were more "in the moment". Personally, it is my favorite."* (Heat changed what the page was *about*, not only which words.)
- **Noisy Sampling** (73, 2023-11-27, https://reddit.com/r/LocalLLaMA/comments/185635o/): gaussian noise on the logits. kalomaze (8): *"Applying Gaussian noise randomization to the logits with a gaussian deviation factor of 1.0 is totally coherent at top k = 1"*; (4): *"in cases where a ~98% or ~99% confidence token is chosen, it's barely impacted at all, but it heavily changes the skew of the spread out distributions […] I like to think of it like a radio signal. If you have a very strong signal in the first place, it won't be obstructed, but if the signal is weak, it'll be fuzzier in terms of determinism."*
- u/out_of_touch (5), the rep-penalty failure: *"sometimes my characters will start out talking normally and slowly progress into talking like college professors giving poetry lectures."* (the "thesaurus" drift)

### Top-n-sigma

- r/SillyTavernAI guide (46, 2025-02-28, https://reddit.com/r/SillyTavernAI/comments/1j06o7w/): *"Even temperature 5 is coherent with top nsigma as your main sampler!"*; *"`1` is a sane default value for top nsigma, similar to `min P 0.1` […] I would say to not set top nsigma anything above `2` though"*.
- u/Nonsensese (3, same): *"Cranking up temp to 5 with top-nsigma set to 0 results in garbage word salad, as expected, but when I set top-nsigma to 1, the generations are actually coherent."*
- Contra, u/AppearanceHeavy6724 (5, 2025-02-14, https://reddit.com/r/LocalLLaMA/comments/1ip8imy/): *"I tested it. It was weird. Not good, either dumbs down or makes model incoherent. Dynamic T works way better IMO."* and *"Nsigma felt like mirostat 2; very strange."*

### Scheduled heat — proposed, not built

u/kryptkpr's **"The Muse"** (71, 2023-08-01, https://reddit.com/r/LocalLLaMA/comments/15ffzw5/) is a *"top-k constrained temperature ramp"* that pushes down top logits. The thread's ideas are the brief's item 7, word for word:
- u/teachersecret (12): *"How about raising and lowering the temp like a sine wave while generating, giving it more creative thoughts, then periods with more deterministic results to keep things on track before going toward creative again?"*
- u/PacmanIncarnate (3): *"We don't want creativity everywhere; we need creative direction, then coherent follow through."* and *"bump up temp based on periods so the beginning of sentences would be more creative then wrapped down and maybe bump up even higher after \n so new paragraphs start more creative."*
- u/_Lee_B_ (6): *"a "randomness budget" sort of approach: if the LLM hasn't produced anything creative for a while, it can deviate more. If it's already deviated, then it needs to stay on track for a build and rebuild it's budget"*.

None of these became a llama.cpp sampler that the archive shows. Newer entropy-driven samplers
that did: **Adaptive-P** (118, 2026-01-04, https://reddit.com/r/LocalLLaMA/comments/1q42wtt/; u/a_beautiful_rhind: *"seems a bit subtle compared to XTC […] if you set .05 then you start seeing it lose a bit coherence."*) and a **Particle Scattering Sampler** fork (2026-07, https://reddit.com/r/LocalLLaMA/comments/1umqgnl/) that moves mass only between neighbouring ranks — *"Scatter uses a Gaussian kernel over rank distance (radius 2.5 by default), so mass only moves between neighboring ranks"*. And a novelty: a robot whose MQ-2 smoke sensor drives temperature 1.0→1.6 live (1497, https://reddit.com/r/LocalLLaMA/comments/1u9a17y/) — *"His word choice flattens and wanders to lower-probability, more associative tokens"*.

### Entropix

Two tiny threads (1g4blp8, 1geny9l), no reports of how its text reads.

---

## 7. RoPE and KV cache

### RoPE off its trained values — the one report of "different weather"

u/Sabin_Stargem is the only witness, but he said it five times over two years:

- 2024-08-18 (2, 1ev8n2s): *"A really, really long time ago before GGUFs walked the earth, I was trying out all sorts of ROPE settings. Aside from seriously affecting the stability of a model, it sometimes changed the personality. I had Llama-1 become very grimdark with my standard alien invasion test scenario, actually making a character cannibalistic and the setting truly apocalyptic. For a different roleplay, an unspecified isekai, the AI produced an afterlife spa hotel. Unexpected, but interesting and read very nicely. After GGUF, I never saw such levels of creativity (and instability) again. If you are trying to add more randomness, a very slight alteration in ROPE per generation might be a technique."*
- 2023-12-22 (1, https://reddit.com/r/LocalLLaMA/comments/18nvdcr/): *"In the past, I had the impression that a model's "personality" changes according to rope. Some models became very grimdark, others merely derpy. […] Being an anecdotal thing, it would be nice to know whether I am reading too much into it."*
- 2023-12-22 (2, same thread), his notes and a dose: *"It is better to use NTK, the lowest you can go without losing coherency. The effectiveness is on a curve, so being too big or small could corrode the output."* and a run labelled *"IDEAL - KoboldCPP Airoboros GGML v1.4.1 - L1-33b 16k-PI q6 - 16384 in koboldcpp, Smart Context, ROPE [1.0 + 268435456] - Creative"* — freq base 2^28, *"Note that it only worked once, trying to generate more failed with the output. Also, this ROPE was a moonshot that somehow worked a miracle."* (The sample is coherent pulp horror, a six-armed biped monster, a freezer room.)
- 2025-07-27 (1, https://reddit.com/r/LocalLLaMA/comments/1maeuuo/): *"In the very old days of Airoboros, it could change the 'personality' of the AI. I actually got some of my best roleplaying from that. However, it was REALLY unstable. My speculation is that ROPE determines 'where' the AI first begins to form connections within its mental landscape."*
- 2023-08-08 (7, https://reddit.com/r/LocalLLaMA/comments/15lihmq/): *"KoboldCPP's 200,000 scaling was utterly borking it, causing junk. […] Rope 0.5 and 70000 is where you want that model."*

Confounds, honestly: these were Llama-1/2 models at *extended* context (RoPE scaling was needed),
with mirostat and hand presets in play; nobody else reproduced it; he himself asks whether he is
"reading too much into it".

What RoPE damage looks like at the surface:
- u/Cool-Hornet4434 (1, 2024-04-26, r/SillyTavernAI **Rope scaling** https://reddit.com/r/SillyTavernAI/comments/1cdhs3w/): *"Typically on Oobabooga I'd set the compress_pos_emb setting from 1 to 2 and double the context. This worked ok for me for most cases but sometimes it would cause two tokens to get mashed together oddly. Like two tokens that really didn't belong together would be mashed together as one word occasionally. OR numbers would get mashed or stretched so 1996 might show as 196 or 19996."*
- u/_Erilaz (1, r/SillyTavernAI https://reddit.com/r/SillyTavernAI/comments/1elcm33/): *"Gemma-2 27B is a very good model […] native context stops at 8K, and RoPE dumbs it down a lot."* and *"It either starts to forget random facts and things, or gives err[ors]"*.

### KV cache

Only accuracy talk. 2026 threads benchmark KV quant by KLD (e.g. https://reddit.com/r/LocalLLaMA/comments/1tp9d1w/, https://reddit.com/r/LocalLLaMA/comments/1vhaabz/). The one "feel" line is a broken fork (u/FantasticRewards, https://reddit.com/r/LocalLLaMA/comments/1flw4of/): *"The output is garbled nonsense though no matter what settings or model I use."* Nobody reports the prose feel of a q4 cache, and nobody **noises** the cache on purpose — except DRµGS, which is exactly that (noise on K/V vectors).

---

## 8. Base models for the surreal

- u/Soft-Ad4690 (82, 2025-05-14, https://reddit.com/r/LocalLLaMA/comments/1kmmq6d/): *"Back during the LLaMa-1 to Mistral-7B era, it used to be a lot of fun to just download a base model, give it a ridiculous prompt, and let it autocomplete. The results were often less dry and more entertaining than asking the corresponding instruct models to do it. But today's models, even the base ones, seem to be heavily trained on synthetic, dry, reasoning-heavy data"*.
- u/sjd96 (11, same): *"The best base model that I had fun playing with is Llama 3.1's 405B release. […] the BF16 instance hosted by Hyperbolic feels much more alive and fun."*
- **Are true base models dead?** (81, 2026-03-03, https://reddit.com/r/LocalLLaMA/comments/1rjyngn/): OP runs `llama-completion -no-cnv` on Qwen3.5-9B-Base with *"I think that apples are better when"* and gets a true/false question and a `<think>` block. u/aeqri (19): *"The last good base we've had was Mistral Nemo 12B I think."* u/FriskyFennecFox (9): *"Check `allenai/Olmo-3-1125-32B`, I tried that one personally, and it's a genuine Internet snapshot."* — the only reddit voice on the brief's own model, and it agrees with the brief.
- kalomaze (33, 2024-05-09, https://reddit.com/r/LocalLLaMA/comments/1cnlmz2/): *"There are things that the base model has learned to predict that you can't really 'distill' out of the Instruct model / must be observed in "candid" completion contexts."* And (6): *"I don't think "hallucinates" is the right term to use here when we're not discussing an Instruction model. Base models are supposed to visualize and guess what comes next."*
- **Oneirogen, a language model for dream generation** (74, 2024-06-28, https://reddit.com/r/LocalLLaMA/comments/1dqfl5r/) — Qwen2 finetuned on DreamBank (a finetune, so off the brief's table). Author u/antcroca159 (16): *"Dreams have phenomenological properties such as physical law violation, teleportation, less sensorial content, etc. that can't be grasped with the hallucination phenomena"*. A usable vocabulary for the human reader's marks, not a mechanism.
- **LLaMA-65B is so surreal and full of existentialistic insights.** (2023-04-04, 12bfrvu) — removed, no comments in the archive.

---

## 9. Misc

- **Random weights**: **Can I try a model with random weights in llama.cpp or kobold.cpp?** (2026-05-05, https://reddit.com/r/LocalLLaMA/comments/1t4ge9g/) is about benchmarking speed, not text; u/ComplexType568 points to tiny-random GGUFs (e.g. aladar/llama-2-tiny-random-GGUF).
- **Random LoRA / noise LoRA / untrained LoRA**: no thread.
- **"lobotomy/lobotomize"**: on reddit the word means censorship, abliteration or quantization loss. Nobody uses it for damage done on purpose for art.
- **r/MachineLearning**: title search for weight noise, noise injection, perturb, layer shuffle, layer dropout, random direction turned up nothing about generation feel. The only near hit: **"Impulse Steering" vs Activation Steering: Steering a model without lobotomizing it** (2025-12-07, 1pgsr0s, score 1).

---

## What the forums agree on, and where they contradict each other

**Agree:**

1. **Perturbing the inside fails into repetition first, salad later.** GPT-2 weight noise loops from 0.001–0.01 std long before salad at 0.04+ (1b7e4mf). DRµGS on the K/V vectors *"either vary the outputs nicely, or else immediately break and start repeating the same word over and over"*, with *"a very sudden fall-off to echolalic degeneracy"*. Back-heavy frankenmerges get *"Major repetition problems"*, self-merges get *"infinite stammering"* and are *"weirdly deterministic"*. Lossy quants are a recipe *to induce* repetition. Word salad is the **sampler's** failure (temperature without a floor; temp 5 at nsigma 0). So the brief's "slur, then word salad" is the heat picture. Internal noise, on reddit's evidence, goes **variety → loop → salad**, and the cliff to the loop is sudden.
2. **Uniform weight damage (quant, layer duplication) hits the lexical surface, not the associations**: typos, "hallucinates words", look-alike words (*night → flight, fight* under weight noise), mashed tokens and stretched numbers under RoPE scaling, language mixing at 1-bit. "Smarts" and the frame survive longer than spelling. The brief wants the opposite: surface kept, weather changed.
3. **Where you tamper matters**: early layers are fragile (can't swap 0–2; front-heavy merge "babbling"), late layers make loops, middle is the tolerant zone (swap, loop ≤4×, duplicate). The same zone is where quant-sensitive tensors *aren't* (the Q2 recovery work found them in blocks 0–1).
4. **Bigger models absorb more** of any damage (quant, layer swaps, noise), which is part of why OLMo 32B "reads sober".
5. **Samplers that act only at forks** (XTC with a threshold, dynatemp, nsigma, min_p as the floor) are the scene's working answer to "creative but coherent". The shared recipe is Min-P ~0.02–0.1 as the floor, temperature last, and XTC ~0.1/0.5.

**Contradict:**

- **XTC**: *"delicious chaotic madness while staying coherent"* / *"a whole new light"* vs *"randomness increased, not creativity"*, cut EOTs, *"confusing facts from previous context"*. The split tracks model size and task (12B RP likes it; 70B instruction users don't).
- **Top-n-sigma**: *"Even temperature 5 is coherent"* vs *"either dumbs down or makes model incoherent."*
- **Layer swapping**: *"any two intermediate layers […] can be swapped with no change in behaviour"* vs *"Of course you can't simply swap random layers"* — resolved in-thread by residual connections plus "not the first few, not too many".
- **Frankenmerges and creativity**: Goliath *"one of the best […] for 'show, not tell'"* and *"creativity is extremely high"* vs *"worse than the original 70b at most tasks"* and *"lacks originality and creativity"* (u/Ok_Library5522 on Goliath stories).
- **DRµGS and hallucination**: author says it slightly *mitigates* them; commenters doubt noise can tell fact from fiction. Nobody measured.

---

## What nobody on reddit has done

- **Noised a GGUF on purpose.** No post applies noise to a quantized file, to Q4 block scales, or per tensor family (attn vs MLP vs embeddings vs head), and none reports a dose relative to tensor norm. The only weight-noise experiments are fp32/bf16 in transformers: GPT-2 124M absolute std sweep, and Mistral 7B at std 1e-4 (top-k printout only). Nothing on a model above 7B, nothing on prose.
- **Per-token or per-page fresh weight noise.** Only DRµGS does fresh-per-token noise, and it touches K/V activations, not weights. No port to llama.cpp or vLLM ever landed (issue #4704); the exllamav2 route through Brain-Hacking Chip died with that repo. As of 2024-08 a regular says *"no one has actually implemented this method."* Nobody has published DRµGS on a base model, on anything but Llama-2/Mistral 7B, or at doses in a table beyond 0.1 / 0.8.
- **Random control vectors, or a new random direction every n tokens.** Mentioned only as a null control in a steering study. The one "random" idea is a dice roll between trained vectors.
- **Tampered with RoPE for effect since GGUF made it automatic.** Sabin_Stargem's personality shifts (2023, Llama-1/2, extended context) were never replicated. Nobody has tried *slight per-generation RoPE jitter*, which he suggested in 2024.
- **Attention temperature as a runtime knob.** It exists only as a merge-time trick (scaling Q/K in repeated layers of a self-merge), reported on benchmarks, then withdrawn by its maker for an unspecified mistake.
- **Noised the KV cache on purpose, or reported the prose feel of a quantized cache.**
- **Scheduled heat** (sine-wave temperature, hot after `\n`, a "randomness budget"). Proposed in 2023 in The Muse thread, never shipped as a llama.cpp sampler the archive knows of.
- **Combined any model-side perturbation with a true base model for fiction.** Base-model threads are about which bases are still clean. Perturbation threads use instruct/chat models, so every reported "feel" is filtered through a chatbot register.
- **Random/untrained LoRA as noise, DARE as a strangeness tool, layer shuffle for style.** No threads.
