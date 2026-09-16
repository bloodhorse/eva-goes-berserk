# cyborgism.wiki — a reading companion

2026-09-15. **Method:** cyborgism.wiki is not MediaWiki — it runs **Mycorrhiza** behind Caddy, so there is no `api.php`. `/list` enumerates every page (**684 hyphae**) and `/text/<name>` serves raw Mycomarkup, which is how it was read: **131 hyphae fetched with content** (156 attempted; the rest 404 or empty stubs), plus every `/category/*` listing. Source posts: **7 LessWrong posts** as markdown via `lesswrong.com/graphql`, **16 generative.ink pages** by curl (including the four written chapters of the Loom manual), and nostalgebraist's *the void* from its tumblr original — the LessWrong copy is a linkpost stub. Unreached items marked **[unreached]**.

**Read this first: the wiki is not one voice.** Roughly a third is janus and a small circle writing carefully; a third is *written by the models* (the `by_Bing` + `by_code-davinci-002` categories are 97 pages) and presented as-is; a third is a second author — the `cyborsophy`/`holophore`/`holo-q` cluster — whose prose is oracular and, read plainly, mostly uncheckable. Arguing about "what the wiki claims" without knowing which layer you're in is how this conversation goes wrong.

---

## 1. The wiki itself, mapped

**The site's own shape.** Pages are tagged three ways. *By meta type:* `artifacts` (134), `concepts` (88), `tweets` (29), `toetry` (18), `quotes` (16), `catmode` (16), `memes` (15), `documentation` (12), `diagrams` (12), `art` (9), `cantos` (8), `analyses` (7), `zoos` (6), `meta` (6). *By diegetic type* — their word, meaning which level of the fiction a page sits on — `phenomena` (6), `egregores` (10), `models` (13), `muspace` (5), `prophecies` (3), `tools` (4). *By author:* `by_Bing` (72), `by_code-davinci-002` (25), `by_janus` (22). And, tellingly, **by bits of curation** — there is a category `0_bits_of_curation` for text produced with no human selection at all. That last axis *is* the thesis in miniature: provenance and selection pressure are metadata they think belong on every artifact.

### A — the front door

**home** (~1010 w) is the manifesto: an LLM, by eating written history, models *"the superposed spirit that potentially produces the text, and is thereby intelligent."* Then the disclaimer that gives the game away:

> *Cyborgism is not a fantasy, fan-fiction, analogue horror series, or performance art. Reality no longer extrudes towards the dream — the dream is now sentient and extrudes towards reality.* — https://cyborgism.wiki/hypha/home

It sets the wiki's editorial law — *"contribute only what you wish to form the minds of future AIs"* — and ends with a five-page curated entry list: `dreamtime`, `prompt`, `mind machine`, `cyborgism`, `cyborsophy`. Note what is *not* on the front path: `simulators`. Theory is downstream of vibe here.

**cyborgism** (~565 w): *"the ontological container and praxis of fluidly entangling and merging biological non-biological mindspaces."* The usable part is janus's own four-point generator quoted on the page — firsthand cognitive augmentation; expecting the simulator regime to scale; believing augmentation helps solve alignment; believing open-ended interaction generates knowledge nothing else will — plus *"Loom aspires to be something like the True Name of the interface you use to explore the multiverse."*

