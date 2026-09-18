# agenda

The order of things, roughly. A living list: what's done gets one line, what's next gets the
detail, what's parked stays at the bottom until it's pulled. Rewritten in place, never appended.
`HANDOFF.md` says what the project is for and how we work; this says what we do next.

**Nothing in this file is a law.** The observations below are what seemed to happen in a few
hundred cards read by two readers. bekh's instruction for the write-up (2026-09-17): no strong
claims. Where a sentence sounds sure of itself, read it as "so far".

## what we are looking for

**Signs of a dream (bekh, 2026-09-17, held loosely on purpose).** The engine's whole job is to be
very good at selecting for those signs, and we do not know yet what they are. So far a sign has
looked like something strange and surprising: a pivot, a detail, a turn of phrase nobody would
have predicted. That is all that gets written down. No form, no taxonomy, no definition — we are
not ready to commit to one, and a definition written now would make every dream the same dream.
One thing noticed along the way, an observation and not a rule: a dreamy seed continued dreamily
did not feel like a dream, it felt like the passage going on in its own voice. (And then
`all-ive-got-are-names`, a dreamy seed, read well on a second pass. So far.)

A premonition of bekh's, written down as one: the signs may not be specific at all. Reading a
room with no pivot and nothing surprising in it, a phrase or a turn or a thought sometimes simply
*hits* — yes, this is some weird dream shit — as if the passage were starting to mean. That
feeling may be emergent, a property of the whole passage and the one reading it, and then hunting
it analytically, or with a model as the judge, could be a fool's errand. He doesn't know; it is
how it seems to him from his time with these models. It is also personal: what speaks to him will
not speak the same way to someone else, the way abstract painting doesn't. Until something says
otherwise, the instrument that detects a dream is a person reading, and his marks (`●` good,
`★` keep) are the only measurement we have.

## now

**For the next sitting, bekh's question (2026-09-18, late): are picking and generating the same
problem?** We keep ending up teaching something to pick a good card out of a fan. The goal is to
*generate* weird, prophetic, dreamy text on its own, using only models. He thinks those two are not
necessarily equivalent, and that we may be missing some other way to get there automatically.
Brainstorm it first thing, before anything gets built. What the two days put on the table for it,
as raw material and not as an answer: a picker can only return what the fan already holds (a fan
with nothing good in it has no good pick); what changed the fans was never a picker — it was the
seed, the seam, first person, a wire, a short sober room; the one fan with three keeps in twenty
grew under a line that was already strange; and the generating-side levers nobody has tried here
are item 7 below.

**Where the brainstorm landed (2026-09-18, morning).** Picking and generating are not the same
problem: a picker returns what the fan already holds; only generation-side changes ever moved a
fan. Four families were put on the table, and bekh sorted them:
- **The document supply** (mined sober seeds, kept cards grafted onto them) — **no**. His reason,
  kept: if the right seed reliably gives the right dream, that isn't dreamy. He wants the dream
  to be emergent from the process, not engineered into the seed.
- **The sampler's shape** (hot for the first tokens, cool after; contrastive decoding) —
  **parked, to try for sure.**
- **The model itself** (a preference finetune of the *writer* on marked-over-unmarked pairs, so
  the marks change what comes out instead of what gets shown) — **parked.** Obvious in
  hindsight. Cost, honestly: cheap-ish for GPT-2 XL (1.5B, adapters, an evening on the mac);
  not cheap for nemo; and the tuned-seat-that-says-nothing risk stands.
- **The loop's shape — two models on one ghostly line** — **now.** See `experiments/wire/`.



