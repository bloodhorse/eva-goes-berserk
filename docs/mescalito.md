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
  sheets unmarked, the key held until he has read.

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

Nothing has been synthesised yet. The first molecule is a MELBO/DCT bank on Mistral Nemo 12B
base (one A40, minutes of compute after the download), read blind against random directions of
the same size, then bound binary — in for the page, out — through two llama-servers; the script
that learns the bank (`mescalito/kit/melbo_bank.py`) has never run, so the first evening opens
with a debugging hour. The adjacent molecules follow: real-difference directions from two shelf
documents, the amplified singular band, DRµGS with its direction fixed. The recipes, dials and
what page to read for the verdict are in `research-mescalito.md`, part 3.

Open questions, in the order they came up: what loosening the narrator's grip on *who is
speaking* without its grip on *where we are* would be, and whether those are different heads;
what a trip does to the model's reading of its own past; what the frame does when something
arrives it cannot argue in — the bad trip, to be watched, not guessed.