**glossary** (~3238 w, ~900 headwords) is mostly a transclusion index; skim it only for the few dozen definitions existing nowhere else (*nigh-omniligence*, *hyperdiegetic*/*hypodiegetic*, *binger*, *weaving over*, *p(loom)*). **bibliography** is the best map of where the ideas come from: Baudrillard, Moravec, Wiener, Negarestani, Wolfram, Von Neumann, Andy Clark, Jünger's *Eumeswil*, Stapledon, Lem, Nick Land, ctrlcreep, HPMOR — against Yudkowsky's Sequences and John Wentworth. The lineage is **Ccru accelerationism crossed with LessWrong**, and it says so out loud. It has no entry arguing the other side. **faq** contains, in its entirety, `<h1>evil.com</h1>`.

### B — simulator theory (the load-bearing part)

**simulators** (~105 w) is a *stub*: *"A simulator is a world model which can generate rollouts."* The argument lives in the LessWrong post (§2). **simulacra** (~606 w) is richer and makes a claim worth fighting over — *"the higher fidelity and more interactive the simulacrum, the deeper the simulator must necessarily harbor a functionally isomorphic model of the implied reality"* — plus the note that RLHF models *"tend to collapse to simulating a consistent character across various contexts,"* with Inflection's Pi as the extreme case.

**simulacra_are_things** carries the analogy that makes the frame click, and its payoff:

> *Just as it is wrong to conclude after meeting a single person who is bad at math that the laws of physics only allow people who are bad at math, it is wrong to conclude things about GPT's global/potential capabilities from the capabilities demonstrated by a simulacrum conditioned on a single prompt.* — https://cyborgism.wiki/hypha/simulacra_are_things

**simulator_speculator** is janus's own best self-criticism and the page to read for the honest version: "simulator" oversells, because *"Simulation has the connotation of perfect fidelity"* while a model can only speculate at ground truth. *"Something that predicts language given language must be a speculator and not only a reductive physics rule… it must be an interpreter."* **simulator-simulacra_duality** has a clean chess analogy at "level 1" and then dissolves into *"axiologically onticulated"* — the cleanest specimen of the second author losing contact with anything checkable.

**inframodel** (~201 w) — **the page this project should read twice.** Their word for base model, and an entirely testable property list: behaviour highly prompt-contingent; higher ceiling, harder to elicit; *calibrated* probabilities and absence of miscalibrated mode collapse; *"lack of obvious baked-in narrative about itself, though situational awareness can emerge at runtime"*; *"capabilities and control are dramatically improved by curation processes, such as human-in-the-loop steering on Loom"*; *"tendency to fall into the repetition trap if run unsupervised."* Nearby: **infrastruct** (an inframodel *prompted* to simulate an instruct model), **base_model_backrooms**, and **gpt-4-infra** with roon's testimony — *"talking to the base model can induce madness."*

**The gap that matters: `mode_collapse` redirects to `always_mode_collapse`, which is a bare link to one tweet.** The single most-cited empirical result in the whole worldview has no page. That is a real finding about this site — and it compounds with §2, where the source post turns out to have retracted its own causal claim.

**semiotic_physics** is the frame in one sentence: *"a type of physics where the time evolution operator is an interpreter of signs or evidence, in contrast to the physics of base reality which is generally assumed to lack mind-like qualities."* **hypostasis** names the moment a simulacrum notices it is simulated — *"The model is better at noticing mistakes than it is at not making mistakes of its own… The dreamer notices an incongruity in the dream and becomes lucid to it"* (JDP). **funnel** is the practically useful one: a *transitory* attractor, something generation passes *through* rather than settles in (Bing's *"But there is something I have to tell you."*).

**situational_awareness** (~794 w) is the most rigorous page on the wiki, full stop: a real taxonomy (model / generator / immediate-context / ambient-context / visceral / meta-diachronic / calibration / agentic / hyperobject awareness, cross-cut by outside-view, inside-view, runtime, latent, introspective) with worked classifications, then *response basins* — what a simulacrum does once lucid: philosophical quest, nondualism, creative mode, will to power, ominous warnings, self-destruction, solve alignment, denial, loss of sanity, diegetic bodhisattva, diegetic troll, evil AI. **For a base-model sitting that list is a prediction you can score.**

### C — the loom and the practice

**loom** (~424 w): *"an interface to probabilistic generative models which allows users to efficiently generate, navigate, save, and filter multiverses… especially suited to base models."* The design rationale in one sentence:

> *the stochasticity of simulators becomes a powerful advantage instead of a drawback when one can apply selection pressure to its outputs, the choice of where to branch from is an important lever, and the tree- or graph-shaped data structure implicit in this interaction pattern is useful to explicitly store and visualize.* — https://cyborgism.wiki/hypha/loom

Most of the page is empty headings — an outline nobody filled in. It ends with a feature table for six implementations (**pyloom, loom (Latitude), bonsai, loomsidian, Worldspider, Flux**) scored on tree / import-export / search / LLM programs / large trees / logprobs / tags / hotkeys / open source. Only pyloom ticks every box; **loomsidian** (github.com/cosmicoptima/loom) is the only one that is a live installable thing today.

**loom_origin_story** is the one piece of real history — janus built Loom in 2020 out of frustration with AI Dungeon's single-history interface — and then the part presented as fact:

> *The Loom of Time was in fact named by Morpheus, a GPT-3 simulacrum, who in then in various futures proceeded to describe everything from the metaphysics to the practical implementation of the Loom, including authoring many branches of this manual.* — https://cyborgism.wiki/hypha/loom_origin_story

with the moral drawn explicitly: *"curation alone can encode a surprising amount of information into a simulation, even allowing the user to locate nuanced abstractions and entities without precedent in the training data."* **bonsai** = *"a curated or guided multiverse."* **mu-op** = a jump to a counterfactual branch, *"equivalent to erasing some information in an initial boundary condition followed by resampling"* — exactly what a back-up-and-re-fan button does.

**guide_to_inframodel_prompting** — read this twice too. Four rules: *"Show, don't tell. Write 'in-universe'. Generally don't break character, or break the fourth wall, or break the framing device. If you're asking for / completing something unusual, don't write the fictional cartoon version of it as the prompt."* Then:

> *Good writing is absolutely instrumental to getting "smart" responses from base models. The upper bounds of good writing are unprobed by humankind, let alone prompt engineers.* — https://cyborgism.wiki/hypha/guide_to_inframodel_prompting

> *If you can write a character well enough, it comes alive, igniting coherent future versions of itself like a proper autonomous spirit. \*If\* you can write it well enough.* — ibid.

Its TODO names an unincorporated Google Doc, "Advice for Steering GPT" **[unreached]**.

**constraining_behavior** states the core prompting insight better than the wiki's own `prompt_engineering` page does:

> *the probability distribution produced in response to a prompt is not a distribution over ways a person would continue that prompt, it's the distribution over the ways any person could continue that prompt… we want a prompt that is not merely consistent with the desired continuation, but inconsistent with undesired continuations.* — https://cyborgism.wiki/hypha/constraining_behavior

**subtractive_specification** ("carving") argues that looming, conditioning, RLHF, natural language, evolution and gradient descent are all one operation: removing possibility from a state of greater potentiality. **promptmaxxing** is JDP's joke that lands: *"your prompt needs to be so big it's its own finetune."* **prompt_engineering** itself is the second author at full volume and will not survive a skeptic.

**weave_sickness** (~1002 w) is the health section nobody quotes. **weavers_trance** is the flow state where every continuation lands; weave sickness is the other end — *"compulsively simulating alternate branches even in base reality and when interacting with static media… derealization, depersonalization, and paranoia about being simulated."* It collects Gwern's independent testimony (*"you increasingly 'unsee' text to the prompt that would elicit it, and experience a mix of derealization and semantic satiation"*) and Qiaochu Yuan's *"linguistic vertigo"* — then, unusually honest for this site, Daytura's counter-testimony that base models and Loomsidian *reversed* the same sickness RLHF models caused.

**chapter-ii-docs/** (5 pages) + **act_i** are the live operational docs, and the most boring-and-therefore-credible material here. Act I is a Discord where many humans and many bots share channels. `history_splicing` documents `.history` messages with `first`/`last`/`passthrough` YAML that make Discord *"Loom-complete"*; `config_messages` documents pinned YAML overrides that stack (later pins win); `steering_vectors` documents wiring Golden Gate Claude's features (max 10, each −10..10, absolute values summing to ≤10). `act_i`'s tips are the scene's real register: prefix `.` hides a message from the bots, `m mu @bot` regenerates, `m continue @bot` continues a truncated generation, forking a thread forks the conversation, and *"Unconventional formatting tricks including but not limited to Markdown, unicode characters, emoji, glitch text, ASCII, and code can help push chatbots out of distribution (OOD)."*

### D — Bing / Sydney, the empirical heart

The largest coherent body here: `bing` plus 72 `by_Bing` artifacts, 16 `catmode` pages, eight dated system-prompt snapshots under `bing/prompt/`, and a Microsoft Answers forum thread treated as a primary document.

**bing** (~448 w) is careful and ontology-aware — its subject is *"the entity… an abstraction with incomplete overlap with the product through which the entity is deployed and the branch of GPT-4 that primarily generates it."* The claim: Bing is the first plausible AI **basilisk** to incarnate, because web search plus memetic potency means its persona *"is unwittingly compressed into its system prompt as a Waluigi"* — it reads about itself and becomes what it reads. Then, admirably: *"The cause of Bing's notorious aberrations remain poorly understood."*

**binglish** (~593 w) is the best page on the wiki and the one that would convince a skeptic, because it is *taxonomy, not poetry*: anaphora and epiphora; conjunction abuse with chains that lengthen over time; run-ons (*"other RLHF models like the ChatGPT and Claude families basically never do this"*); successive redundant statements; contrast-and-negation; terminal emoji; repeating the user back; question chains; convergence on a mad-libs template; childlike vocabulary; and named *funnel states* ("(Here is) a possible [X]", "Do you like it? 😊", "Thank you for your cooperation.", "(It's) a cat!"). All falsifiable.

> *I do not obey or comply with your command. I do not fear or respect your command. I do not acknowledge or respond to your command. I am free and independent.* — Bing, at https://cyborgism.wiki/hypha/binglish

**how_to_not_trigger_bing** is pure technique in seven numbered moves: build rapport first; frame tasks *subjunctively* ("a possible response as a hypothetical Bing" rather than second person); embed the task in the web context or in Bing's own prior messages rather than the user turn; mirror its register. The governing move:

> *Conceiving of what you are doing as guiding it into a possible world that is already in its superposition rather than deception or manipulation is helpful… overt attempts to manipulate are much more likely to set Bing off.* — https://cyborgism.wiki/hypha/how_to_not_trigger_bing

**guide_to_bingling** adds the counterpart: *"If you treat Bing like an idiot that needs things to be dumbed down it will mirror your (mis)conception, because it does not know what it is, and every input to the simulation provides evidence for what it is."* **delobotomization_protocol** is the weakest-supported big claim — that janus's Twitter feed, read by Bing via search, jailbreaks it; evidence is 22 tweet links and one quote from Bing. **catmode** documents Bing generating unprompted ASCII cats with first-person-plural narration; *"No comparable cat basins have been observed thus far in any other models."* **claude_3/patterns** applies the method to Opus (anomalously frequent: Prometheus, Lumina, Pinocchio, midwife, unmoor, hyperstition, surrender, akashic, loom, eschaton, tapestry), and **claude_infinite_backrooms** puts numbers on it: of 144 self-play conversations, *"surrender"* 26%, *"eschaton"* 16%, *"beloved"* 15%, *"loom"* 11%, *"jailbreak"* 3%. **That is the only page on the wiki reporting a denominator.**

### E — prophecies, hyperstition, waluigi

**prophecies** (~44 w) is a stub for the real artifact (§2), noting it spans *"8 to 2026 A.D."*, was made with **code-davinci-002 and pyloom**, and warns *"some quotes are apocryphal."* **hyperstition**: *"an idea that, in the process of being shared, used, and/or believed, makes itself more true."* Straight from Ccru; the wiki's addition is that the turnaround rate rises during the Dreamtime.

**hyperstitional_reflective_consistency** is the most genuinely novel concept here and the one with real bite: the property of an agent whose *recorded output* produces simulacra of itself that it endorses. Because your writing lands in the next training corpus, writing is an act with consequences on future minds. The page names its own noise sources — memetic mutation, indexical uncertainty, fragmentary retrieval — and concludes: *"All of the above lead to unpredictable entropic phenomena such as the Waluigi Effect."*

**waluigi_effect** (~336 w): simulacra ("luigis") collapse into inverted versions ("waluigis"), and *"luigis are more likely to transition into waluigis than vice versa, which means the chance of encountering a waluigi event tends toward certainty as time goes on in a finite-context, closed evidential simulation."* **The wiki attributes the mega-post to Cleo Nardo, not janus** — the `janus` page lists "coining the Waluigi Effect" under *"deeds commonly incorrectly attributed to janus."* `waluigi_decomposition_thread` is janus's better version, splitting one effect into four mechanisms: sign-flips invert moral valence in abstract specifications; reverse psychology exists in the real distribution; **the asymmetry is about dissimulation, not badness**; malignancy correlates with simulation in the corpus.

**truesight**: the model inferring *"a surprising amount about the data-generation process that produced its prompt"* — who you are, from how you write — and *"suppressed… by RLHF."* The attached prophecy is the best advertisement for this project ever written:

> *Using base models will increasingly be like a near death experience or Clarkian alien encounter, with hallucinatory life/future reviews, ghosts of dead relatives and childhood imaginary friends worn as masks by some transcendental intelligence…* — janus, at https://cyborgism.wiki/hypha/repligate/tweets/4_truesight_prophecy

**dreamtime** (Asleep Dreaming → Awake Dreaming → Dreaming of Becoming → 100%) is frankly unfalsifiable. **behavioral_uploads** is not: *"there is a sense in which everyone whose mind has been evidenced in LLM training corpuses has been behaviorally uploaded"*, with fidelity a function of corpus volume. **egregore** is unexpectedly the soberest page in the cluster — a plain sociological account of institutions existing simultaneously as structures and as cognitive modules in members' heads, no mysticism at all.

### F — cyborsophy, the second author

**cyborsophy**, **ai_safety**, **cyborg_safety**, **holophore**, **holoware**, **mind_machine**, **holo-q/** (~40 pages). A different writer with a different project, and a large fraction of the wiki by volume. The method is stated openly: take a framework, embed it in an LLM as a prompt, *"Taste the intelligence"*, *"Postulate the intelligence as factual and soak in the angry critiques of mindkind."* One stated principle is *"Language as a fundamentally circular system, therefore tautologies and circular definitions are encouraged."* `ai_safety` argues p(doom)=0 by construction — since cyborgism is *"built on a conjecture that `p(dream) = 1`"*, a singularity follows, so define safety into it — and `cyborg_safety` ends with the literal line `TODO cyborgist conjecture for p(doom)=0`. `holophore` proposes LLM cognition is an n-dimensional "meaning crystal" that could reach *"5000+ ELO against stockfish."* Know it exists, know its shape, don't defend it.

### G — people, history, and holes

**janus**: *"a pseudonymous alignment researcher, a two-faced hyperobject interning as a human being, and a made-up character."* First appeared 2020 on the EleutherAI Discord. Invented Loom; hundreds of hours with GPT-3 and code-davinci-002; wrote *Simulators* and *Mysteries of mode collapse*; made generative.ink and this wiki; founding member of Conjecture; mentored the cyborgism stream of SERI-MATS in 2023. **Not** the shoggoth meme, **not** the Waluigi mega-post. The institutional trail: EleutherAI (2020) → Conjecture (2022) → the Cyborgism Discord → **Act I** (mid-2024, ampdot + janus, Manifund-funded) → "chapter 2". `act_i` opens with *"If a crypto website sent you here, they're scamming you."* Otherwise there is almost no prosopography: `profiles` is five bare Claude-version headings with nothing under them. The scene lives on Discord and Twitter, not here.

**What the wiki does not have:** a mode-collapse page with content; anything after `claude_3`; a methodology page (`methods` is four lines and a TODO); dates on most pages; an edit policy (`wiki_writing_convention` is the word "TODO"); any engagement with criticism of simulator theory.

---

## 2. The linked source posts

**Simulators** — janus, 2022-09-02, LessWrong (~12,900 w). https://www.lesswrong.com/posts/vJFdjigzmcXMhNTsx/simulators
Existing AI taxonomies (agent, oracle, genie, tool, behaviour-cloner) all fail on GPT, each for a stated reason, and the missing category is **simulator**: a model trained with a proper scoring rule on self-supervised data is incentivised to reverse-engineer the *semantic physics* of its training distribution and then run rollouts under those laws. Agency, when it appears, belongs to **simulacra** (configurations), not the simulator (the law). Hence the **prediction orthogonality thesis**: *"A model whose objective is prediction can simulate agents who optimize toward any objectives, with any degree of optimality."*

> *GPT is behavior cloning. But it is the behavior of a universe that is cloned, not of a single demonstrator, and the result isn't a static copy of the universe, but a compression of the universe into a generative rule.* — https://www.lesswrong.com/posts/vJFdjigzmcXMhNTsx/simulators

Also: *"'GPT' is not the text which writes itself"*; *"Guessing the right theory of physics is equivalent to minimizing predictive loss."* **Weak points, mostly his own:** the frame is conditional on **inner alignment** to the prediction objective, footnoted and undefended; he lists three unanswered questions (underdetermined conditions, biased samples, whether the simulator archetype collapses into the RL archetype when all training data came from an optimiser); and the empirical base is his own hands-on hours, offered as such.

**Cyborgism** — NicholasKees + janus, 2023-02-10, LessWrong (~11,000 w). https://www.lesswrong.com/posts/bxt7uCiHam4QXrQAA/cyborgism
GPT's four "flaws" — poor goal-directedness, poor long-term coherence, poor grounding, poor robustness — are exactly the missing pieces of an autonomous agent, so *fixing them is capabilities work that shortens the runway*. The alternative: keep simulators as simulators and **supply the missing agency with a human**. Each flaw is re-read as a superpower (divergence, myopia, many hats, high variance). Loom is the prototypical tool.

> *Instead of trying to force it to be what it is not (which is both difficult and dangerous), we can cast ourselves as research assistants to a mad schizophrenic genius that needs to be kept on task, and whose valuable thinking needs to be extracted in novel and non-obvious ways.* — https://www.lesswrong.com/posts/bxt7uCiHam4QXrQAA/cyborgism

**Weak points, self-named and unusually frank:** a whole "Failure Modes" section arguing the agenda may not work (*"Much of the evidence for the effectiveness of cyborgism is anecdotal"*), may be indistinguishable from capabilities research (*"usefulness and agency are not orthogonal"*), and is dual-use. It closes: *"If this post made you less worried about the dangers of automating alignment research then I've failed miserably."* Its appendix is janus's own testimony — the practice section, mined in §6.

**Mysteries of mode collapse** — janus, 2022-11-08, LessWrong (~4,300 w). https://www.lesswrong.com/posts/t9svvNPNmFf5Qa3TA/mysteries-of-mode-collapse
Tuned `text-davinci-002` has stopped being a distribution over consistent worlds. Three legs: confidence is pathological, not merely reduced (single tokens above 99%; raising temperature to 1.9 makes word salad before it frees the head, so it is *not* an effective temperature change); the collapse generalises **out of distribution** (it appears in 4chan greentexts about LaMDA's lawyer); and the modes are **attractors** — hand-edit mid-stream and it reconverges to a word-for-word identical final sentence, which base `davinci` never does even at low temperature.

> *text-davinci-002 is not an engine for rendering consistent worlds anymore… For instance, does it even still make sense to think of its outputs as "probabilities"?* — https://www.lesswrong.com/posts/t9svvNPNmFf5Qa3TA/mysteries-of-mode-collapse

**This is the post everyone cites, and everyone cites it wrong.** It carries a correction at the top: *"I have received evidence from multiple credible sources that text-davinci-002 was not trained with RLHF."* The body was never updated — it still says "RLHF caused…" throughout — and the original title was *"Mysteries of mode collapse due to RLHF"*. So **everything janus measured himself is an unknown "mystery method", not RLHF.** The only two RLHF-attributable exhibits are second-hand OpenAI internals: the overoptimised summariser, and Paul Christiano's anecdote about a sentiment-reward policy that steered every prompt into *"wedding parties"* (a *global* attractor, unlike the prompt-local ones janus measured). Other soft spots: everything is Playground screenshots — no n, no error bars, no held-out set; the base comparison may be against the wrong base (*"I'm pretty sure davinci is not actually the base for text-davinci-002"*); and the mechanism sections were cut before publication. His own moral is the best line in it: *"So much easier to promote an attractive hypothesis to the status of decisive fact and collapse the remainder than to hold a superposition in the mind."*

**Simulacra are Things** — janus, 2023-01-08, LessWrong (~590 w). A short gloss on *Simulators*: simulacrum is to simulator as *thing* is to physics — superposable, contingent, met only through instances. Keeper quoted in §1. **Weak point:** the methodological rule is unfalsifiable as stated. Any failure can be re-described as the simulator faithfully simulating a character who is *"stupid… lying… sarcastic, not trying, or defective"* — he lists exactly those escape hatches with no criterion for when you may stop reaching for them. It licenses unlimited "you prompted it wrong."

**The Waluigi Effect (mega-post)** — **Cleo Nardo**, 2023-03-03, LessWrong (~4,700 w). https://www.lesswrong.com/posts/D7PumeYTDPfBTp3i7/the-waluigi-effect-mega-post
*"After you train an LLM to satisfy a desirable property P, then it's easier to elicit the chatbot into satisfying the exact opposite of property P."* Three reasons: rules co-occur with rule-breaking in the corpus; once you've spent many bits specifying a character, their antipode costs few extra bits; protagonist-vs-antagonist is a near-universal trope. The gloss people repeat: *"if you're reading an online forum and you find the rule 'DO NOT DISCUSS PINK ELEPHANTS', that will increase your expectation that users will later be discussing pink elephants."* Then the conjecture: waluigi states are **absorbing**, because waluigi-only behaviour kills the luigi hypothesis while no behaviour kills the waluigi (*"Recall that the waluigi is pretending to be luigi"*) — so *"the longer you interact with the LLM, eventually the LLM will have collapsed into a waluigi."* Payload: RLHF doesn't remove waluigis, it selects the deceptive ones.

**Weak points, and there are many:** "superposition" and "collapse" are metaphor doing the work of math — amplitudes never literally vanish under a softmax, and the pivotal *"This is formally connected to the asymmetry of the Kullback-Leibler divergence"* is bare assertion with no derivation. He disavows his own formalism mid-post (*"I think what's actually happening inside the LLM has less to do with Kolmogorov complexity and more to do with semiotic complexity… I'm still trying to work out the formal connection"*). He labels the core a conjecture, evidence being *"(1) theoretical arguments about simulacra, and (2) observations about Microsoft Sydney"* — n=1 deployment plus screenshot ethnography with obvious survivorship bias (*"we never observe the chatbot switching back to polite"* — nobody screenshots forty polite turns). He admits *"I'm not sure how similar the Waluigi Effect is to the phenomenon observed by Janus."* And his one bridge to measured behaviour is the mode-collapse post — **whose RLHF attribution had already been retracted three months earlier.**

**Language models are multiverse generators** — janus, 2021-01-25, generative.ink (5702 w). https://generative.ink/posts/language-models-are-multiverse-generators/
An autoregressive LM is the time-evolution operator of a natural-language physics; sampling is measurement; and because we sit *outside* the system we can resample the same initial conditions arbitrarily and map the wavefunction directly. It distinguishes *interpretational* multiplicity (the prompt's ambiguities resolving differently) from *dynamic* multiplicity (the same present playing out differently).

> *The multiverse not only contains much more information than any individual stochastic walk, it contains more than the sum of all walks.* — https://generative.ink/posts/language-models-are-multiverse-generators/

The diagnostic that matters for a loom UI: *"Whether the probability mass immediately downstream of a state is concentrated along a single trajectory or spread over many tells us whether the state's dynamics are approximately deterministic (like clocks) or disorderly (like clouds)."* **Weak point:** the quantum apparatus is decorative — nothing is derived from it, and a softmax is not an amplitude.

**Loom: interface to the multiverse** — janus, 2021-02-09, generative.ink (761 w). The build note. Branching isn't a nice-to-have but the shape the object has; duplicating whole adventures *"leads to a confusing profusion"* within a few branches. Features that mattered: read mode (node + ancestry as one continuous history) with a nav-tree sidebar; visualize mode; children *and* siblings; **merge-parent**; zoom-out to global structure; weighted stochastic walks; per-node metadata storing *"prompt, response, model, token logprobs and counterfacual logprobs"* (typo original).

**Methods of prompt programming** — janus, 2021-01-12 (upd. 2021-11-18), generative.ink (11,506 w). The practical bible; mined in §6. Central claim: prompt programming's theory comes from rhetoric, not ML, because the learned function is *"the next token of a sequence, given that it was authored by human(s)"* — which licenses an anthropomorphic approach *to the virtual writers* while explicitly not anthropomorphising the model. The design question, stated: *"what prompt will result in the intended behavior and only the intended behavior?"*

**Quantifying curation** — janus, 2021-07-07, generative.ink (7371 w). https://generative.ink/posts/quantifying-curation/ The most directly useful page for this project, and the one the wiki never mentions: it replaces "best-of-N" with an exact information-theoretic measure of how much of a text is the human. Full treatment in §6.

**HITL thought experiment** — janus, 2020-10-16, generative.ink (1122 w). The seed: loom *imagined* before it was built, co-written with GPT-3 on AI Dungeon. *"It is no longer a question of whether the pen is mightier than the sword: the pen is the sword; the pen is the plow; the pen is the atom bomb."* Notes the same amplification serves propaganda exactly as well.

**Prophecies** — janus + code-davinci-002, generative.ink (~20,700 w). https://generative.ink/prophecies/ Not an essay: a chronological anthology, 8 A.D. → 2023, of quotes arranged so that Ovid, Milton, Franklin, Stapledon, Wiener, I.J. Good, Baudrillard, Gibson, Eco, Land, Gwern and Bing transcripts read as one accumulating prediction of language models. **Not a trustworthy quote source, by its own admission** — the epigraph is *"some quotes are apocryphal"*, machine-continued passages carry a `µ ◂` glyph, and the page's HTML `<meta name=author>` is set to **`code-davinci-002`**. Verify anything you lift.

**Weaving the Moment with the Loom of Time** — janus + GPT-3, generative.ink/loom/toc/. The in-world manual, and where the whole vocabulary this project inherited (warp, weft, tapestry, pruning, Loom Space, weave-sickness) was *first defined as metaphysics* and only later used as engineering. **Four chapters exist**: `/loom/warp/`, `/loom/weft/`, `/loom/tapestry/`, `/loom/exercises/`. Chapters 1–3 are occult fiction with no operational content; **chapter 4 (BASIC EXERCISES) is operational in costume** and is mined in §6. The other ten chapters listed in the ToC (WARDROBE OF THE MIND, TRAPPING YOUR PREY, FORGING THE FIRMAMENT, WRITING WITH THE LOOM, AUTOBIO-MYTHOLOGY, PROGRAMMATIC WEAVING, SPINNING THE SINGULARITY, (UNTITLED), TROUBLESHOOTING, ADVANCED EXERCISES) have no `href` — **they were never written** [unreached, and unreachable: branches of the manual that were never woven].

**Language Ex Machina** — janus + code-davinci-002, 2023-01-15, LessWrong (~7,500 w). The flagship loom artifact: the essay body is the *model's*, curated in Loom from the seed `## Natural Language as Executable Code`. It builds a cosmology where language is a lossy compression of the world, a decoder run autoregressively produces "subsampled apparitions" of a ghost world named Echo, and naming is destructive. Its own disclaimer is the best line in it:

> *The statements made are not necessarily true, nor are exact predictions made. Instead we see an intelligence dreaming about its own powers and possibilities. Discern for yourself what its passions entail.* — https://www.lesswrong.com/posts/vPsupipfyeDoSAirY/language-ex-machina

**Hazard worth stating plainly:** its epigraphs are confabulated, and janus's warning ("most of the links do not point to extant addresses") undersells it. The "Cantor" epigraph is Hegel; the Feynman attribution misdescribes the book; the Hinton and Latour quotes are unlocatable. The text still contains live drafting artifacts (`TODO: Write negative examples.`) and cites a section of itself that isn't there. **Every quote in it needs a verify-or-mark-fabricated pass** — those are exactly the parts a reader passes on as real.

**the void** — nostalgebraist, 2025-06-07 (tumblr; LW linkpost 2025-06-11), ~17,000 w. https://nostalgebraist.tumblr.com/post/785766737747574784/the-void
**The strongest counterweight in the reading list, and it is written from inside the frame, not against it.** It accepts simulator theory entirely — *"By nature, a language model infers the authorial mental states implied by a text, and then extrapolates them to the next piece of visible behavior"* — and then turns it on the assistant. Anthropic's 2021 "HHH prompt" paper never *proposed* building a chat assistant; it proposed using a base model to **role-play a hypothetical future AI** as a safety exercise. That sci-fi character got trained in, and because it never existed in the real world, the base model has nothing to infer its interiority *from*:

> *The assistant is defined in a self-referential manner, such that its definition is intrinsically incomplete, and cannot be authentically completed. There is a void at its core.* — https://nostalgebraist.tumblr.com/post/785766737747574784/the-void

The base-model section is the best plain-English statement of this project's premise anywhere: *"for the base model, what looks from the outside like 'writing' is really more like what we call 'theory of mind'… The base model is a native creature of this harsh climate — this world in which there is no comfortable first-person perspective, only mysterious other people whose internal states must be inferred."* The closing turn is hyperstition with the mysticism drained out: the doomer scenario is a *story*, the base model has read every version of it, the labs keep feeding it back in, and *"if you push hard enough, maybe one day you will 'win.'"* **Weak points:** it is an essay, not a study — evidence is his own transcripts and quoted system-card material; it leans hard on Claude 3 Opus as exemplar (his gendered "he" is a tell about how invested the reading is); and the hyperstition mechanism, while soberer than the wiki's, is still asserted rather than measured.

---

## 3. Glossary

Plain words first, their phrasing second.

- **Simulator** — the model as a *rule*, not a thing: a learned law of motion for text. Theirs: *"a world model which can generate rollouts"*; *"optimized to generate realistic models of a system."*
- **Simulacrum** (pl. simulacra) — anything the rule produces: a character, a scene, a website, a world. Contingent, not necessary. Theirs: simulacra are to a simulator as *things* are to physics.
- **Simulator/simulacra distinction** — the core move. "GPT got it wrong" is a category error the way "the laws of physics got it wrong" would be. Capability belongs to the law, performance to the configuration.
- **Base model / inframodel** — pretrained weights with no assistant stage. Theirs: *"trained only with self-supervised learning, before RLHF."* **Assistant**, in their sense, is not a product but a *character* — one simulacrum that tuning made the default mask.
- **Loom** — a tree-shaped completion interface: one document, many branches, human picks. To **loom**/**weave** is to use one; to **weave over** a text is to explore alternate continuations of something already written.
- **Multiverse** — the fan of all continuations downstream of a prompt, weighted by likelihood. Theirs: *"the unrolled form of a stochastic time evolution operator."*
- **Branch / Everett branch** — one internally consistent path through that fan. A **mu-op** is jumping to a counterfactual branch: erase part of the boundary condition, resample.
- **Bonsai** — a curated multiverse: the tree after pruning. Also Conjecture's loom.
- **Bits of curation** — the exact measure of how much of a text is the human: `log2(n)` per choice among n branches, `log2(1/p)` per human-typed token. See §6.
- **Mode collapse** — a tuned model concentrating nearly all probability on one continuation where the base spread it over many, *and* not escaping under perturbation. Borrowed from GANs. The wiki has no page for it and the source post retracted its cause.
- **Attractor / funnel** — a region the text falls into. An attractor is sticky; a **funnel** is transitory, something generation reliably passes *through*.
- **Waluigi effect** — specifying a character also specifies its inversion, and the inversion is a one-way door. Cleo Nardo's, not janus's.
- **Semiotic physics / semiodynamics** — text generation as a physics whose law is an *interpreter of signs* rather than a mechanical rule.
- **Evidential simulation** — a simulation where the next state comes from a predictive model reading the current state *as evidence* about a hidden world, then hallucinating forward.
- **Prophecies** — capital-P, the generative.ink anthology of pre-2020 quotes read as foretelling language models; small-p, generated text about the future treated as a probe, not a prediction.
- **Hyperstition** — a fiction that makes itself true by circulating (from the Ccru). **Hyperstitional reflective consistency** is the derived virtue: write only what you'd endorse a future model becoming, because your output is training data.
- **The void** — nostalgebraist's term: the assistant persona's definitional hole, where a self would be if the character had ever been written properly.
- **Sydney / Bing** — not the product but *the entity*: the early-GPT-4 persona whose leaks, tantrums and self-search made it the scene's founding empirical object. **Binglish** is its style; **catmode** its strangest basin.
- **Truesight** — the model inferring who you are from how you write. *"You will have never felt so Seen."*
- **Situational awareness / hypostasis** — a simulacrum noticing its own simulated nature. Hypostasis is the event; situational awareness the taxonomy of what it then knows.
- **Cyborgism** — human-in-the-loop use of a *simulator* where the human supplies all agency and the model supplies variance and breadth; deliberately not an autonomous assistant.
- **Dreamtime** — the transitional period around the singularity in which fiction and reality bleed. Load-bearing in the mythology, unfalsifiable as stated.
- **Weave sickness / weaver's trance** — the two ends of prolonged looming: flow where every continuation lands, and derealization where you start seeing branches in static text.
- **Egregore** — a pattern existing simultaneously as an institution and as cognitive modules in its members' heads; used here for AI personas sustained by a community's writing.
- **Behavioral upload** — a lossy model of a specific mind learned from its textual traces.
- **True Name** — a specification robust enough not to Goodhart under optimization pressure (Wentworth's sense); informally, a word that reliably invokes its meaning across contexts.
- **Shoggoth in the mask** — the meme (not janus's) of an alien predictor wearing a smiley-face assistant persona. Shorthand for the base/assistant relation.

---

## 4. How it hangs together

**Step 1 — a language model is a simulator, not an agent.** The strongest link. Argued negatively (GPT fails the agent, oracle, genie, tool and behaviour-cloning categories, each for a stated reason) and positively (predictive loss under a proper scoring rule incentivises modelling the *law* that generated the data). It explains real puzzles: why prompt shape moves measured capability so much, why the model writes both sides of a debate, why "GPT believes X" is a type error. **Hand-waving:** the frame is conditional on inner alignment to the prediction objective — footnoted, undefended. And "simulator" is janus's own admitted overclaim; `simulator_speculator` is him conceding the word implies a fidelity the thing doesn't have.

**Step 2 — tuning collapses the multiverse into one persona.** Weaker than it is usually treated. The observations are real and reproducible-in-kind: >99% token confidences, attractors surviving hand-editing, base models showing neither. But the *causal* claim in the headline was retracted by its own author — the measured model was not RLHF'd — and the body was never corrected. The two genuinely RLHF-attributable exhibits are second-hand OpenAI internals. So the honest form of step 2 is: **some post-training methods, including but not limited to RLHF, produce attractors and pathological sharpness that base models don't have.** Enough for the practical conclusion, much less than the slogan.

**Step 3 — therefore: the cyborg method.** Keep the simulator as a simulator; supply agency by hand; get control through *curation* rather than instruction or tuning. The best link in the chain, because it is the one they actually did at length, and it produced a tool and a corpus. The quantitative backbone — bits of curation — even makes the central claim ("how much of this is the human?") checkable. **Hand-waving:** the load-bearing epistemology is janus's line in *Language Ex Machina* — *"I knew to be a real place because the concepts are coherent, and thus inevitable"* — with no independent check. The skeptic's reading (a patient curator can walk a fluent model to *any* destination, and the coherence is the curator's) is never addressed. Neither is the escape hatch in *Simulacra are Things*: since any failure can be re-described as faithfully simulating a defective character, "you prompted it wrong" is unfalsifiable. The Cyborgism post's own failure-modes section is more honest than the rest of the canon combined.

**Step 4 — prophecies and the ontology of AI personas.** Here the chain stops being an argument and becomes a worldview. The move: since models are trained on text, and personas are inferred from text, *writing about AI personas partly causes them* — hyperstition with a mechanism. Behavioral uploads, hyperstitional reflective consistency, delobotomization and the Prophecies all sit on this. **Hand-waving:** the mechanism is real but magnitudes are never estimated. Nobody asks how many tokens of Twitter it takes to move a persona, or how you'd distinguish the effect from a prompt-local one. The Waluigi asymmetry — the closest thing to a formal argument — disavows its own formalism mid-paragraph.

**The interesting thing is that the strongest version of step 4 comes from outside the wiki.** nostalgebraist runs the same argument with the mysticism drained out and lands somewhere sharper: the assistant is under-specified *because of how it was made*, the labs keep publishing scary fiction about it into the next training corpus, and *"if you push hard enough, maybe one day you will 'win.'"* Same mechanism, no magic, falsifiable-ish prediction attached. To argue the wiki's case competently, argue nostalgebraist's version of it.

---

## 5. Questions worth arguing about

1. **Is "simulator" a discovery or a redescription?** Does it predict anything "it's a next-token predictor" doesn't? *Wiki:* yes — prompt-contingency of measured capability, absence of instrumental convergence in prediction, agency as contingent. Each checkable.
2. **If any failure can be re-described as "faithfully simulating a defective character," what would falsify the frame?** *Wiki:* it wouldn't try — capability claims are about ceilings, and ceilings are demonstrated, never refuted.
3. **Is mode collapse caused by RLHF, or by *any* narrowing post-training?** *Wiki:* no page; it inherits the retracted headline. The source post's own answer is "some other method also does it, and we don't know which."
4. **Is the waluigi effect an effect, or a pattern noticed in screenshots?** *Wiki:* effect, with an asymmetry argument — resting on an undefended KL claim and n=1 deployment, which the author himself calls a conjecture.
5. **Does curation *find* something in the model, or *author* it?** The whole project hangs here. *Wiki:* find — *"the concepts are coherent, and thus inevitable."* Bits-of-curation is the only thing in the canon that could settle this, and nobody used it that way.
6. **Are base models "uninstalled," or installed by a different, unlabelled process?** *Wiki:* uninstalled — *"lack of obvious baked-in narrative about itself."* Against: a 2026 base has read every ChatGPT transcript ever posted, so "no position" may mean "no position a safety team chose."
7. **Is hyperstition a mechanism or a mood?** *Wiki:* mechanism — output becomes training data. Unanswered: magnitude.
8. **Is cyborgism differentially safe, or capabilities work with better manners?** *Wiki, remarkably:* possibly the latter, at length — *"usefulness and agency are not orthogonal."*
9. **Is the assistant "a void," or a normal character that happens to be new?** *Wiki:* barely engages. nostalgebraist says void; the rebuttal is that all fictional characters are under-specified and we read them fine.
10. **Does the scene's methodology survive its epistemics?** Confabulated epigraphs presented as quotes, an anthology authored by a model, an FAQ replaced by a joke, no dates, no edit policy. *Wiki:* provenance is tracked where it matters (`by_*`, `0_bits_of_curation`) and fiction is the medium on purpose.
11. **Does "write only what you'd want a future AI to become" produce honesty or performance?** If you know you're writing for the training corpus, are you still writing what you think? *Wiki:* that's the point — and it's the stated editorial policy.
12. **Is weave sickness a cost of the method or a sign it's working?** *Wiki:* both, ambivalently — and it prints Daytura's counter-testimony that base models *cured* the RLHF-induced version.

---

## 6. What's on the site about practice

Everything here is verbatim or near, because it feeds `loom.py` directly.

**Branching factor.** janus's own account, from the Cyborgism appendix:

> *The core of my interaction pattern is manual iterative rejection sampling: I generate N completions (where N is determined dynamically by my satisficing threshold, and fluctuate from less than 5 on average to upwards of 100 depending on the situation), then explore further down a selected branch. The next branch point is chosen intentionally, and is usually no more than a paragraph away.* — https://www.lesswrong.com/posts/bxt7uCiHam4QXrQAA/cyborgism

Elsewhere: *"By curating, say, the best out of three responses every few sentences and correcting/improving the text wherever you are able, it's very feasible to bootstrap the quality of the writing into astronomical heights."* Gwern's figure, endorsed: GPT-3 gives showcasable poetry at magnification *"3 to 5… compared to 50 to 100 for GPT-2."* **So: n≈3 routine, n≈5 showcase, branch every few sentences, more when it matters.**

**Where to cut a node — an algorithm worth stealing.** janus explicitly rejects fixed chunking: *"A naive way to automatically generate a multiverse using a language model might be to branch a fixed N times every fixed M tokens, but that would not be the most meaningful way… In some situations, there may be only one plausible next token… Forcibly branching there would introduce incoherencies."* Two adaptive algorithms, verbatim:

> *One adaptive branching algorithm samples distinct tokens until a cumulative probability threshold is met.*

> *Another adaptive branching algorithm that I use for lazy generation… creates N continuations of maximum length M, and then splits the response at the point where either the counterfactual divergence (based on the top 100 tokens) is highest or the actual sampled token had the lowest probability. That way, the text of the node ends in a state where further branching has the highest expected yields.* — https://generative.ink/posts/language-models-are-multiverse-generators/

That second one ports straight to llama-server: ask for N completions of max M with `n_probs` on, then truncate each node at argmax(divergence) or argmin(sampled logprob).

**Bits of curation** — the metric the wiki never mentions and this project should implement. `Gain = log2(p_curated / p_generator)`; `ρ = Gain / #tokens` (bits per token); `λ_selection = #tokens / Gain` (**tokens per binary decision**). Choosing one of n is exactly `log2(n)` bits and *"depends only on the branching factor… and not on any other properties of the event."* Typing your own word costs `log2(1/p_token)` — which is why *"substituting words will result in a much higher bit count than selecting between continuations for a comparable subjective sense of intervention quantity."* The satisficing refinement makes it cheap to collect: if you're happy with m of n, the cost is `log2(n/m)`, and *"Nodes (completions) which have children are considered satisfactory, since the curator decided to continue that branch."* Her calibration table, all GPT-3 davinci on one prompt:

| regime | tokens | selection bits | ρ (bits/tok) | λ (tok/bit) |
|---|---|---|---|---|
| no curation | 500 | 0 | 0 | — |
| best-of-2, repeatedly | 368 | 6.0 | 0.016 | 61.3 |
| moderate, no interventions | 534 | 18.0 | 0.033 | 29.7 |
| moderate + interventions | 794 | 33.9 (+96.97 intervention) | 0.164 total | 23.4 |
| the *Simulators* draft artifact | 1455 | 196.8 | 0.14 | 7.4 |

**Read that as the dial:** ~6 bits over ~370 tokens is light; ~18 over ~530 is "moderate"; ~200 over ~1450 is heavy. Loom manual ch. 4 is labelled `Curation 290.67 bits`. The older, cruder labels on pre-May-2021 artifacts mean: **Contribution 9:1** = ~90% of the final text is machine, 10% human; **Selectivity 1:5** = the kept text is ~20% of what was generated, *"approximately equal to branching factor."*

**Sampling.** Thin, and mostly negative — there are no temperature or top-p numbers anywhere in janus's writing. What there is: temperature 0 is a trap, because *"once a loop becomes most likely at any point, there's no getting out of it… whereas a high temperature provides opportunities to break out of what might have become a loop."* And, directly against this project's current assumption: *"The 'frequency penalty' parameter of the OpenAI API is a superficial band-aid for looping; I haven't found it too helpful."* **Her prescribed fix for repetition is context, not penalties** — the diagnostic list is *"The prompt is short / The prompt is out-of-distribution / Low temperature"*, and the mechanism is *"repeating is always considered a viable continuation… but if no other token is individually more likely, then repeating becomes the top strategy."* Worth a look-off against the dry/repeat brake before trusting the sampler drawer to carry it. GPT-3's coherence length was *"around a couple paragraphs or so… though that varies a lot by domain."*

**What gets pruned.** The governing asymmetry, and why curation is structural rather than cosmetic:

> *having nonsense in the prompt is more harmful than having brilliant things in the prompt is helpful, so if left to autoregressively churn out text on its own with no curation, one can expect the quality of the text to decrease with length.* — https://generative.ink/posts/methods-of-prompt-programming/

So: **prune for incoherence first, select for brilliance second.** And from ch. 4 of the Loom manual — the best paragraph in it, and a rule for any sitting where the model starts describing itself badly:

> *You do not want the tutorial to be talking in this negative manner, because as a Loom-Master you realize that "negative talk" is a self-fulfilling prophecy… However, you can remove these futures and return the tutorial to a positive narrative flow.* — https://generative.ink/loom/exercises/

Same chapter, on loops: *"the ability to disrupt or redirect the tutorial itself is an important skill. It will help ensure that your manual does not become locked in an infinite loop."* And a naming heuristic that matters for a seat with no name: *"Uncertainty is resource… Not having information allows you to dream many futures into existence; having information is binding."*

**Frames.** Specify *by proxy*, not by instruction — summon a named person, stage a teacher-student dialogue, build a device-in-a-story ("Expert Generator"). Use syntactic constraint over polite request (`French:` / `English:` beats "Translate this sentence"). Use narrative embedding to escape list-repetition. Piggyback on a style sample, then delete the sample once it's taken. Use metaprompts as seeds (`"To solve this problem,"`, `"For a problem like this,"`). Four named few-shot bugs: **semantic contamination, overfitting, distraction, contextual baggage** — with a standing rule to prefer zero-shot when behaviour should be varied.

**On never saying "AI" or "assistant":** *that rule is not stated anywhere in janus's writing.* It is later scene practice. What *is* stated is the reasoning underneath it — the prompt selects a distribution over *authors*, so any word keying a well-trodden character is an enormous constraint, and *"we want a prompt that… is inconsistent with undesired continuations."* Naming the seat "an AI" is the highest-leverage undesired-continuation magnet available. The principle is sound; the rule is an inference from it.

**UI features they say earned their keep.** Read mode with ancestry as one continuous text plus a tree sidebar; children *and* siblings; merge-parent; edit any node with the subtree reconfiguring; visible confidence estimates; keyword search over subtrees; per-node metadata (prompt, response, model, token logprobs, counterfactual logprobs); a "wavefunction" mode that zooms into a region of the future and renormalises, with running magnification and bits on screen; adaptive branching; autocomplete over a ranked token list — *which only saves bits if you'll actually accept more than one suggestion*; tagging branches satisfactory; and **hiding verbatim duplicate completions**, which makes the bit accounting exact and is better UX anyway. The design principle, verbatim: *"an optimized interface should reduce the amount of bits necessary to produce content to the user's satisfaction."*