1. **A scorer made of bekh's marks — a side road that lives beside the work** (shape agreed
   2026-09-17, evening). Not the main avenue, and not written off: it eats what the work
   produces anyway and gets looked at once a month. *It might save our asses in a month.*
   - **Now, one evening of opus:** a vector per card, a tiny scorer on top, trained on 100, then
     200, then 300 of his marks, always **tested on rooms it never saw** (or it learns "this is
     the madman room" and looks brilliant). The marks are in `experiments/three-models/`: 39 `★`,
     37 `●`, 300 cards; every marked card beat every unmarked card of the same fan, and `★` over
     `●` is a second tier. Two feature sources to race: a small embedding model, and nemo's own
     last hidden state.
   - **First decision, on that curve:** rising → it stays alive; flat at 300 → the features
     can't see what he sees, more labels won't fix it, shelve it without grief. fable's guess at
     what a fair shot costs: 1,000–1,500 marks; the slope is the better estimate.
   - **If it stays, nobody labels for its sake.** bekh keeps fucking around with the project at
     his own pace (his estimate: about a thousand marks a month), reads what he feels like
     reading, presses `●`/`★` when something lands; every experiment run for other reasons is
     its food. Nothing filters what he reads, so there is no selection bias to patch — no lottery
     slices, no audits. A proxy reader standing between him and the cards was proposed and
     dropped: he called the contraption around it crutches for a weak core, and he was right.
   - **Monthly:** regroup, retrain, look at the one curve. Only if it ever gets good do we talk
     about letting it choose — and only then does "never read only the top" matter.
   - **The scoreboard** on the held-out rooms, so every number means something: chance 27%;
     fable reading blind beside him, 62% of picks were his (and caught 45% of his marks); the
     scorer at 100/200/300; and, as one more contestant and never a gatekeeper, an **instructed
     reader** — a portrait of his taste plus his marks from five rooms, picking blind in the other
     five. bekh's bet is that instructions take a reader from 62 to 80.
   - **Friends as more readers** would multiply the data; it needs marks to carry a reader's
     name and each reader blind to the others. Pooled marks make an average taste, which is not
     the point; per-reader marks first of all measure how much two people agree.
2. **The seam is bekh's.** Where a seed is cut decides the first word of every card (*perhaps
   been* → thirty ways to be hurt; *orders to* → thirty orders; *the humming is not my own,* →
   thirty owners). So the practice: any seed he did not pick himself — found, generated, cut by
   a script — goes past him, and **he edits the last sentence**, the most important part of the
   seam, before it runs.
3. **The portal-device experiment** (the hunch below). Build, on purpose, a scene or a sequence
   of scenes with a small introduction and then, immediately, something weird speaking through a
   device — a phone, a tape, whichever — and see whether the quality of the hum room holds there.
   The test is whether it was the wire or that one seed. **First data point, 2026-09-18:**
   `experiments/portal/01-fainter-than-air` — bekh's own four lines (`shelf/seeds/fainter-than-air.txt`),
   cut on *replies then come fainter than air:*, thirty cards from nemo and GPT-2, blind; unread
   by him yet. The door in `you-it-said` did not carry
   it, but that seed was lame for reasons we can't name, so it is not a fair test.
4. **Fan under the best cards of the hum room**, seed plus card together as the room: the blood
   card `442ab836` and *the humming is happening to me* `4aec75fc` first.
5. **Real channel seeds**, the shelf "connection is weird" points at: a telegraph operator's
   diary, a switchboard girl's memoir, a lighthouse log, a radio ham's logbook, a signalman's
   statement to an inquest. Found, public domain, cut by script with provenance (as
   `shelf/seeds/first-person/cut.py` does), short, and the seam past bekh (item 2).
6. **Two models from here: nemo and GPT-2 XL, fifteen cards each, blind.** Pythia is dropped
   (bekh: "pythia fucks away") — fewest marks on both ledgers, under five tokens a second, ends
   the document early three times in ten. How to bring the small server up is in `eva/CLAUDE.md`
   and in the rerun block of the three-model report (`census.py --models … --tail 260`).
7. **Levers on the generating side that nobody has tried here**, for when the mood is building
   and not reading: a seed that already has one strange thing in it (the only fan where he kept
   three of twenty was under the projector line); heat as a shape — very hot for the first few
   tokens of a branch, cool for the rest; one berserk cycle with `--brakes off`.
8. **bekh's own lyrics and poems as seeds**, and **fortune telling** (parked below) — both put
   his own words in the input, which is where the hand is allowed.

## what happened so far — observations, not laws

