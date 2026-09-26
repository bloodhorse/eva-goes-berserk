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

**Two nights so far, both on nemo, and the pharmacopoeia is the record:
`mescalito/pharmacopoeia.md`** — one entry per direction that has had more than one page,
rewritten in place; start there for what any direction does. This section is the shape of
things, not the findings.

**What exists.** A bank of 256 directions nemo owns (`night1/nemo_s10.pt`, layer 10 → 20,
R = 4.57 against a median residual norm of 13.05), exported as control vectors with sixteen
random controls (`night1/cv-nemo/`); a pod recipe that worked (`kit/pod.py`, `kit/night.sh`:
an A6000, 35 minutes, $0.34); on the mac one script, `kit/run.sh` — out-dir, seed, vector or
sober, dose, rng list — writing a page in ~15–27 s and skipping what exists (the night-1 and
night-2 scripts it replaced are `attic/kit-night2/`, provenance for those folders); `kit/land.py`,
which lands a dosed page in the stream as a dream, any seed, `LAND_UNFLAG=1` when the reader
would skip it for a web tell, and runs the reader, the sleeper, the painter through its backlog
and the mirror itself; `land_batch.py` for a list; `kit/sheet_build.py`, a reading page with stars for the mini.
Pages: `night1/` (the bank, the lottery, the strong end, the ladder on the 22) and `night2/`
(god, scott, the baseline, bloodbath, 061 across the pot), all in git; a night is one folder.
Reads are working notes and live in `attic/mescalito-reads/`.

**What was settled.** *Owned beats random, outright*: 24 random pages at the same norm are the
sober distribution, 24 owned pages all move. *A substance is what holds across draws and
seeds*: one page is a mood. *The seed decides what there is to lose*: a lowercase *i* in a
situation takes the drug; a famous memoir in *we*, a third-person tale and an aphorism don't;
a seed with a *you*, a switch or a phone is a road sign to the web and holds nothing (the hum).
*Rank is gain*: the strong end works at 0.25–0.4, mid-bank at 0.5–0.75, and 1.0 is too hot.
*The dose a direction needs is also the seed's*: god at a quarter where the page has a slot
(the asses), 0.4 where it hasn't (Scott). *Frames have a ceiling by kind*: a narrative frame
(a capital-I diary with dates) survives to ~0.5, an orthographic one (Salem's sworn spelling)
to ~0.4, gone at 0.75. *The subject is the direction, the dose sets how much sentence survives
around it* (the ladder; Scott's feet become feet of clay). *A direction is a pointer into the
inherited web, and the pointer is the model's own* — found with no text; what it points at is
a genre (apologetics, the puzzle book, the deathbed), which is why the root law still reads
each page genre first.

**The method flip (2026-09-26).** bekh's stars measure the dream; they were never going to
measure a drug. Two readers built selector instructions from his 40 stars on the ladder
sheet — what he stars is mostly a veto (someone else talking by the end, a settled close, a
dream told as a dream), and the one positive that carries is *her body hurt, told flat*, with
the impossible and a second voice next; beauty, sadness and oddity are at base rate. On a
sober baseline of forty storm-girl pages both instructions star at the drugged rate or above
(21/14/20/17 of 40 against 37 of 98 held drugged) — sober nemo has none of the drug's failure
modes and the seed hands out the positives for free. So the pharmacy's measurement is *did
the direction bring a subject the seed doesn't have*, a question a model can answer on a
fill-in-the-blank; the stars stay for the dream. The reads are in the attic; the numbers are
here.

**Compounds** — a shape that held across seeds with a sober control. Night 1's three, named
by bekh: **ender** `M-224-75` (the ending as subject; on Scott 6/6), **kin** `125KIN-75` (the
family; on Scott soft, 2/6, home and the tender companion), **voices** `169x75v` (the head
populated; not on Scott — a capital-I party of men has nothing to double). Night 2's, unnamed
but for god: **god** `M-012-25` `012_f232` (free will and the fall — angels, Satan, the
rebellion; 9/9 on a slot with no god in it, sober 0/3, control clean; 3/3 on Scott at 0.4),
**the puzzle** `013_f60` (counting as a way of being lost, ending in a logic puzzle; 3/3 on
Scott at 0.4), **the letter** `005_f53` (an addressee; 4/6 on Scott, the diary signs off
*Yours truly*), **the power** `061_f20` (a presence above and the narrator small under it —
a throne built where the seed has nobody, a crowning where it has someone uncanny, nothing
where it has a plain husband; **reach on fifty seeds at 0.75: a third clear, a quarter soft**, and the throne is always the seed's own god; two pages in the stream as 21:3 and 21:4). Pinned,
unfanned from night 1: `015` the sister, `064`, `110`, `162`, `112`, `147`, `153` the data
direction (read, never seeded), `036`, `023`. **Bloodbath road 1 is dead**: the four dark
directions on two seeds, blood 1 of 24 and that one a fitness blog — the blood on the storm
girl was hers; road 2 (a difference vector, murderer minus calm) is the live one and a build.

**Next**, in order: the power at 0.4 on the same fifty seeds (`kit/long.sh`) — whether a period mouth and the throne can coexist on real text; a name from bekh for the puzzle, the letter and the power; **olmo** — a
fresh pod, her bank, and god, the puzzle and the end rerun there first (does a second model
trained on other data have the same knobs near the top of its bank — the question that stops
being about nemo); then the pharmacy plumbing for the stream (a substance by lot, at a dose
the seed can take, which now needs a held-or-salad check); then the letter re-run on ten sober
Scott draws before it is named (real diaries end *Yours truly* on their own).

Open questions, in the order they came up: what loosening the narrator's grip on *who is
speaking* without its grip on *where we are* would be, and whether those are different heads;
what a trip does to the model's reading of its own past; what the frame does when something
arrives it cannot argue in — the bad trip, to be watched, not guessed.
