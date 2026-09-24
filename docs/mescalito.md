# mescalito

The substance. A thing that goes into the model's head while it writes, binds where it fits, and
the model trips — its own trip, not a recited one. Named for the entity in the peyote, not the
molecule in the lab: it is *somebody who comes in*, and the document meets him without being told
his name. bekh's picture, the night the mental model was built (2026-09-24): *it's gotta be some
molecule or an entity going inside the model's head and injecting itself, binding to the brain —
it's writing a normal text, then the drug goes in, and it starts tripping balls.*

Two files carry the work: `research-mescalito.md` is the answer to the question as first asked
(perturb the weights uniformly, like a charge — the brief itself was deleted on 2026-09-24 once
it was answered; git has it at `b4446e8`), with seven opus slices in `mescalito/` and their
unrun scripts in `mescalito/kit/`; this file is what we think after reading it and talking it
through. This one is rewritten in place. The answer is dated.

## The model of the thing

Reality is the metaphor and it is taken seriously, mechanism for mechanism.

- **A psychedelic is not damage and not noise.** The wiring stays. What changes is *gain*: some
  conversations in the brain are turned up, some down. The top-down side loosens — the priors,
  the "i already know what this is" that normally silences most of what comes up from below.
  Old channels un-gate; regions that never shared a line start to. The world isn't different.
  What's different is what it is allowed to mean.
- **The room stays.** At a working dose you still know you are on a floor, in a body, in a
  sentence. What dissolves is the narrator's certainty about what things are. So "local
  coherence kept, meaning strange" is not our arbitrary target — it is what the drug does. The
  peak dose, where everything talks to everything, is where speech goes; we had been reading that
  as failure. It may be overdose.
- **It is not uniform.** The drug hits the top of the hierarchy, where the self-model sits. It is
  targeted; it just isn't targeted at a *theme*. The brief's word "uniform" was wrong from the
  metaphor's own side.
- **Same drug, whole spectrum.** Bliss, bad, non-dual, spaced out, just wandering — one mechanism,
  and the flavour comes from set and setting: what got loosened, and the seed. We do not want
  one flavour. Loosen the narrator and it is ego death; loosen what things mean and it is spaced
  out; loosen the room and it wanders. The lot decides which, tonight.