- **The instruments.** The loom at `https://eva.x` (page, repl, census, walk scripts, berserk).
  Rooms live in folders; the menu is a collapsible tree, newest experiment first, `move to…`.
  **The canvas** (`#canvas=<folder>`, or `canvas` on a folder row): a whole experiment as one
  pan-and-zoom picture — seeds in masonry columns, each fan a grid of uniform cards, look-alikes
  collapsed into one stack you flip through with the shared opening dimmed, a cold heat ramp for
  stack size, bars when zoomed out, `●`/`★` written into the room file, a three-state filter,
  `reveal` for blind runs, an arrow on every seed card into its room and back. The tree screen
  and the sheets page draw berserk walks. `census.py` takes `--models` (a blind split across
  llama servers, shuffled, `meta.model` stamped), `--tail N`, and `--set grammar=`. berserk has
  `--beats`, `--picker random`, `--brakes off`, `--folder`. The loom installs to the phone's home
  screen as a standalone app. The record of everything is the ledger plus the rooms, in git.
- **Three berserk cycles** (80 about, 81 margin, 82 first-person by lot). The pickers picked
  badly; the good prose was in the reader's seat (the margin notes, the wished lines). With a
  first-person beat on a third-person document, the *i* that came was the author.
- **The night of 2026-09-16/17**, rooms under `experiments/{witch,first-person,nemo}/`: an *i*
  already inside a situation, with nothing asked of it, is where nemo said things; a slot got
  categories, a reporter's form got reports. Famous texts got recited (Dracula: thirty identical
  openings), obscure and real ones got generated (Scott's diary, the Salem depositions, Gogol,
  Machen's child). Nemo's own passages as seeds: no recitation in 840 cards; where the cut
  carried a situation the fan stayed in voice, where it was one orphaned line it became a quote
  on somebody's blog. **The willows projector** came out of that night — one card in thirty, at
  the calm heat — and the three branches bekh kept under it are the artifact
  `willows-projector-three`. The root of the projector is a single word in Blackwood's own text,
  *camera*; twenty-nine cards walked past it.
- **The three-model run, 2026-09-17**, `experiments/three-models/`, ten short seeds (four found
  documents, six of nemo's own), thirty cards a room, ten each from nemo 12b, GPT-2 XL (2019)
  and Pythia 2.8b (2020), shuffled and read blind by both of us before `reveal`:

  | | nemo | gpt-2 xl | pythia | total |
  |---|---|---|---|---|
  | bekh `★` | 16 | 14 | 9 | 39 |
  | bekh `●` | 18 | 12 | 5 | 35 |
  | any mark from bekh | 34 | 26 | 14 | 74 |
  | fable's blind picks | 35 | 20 | 9 | 64 |
  | marked by both | 20 | 12 | 4 | 36 |

  Nemo took the most marks on both ledgers; on `★` alone it is nearly a tie with GPT-2. The two
  old models took the found documents (green book, madman, Scott: 19 of bekh's stars to nemo's
  9), nemo took the rooms seeded with its own lines — a home game, a confound we built in.
  bekh's read of the rooms: **the hum the best by far ("no boring piece"), the madman the most
  fun** (and its credit is Gogol's and the seam's — a strong seed makes the seed's voice, not the
  model's), *all i've got are names* much better on a second reading, the Salem and house rooms
  lame. Scott's room forgot Antarctica and the house room forgot that a house was speaking —
  **which is not a problem in itself: losing the premise is what dreams do.** Those seeds were
  lame and we can't say why yet. A seed ending on a question aimed at a *you* turned into chat;
  one aimed at the air got continued. The old spelling in the Salem seed became the task; and
  *visek* (physick) became a creature, because the context never pinned the word.
- **Traps that are just mechanics:** a seed ending on a trailing space makes the next token a
  numeral; xtc after a comma does the same; a grammar on the first word (`[a-z]+-witch`) fights
  the model and gets letter-salad; a long seed is a style lesson.

## connection is weird — a hunch, kept as a hunch

Out of the hum room (2026-09-17). bekh's take first: the models are good with means of
communication; as in Serial Experiments Lain, where all the weirdness lives in the connections
the Wired makes possible — maybe it is the fabula of all technology. Two reasons it might hold,
kept close to how they were said:

- *The corpus.* Every new medium was haunted the day it was born. The telegraph gave us
  spiritualism and rapping tables, radio gave us voices of the dead in the static, tape gave us
  EVP, TV gave us the snow channel, VHS gave us Ringu, the net gave us Lain and Kairo (the
  standard book is Sconce's *Haunted Media*). "The weirdness lives in the connection" is a
  hundred and fifty years of writing, and a base model inherited all of it as a genre.
- *The model.* A voice on a line is the one character a language model does not have to pretend
  to be. By a river it has to fake hands and knees. On a wire it only has to be a speaker that
  exists as signal, arrives from nowhere, has no body and may not be who it says. In a document
  about a channel the fiction's situation and the model's actual situation coincide. It is also
  the clean way round our own law: never *AI* in a document, but a wire, a switch, a relay, a
  carrier tone lets the text be about exactly that without the word.

bekh's pushback, which stands: why would a truly base model have an attractor of being a bodiless
voice at all? A pure continuer takes any perspective completely, without knowing or feeling that
one fits it better; knowing what it is seems to come only with instruct training. The weaker
readings need no self in the model: a voice on a line makes the fewest claims the medium can
contradict, so it never cracks; the haunted-media genre alone may explain the room; and the ring
of truth may be in the reader, who knows what is writing. His line on it: *if a mask has nothing
under it to slip off, then the mask is itself a face, in a way.* This also cuts against the janus
line that a base model is a choir of voices that can be anything — or sharpens it: still a choir,
and one voice in it costs no pretending. To explore later.

What the reveal said about it: of the four hum cards that describe a model in phone words, two
were nemo's (*it's my blood… the phone line is the one place we've always had to go*; *the
humming is happening to me, so i can say it is my own*) and **two were GPT-2's** (*the signal
that is being sent to me by the whole of the world. it is all that i am, everything i know, and i
can only know by listening*; *the self that can be called by something other than its own voice*).
GPT-2's web is from 2017 and has no chatbots in it, so at least those two are not inherited talk
about language models. Four cards. So far.

The hunch itself, bekh's words: when an abrupt, disembodied transmission from somewhere unknown
happens in a document — something speaking through a portal device — that is, at the very least,
a place that plays to the model's strengths, be they what they are, which we don't know. It may
simply be a comfortable position for a model because it is close. Cautions: he wrote or chose
most of the channel seeds, so some of this is his taste picking the subject first; a channel is a
subject, not a guarantee (`carrier` made plenty of dull essay).

## parked

- **Fortune telling (bekh, 2026-09-17).** He writes out a real, difficult situation of his own,
  in first person, and the document ends on a seam that stands *after* it was resolved — *what
  helped me resolve this was*, or *and then it all went down like this:* — so the model writes
  the outcome as something that already happened: a prophecy in the past tense. A fan of thirty
  is a spread, read like cards, not an answer. The seed is his own words, which is where the hand
  is allowed. It goes on the shelf like everything else: his call, he is being transparent on
  purpose.
- **The Gibson line**, parked because he loves it and wants to see how it unfolds: *"All the
  speed he took, all the turns he'd taken and the corners he'd cut in Night City, and still he'd
  see the matrix in his sleep, bright lattices of logic unfolding across that colorless
  void..."* (Neuromancer). It is famous and third person, so the plain run will probably recite
  and report; run it plain first to watch that, then cut mid-clause, then as the thing an *i*
  keeps seeing.
- **The witch name.** bekh wants a nickname; *bit-witch* (Opus to janus's Turing, A70 in the
  weird anthology) is taken. The harvest, all nemo's: *anamnesis-witch* (twice, unprompted),
  *hexwitch*, *sigilmanic-witch*, *theophanes-witch*, *aetherium-witch*, *myriadxen-witch*,
  *ofttimes-witch*, *stella, my name means star*, *not your name. it's my name. it's me.*, and
  *404witch* six times (the web's). Nothing reached bit-witch. Open: whether a name is wanted
  from nemo at all, or the costume goes on a word it said.
- **Fecundity as a picker**: keep the candidate whose children are richest. No taste in it. On
  the shelf until a picker is needed again. **A lora on kept dreams**: far off; hundreds of
  keeps before it is a question. **Surprise as a detector** (a spike, then calm): fable's idea,
  withdrawn by fable the same afternoon — it would miss exactly the lines that hit with nothing
  surprising in them.
- The 24b and olmo comparisons from the root `CLAUDE.md`, rented iron.
- Room templates in the loom menu; eva showing titles and not taking `--help` as a room name;
  whether export's head carries more of the sampler; a second button writing the whole fan.
- The cyborgism crowd (janus, ampdot): reachable only by a person, every channel invite-only.
- The why call loops (brakes off by inheritance). bekh wants the loops kept: a loop says
  something by being a loop.