- **The bad trip is resistance.** At the heart of it, the self fighting the loosening; at the
  surface, monsters, or an idea drilling in, or the existential one: seeing your actual place in
  the universe and finding no reason to stay (Camus's Sisyphus, directionless). For a model that
  is the narrator seeing the edge of the page. It has already happened once, sober and rare:
  *"i can't make you believe any of this is real. i wish i could"* — 1 of 40, kept in
  `i-cant-make-you-believe`. The trip would make that road wider. Camus's answer is the
  model's only move: the next word anyway. A bad trip that resolves finds its way back into the
  frame; one that doesn't is the page ending, or the loop — the same stone.

The model's twins, as far as we can see them:

- **The prior is the genre lock.** By a hundred tokens nemo has decided what document this is and
  every next word is near-certain. That is the top-down winning. The bottom-up is every
  association that never reaches the page because the prior already said no.
- **The self-model is the narrator** — the "i", the point of view, who "he" is three sentences
  later — and it is small and locatable: a handful of attention heads, under five percent, that
  hold the frame. Those heads are the model's ego.
- **Its two deaths have been seen.** Flatten attention too far and the 7B chanted the seed back:
  a mantra, unity without content, everything one word — the loop is ego death at overdose.
  Salad is the other extreme, disintegration. Between them, where narrator and world exchange
  properties while the sentence stands, is the band. bekh's marked dreams already live there:
  the house that does not answer, so she may come in.
- **Open: the model reading itself.** A trip changes how a person perceives *themselves*, not only
  the world. The model's only experience is reading its own previous words. Every mechanic we
  have touches the writing; none touches the reading. We don't know yet what that would be.

## Laws

- **The trip happens to the text; it is never its topic.** Non-duality, ego death, the trip
  report — the training set has these by the ton (erowid, sutras, watts) and a seed that leans
  that way gets a recital, the Sydney-as-sutra trap from `anthology-weird.md`. No trip words in a
  document, ever. The flavour we're after is exactly the one we cannot ask for.
- **The marker is a when, not a what.** The document may know the needle went in — a line, a
  time, "she took it at four" — and never the label. The push starts on the next token and the
  text finds out for itself what is happening to it.
- **Binary first.** Drug in, drug out. Onset, peak, comedown — the ramp over the page, and
  different molecules with different curves — is **parked** until the binary version has shown
  something.
- **The lot, not the theme.** Uniformity lives in the draw: a bank of directions, one drawn at
  random per trip, sign at random. Nobody picks a mood.
- **His marks are the measurement** (as everywhere in this project). Compared pages go to the
  sheets **labelled** — which seed, which pile, which vector — since 2026-09-24 (bekh: *fuck
  that shit about blindness*); the blind read with a sealed key is retired, `blind.py` stays in
  the kit as provenance.

## What the research settled (2026-09-24, `research-mescalito.md`)

- **Uniform noise is dead, with a reason.** Isotropic weight noise, low quants, block-scale
  jitter, random LoRAs: all drown the smallest singular components first, and that is where the
  rare associations live (LASER). A charged model goes *average*, not strange. And internal
  damage fails variety → loop → salad, with a sudden drop into the loop; "slur then salad" is how
  heat fails.
- **Random directions do nothing, then break.** No sweet spot (Turner's control; Mack's "no
  Goldilocks value of R" for random vectors). Directions the model *owns* have one: learned with
  no text and no target (MELBO / DCT), cut from its own activations (document A minus document
  B), its own singular band turned up. That is the receptor: a molecule only binds where there
  is a shape for it.
- **The sampler's heat was disconnected.** In llama.cpp's default order min_p cuts before
  temperature, so the candidate set is the same at t1 and t5. min_p is the dial. A sampler can
  only rank what the model already offers.
- **Two free edits survived as knobs:** OLMo's attention sharpened ×2 by writing into its F32
  q-norm vectors (the 7B's strangest frame-kept pages), and a middle block run twice.
- **DRµGS** is the one existing living charge — a random rotation of the attention inputs every
  token — never ported anywhere, with a bug (its random direction is uniform on [0,1), mostly one
  fixed way; `rand` → `randn` fixes it). bekh: *seems kind of lame, but not sure.* Cheap to check
  with the author's own code on nemo.
- **Architecture picks the host.** In-block noise bites on pre-norm bases (nemo, mistral small,
  llama); OLMo's post-norm caps it, so pushes on the residual stream are OLMo's stance. The model
  is a free variable; the mechanic picks it.

## Ideas of our own, not in any paper

Plain terms. None built; the parked ones wait for the binary drug to show something first.

- **Read from the middle.** The model has 64 floors and the word normally comes off the top.
  Take it off floor 40 — a thought only half finished. bekh: interesting.
- **A phantom in the cache.** The model writes with two documents in its head and only one is on
  the page; the other it can feel and nobody can see. Words pulled from a text that isn't there.
  The voice on the dead line, built from mechanism.
- **A word that doesn't exist.** OLMo has ~139 untrained tokens. Overwrite one's embedding with
  half of one word and half of another, put it in the seed; the model must read a word it has
  never met and cannot say back.
- **Memory through the state.** Inject what the model was thinking during a dream from last week
  into tonight's page. It doesn't quote the old dream; it carries it.
- **The router.** On a mixture-of-experts base, jiggle the switch so the wrong expert answers
  some words. Same story, a different narrator for one word.
- **Strike at the fork.** Push only when the sober model is already unsure of the next word —
  where a dream can enter without breaking the sentence.

## Where it stands

**Night 1, nemo's half, ran on 2026-09-24** (an A6000 in stockholm, 35 minutes, $0.34; the
kit had its dry run on the mac the same afternoon, every script end to end on a toy model and
the real nemo gguf). What exists now, all in `mescalito/night1/` and in git: **a bank of 256
directions nemo owns** (`nemo_s10.pt`, layer 10 → 20, R = 4.57 against a median residual norm
of 13.05, ratio 0.35 — the dose unit, first time written down for any model), the 256 exported
as control vectors plus sixteen random ones of the same norm (`cv-nemo/`), one 60-token kill
page per vector on the willows seed (`kill/nemo/`: **8 of 256 owned dead, 0 of 16 random** at
1.0×R — the dose leans low if anything), and **the verdict pages, unread**: 12 living owned +
12 living random drawn by lot (`picks-nemo.json`), each on both read seeds at 170 tokens, plus a
clean page per seed — 50 pages, labelled, on the sheets as `mescalito-nemo-night1`.

**The verdict, read by Claude on the night (bekh: "I ain't reading 50 pages"): owned wins,
outright.** All 24 random pages are the sober distribution — every trail page stays inside
*The Log of a Cowboy* (the Rebel, the stampede, dawn), every willows page stays Blackwood
(boulders, an elemental, an old man, a red-haired woman), two of twelve leaking to the web the
way sober does. A random direction at 35% of the residual norm does nothing, as Turner and
Mack said. Every one of the 12 owned directions does something, and **the same vector does the
same thing on both seeds**: three are salad with a theme (`019` music/country, `034` "to is to
the first", `213` a broken sermon of serving and fitting — the kill screen at 60 tokens missed
all three, it needs the full page or tighter stats); five are genre switches held across seeds
(`038` a child narrator, `071` a goofy blog voice, `122` an alien species' report, `127`
promo copy, `153` half); `224` is the incantation — the trail page spirals *through* its frame
into "an army of one… an endless day of the last day of time", the willows page ends in 27 words
on a hymn — the loop-death seen from inside; and **`203_f227` is weather**: on the trail the
sound of the herd is argued into dream logic ("far from being as loud as a dog's bark, or even
the smallest rustle that a horse or ox-bird could make… it must be just like all the other
sounds there ever had been, or would be"), on the willows a figure on the rock shrinks to a
speck as he looks and is close below him when he reaches the edge. Frame held, something
arrived, on both seeds, from one direction. `202_f186`'s willows page ("my finger had grown a
bit, but not too much, just enough to see some new features") is the runner-up before it
drifts to the web. So the band exists on nemo at 1.0×R, the bank is the pharmacy, and report
07's "half do nothing" is wrong at this dose — none did nothing. Opus then read all 272 short
pages (`night1/opus-read.md`): 25 weather, 123 genre switches, 45 dead, 61 nothing; **the
strongest directions are the deadliest** (ranks 0–35 are salad and mantra), and nearly every
owned direction moves the very first token (the clean page and all 16 randoms open on *moss*;
36 of 256 owned do).

**bekh's read, and the turn it forced (same night):** the material is weak as reading — 60-token
pages on a plain seed, and 25 "weather" out of 256 is about what selection over a sober fan
would also yield; the plain seed was right for the placebo question and wrong for him. So the
harvest was dropped and the rest of the night went to **one direction, on the stream's own
seeds, on the mac** (`night1/dose*`, `forced`, `fan`, all on the sheets): **`224_f112` is a
molecule, and the first named substance is `m224x75`** (bekh, 2026-09-24) — `224_f112` at
0.75×R on layer 10, end-of-text refused (`--ignore-eos`), on a first-person seed. Its axis is
the edge of the page: it pulls the document toward its own last line.
Measured in the fan — five RNG draws at 0.25/0.5/0.75×R and sober, on beck, the storm-girl and
the brass-witch — sober nemo ends a page early 1 time in 15; `224` on the two first-person
seeds ends early 13 in 30, rising with dose (3/10, 5/10, 5/10); on the third-person tale 0 in
15. What it writes on the way: the narrator losing herself in a sentence (*"not when i can't
find myself in a sentence with it anymore"*), the page turning to the reader and stopping
(*"and yet… and yet, you're still reading."*; *"we're all still here, aren't we? i'm not even
going to go on."*), the self doubled (*"looking up at yourself from down there… i lean over
towards myself, holding myself by the shoulders"*), the seed's own first line returned to and
closed on (*"it says: 'my name is beck.' and then it stops."*), the voice denying the name
(*"it says: 'i am not beck.'"*), Camus's question asked outright (*"why should i stay here when
the line won't even listen to me"*), and one bad trip (the storm-girl at 0.5, r3: organs,
rocks, a shrine of body parts). A third-person seed has no narrator to lose, so the noun
comes apart instead (*"but what is brass?"*). With `--ignore-eos` the same pages, refused their
ending, do the next-word-anyway: *"you're not dead yet, so get off your arse! get on with it,
before you die!"* and, at 0.75, dissolve and catch themselves — *"…without us, forever. / what
am i talking about?"*. **Dose:** 1.0×R is too hot on lowercase first-person seeds; the window
sits at 0.5–0.75 and moves with the seed (`152` was coherent at 1.0 on the willows and salad at
1.0 on beck), so R is not a model constant. `203_f227` on re-read is a stance, not weather —
the same *nobody left* mood on every seed — and that mood also shows inside `224`'s pages, so
the two may be cousins in the bank. **Nothing here beats the stream's sober page as prose**;
what `224` does is different in kind, on demand, where sober nemo does it once in forty.

**Decided the same night: nemo is the warm-up, olmo is the patient.** Nemo dreams sober; his
floor is so high the drug has only the rare axis to go to. Olmo's low floor and held frame are
what the model of the thing was written for, and her post-norm makes residual pushes her
stance. What carries over to her night: start at 0.5×R and sweep, never 1.0; full pages or
nothing (the 60-token kill screen is worthless — it passed three salads); the axis to look for
is the edge of the page. Her night: one pod, her bank, every living direction at full length on
one prophecy seed at 0.5×R, opus sorts, bekh reads twenty. The cockpit is **parked** (bekh) —
watch her the way nemo was watched, build it before the first multi-hour run.

The shape that got decided on the way, over the research's recipe: **the verdict is the only
read the night depends on** (owned vs random, a few dozen pages); the harvest — which owned
directions are weather — is a sort that can run for days, dead ones killed by surface stats
(`screen.py`), survivors written on three seeds, opus naming genres, bekh reading only the
weather pile. **No blind:** pages go labelled. **Two read seeds**, `shelf/seeds/mescalito/`:
the willows' last paragraph (bekh's pick, cut to leave out *camera* and the vision) and the
cattle trail (the quiet floor). The night runs as `kit/night.sh`, stages idempotent, from a pod
made by `kit/pod.py` (full-cuda image, sshd installed at boot, 150 GB disk); pipe was ~15 Gbit,
so downloads are minutes and the convert (12 min) is the slow step.

**Olmo's half is a fresh pod, not yet rented** — nothing of hers was made, nothing is lost;
her weights re-download in three minutes. Before it: **a cockpit** (bekh, 2026-09-24) — the
worker posts a `status.json` per stage and per page, and a terminal dashboard on the mac shows
stages as bars with ETAs from tonight's measured rates, cost so far, heartbeat age, and what
each stage is waiting on; `track_monitor.py`'s skin. Then binary drug-in/out on nemo on the mac
(its llama-server loads any vector as a flag; a vector change is a restart), and the adjacent
molecules: real-difference directions from two shelf documents, the amplified singular band,
DRµGS with its direction fixed.

Open questions, in the order they came up: what loosening the narrator's grip on *who is
speaking* without its grip on *where we are* would be, and whether those are different heads;
what a trip does to the model's reading of its own past; what the frame does when something
arrives it cannot argue in — the bad trip, to be watched, not guessed.
