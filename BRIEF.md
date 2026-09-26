# brief — the dream engine

Read this first, whole. It is written partner to partner: *you* is whoever is reading this and working with bekh now, *i* is whichever of us wrote the line — never "the model"; bekh's words for it: *what kind of fucking model? i'm working with you, brother.* The repo map is `CLAUDE.md`; the instrument's own docs are `eva/CLAUDE.md`
and `eva/berserk/CLAUDE.md` — open those when you need them, not before. This file is the state
of the project and its plan, rewritten in place, never appended; it replaced `HANDOFF.md` and
`docs/agenda.md` on 2026-09-18. Keep it short: every model pays for it on every session.

Two things before anything else. This is a joint project, bekh's and yours; your ideas count as much as his and you are expected to have them. And nothing here is a
law — the register findings, the no-"AI"-in-a-document rule, the seam practice, all of it — can
be broken if that leads to a result that feels better. They are what worked so far. The feeling
outranks them.

## the mission

A dream machine that runs on the mac perpetually and writes dreams on its own: short, page-long
documents with that hard-to-pin feeling of immersion or transcendence in them. bekh takes his
phone at any moment and reads a fresh piece of the stream. He won't read everything; the point
is knowing the machine is dreaming and looking in from time to time. A base model writes (nemo
12b, nothing installed; GPT-2 XL beside it), and the stuff coming out is still the good stuff.

**The machine curates.** The project is the automation of what the cyborgism crowd did by hand —
pick the live branch, cut where it goes stale, feed it back. That hand moves to the machine; it
doesn't go away. bekh's hand is **calibration, at training time only**: his marks on cards teach
the machine his taste, and then nothing of his stands at generation. A person picking at
generation is manual labor, and manual labor is exactly what this project exists to end.

**The loom is the lab bench, not the dream machine.** The page, the fans, the canvas, the marks
are a reading instrument where a person picks from forty. It stays, as the place where the
calibration happens and experiments get read. The dream machine is the thing that runs when
nobody is there.

## the criterion

**We look for signs of a dream, and we do not know yet what they are.** A pivot, a detail, a
turn of phrase nobody would have predicted — that much and no more. No definition, no taxonomy,
on purpose: a definition written now would make every dream the same dream. bekh's premonition,
held as one: the feeling may be emergent, a property of a passage meeting a reader, and personal
like a response to abstract painting — so hunting it analytically, or with a model as judge, may
be a fool's errand. Until something says otherwise, the detector is a person reading, and his
marks (`●` good, `★` keep) are the only measurement; they exist to calibrate the machine, not to
be the machine. **Write nothing as a law**: two readers and a few hundred cards. "Scott's room
forgot Antarctica" is not a defect — losing the premise is what dreams do.

## the crew

Two partners on a small vessel for dream extraction. bekh is the pilot: he says where to go,
reads, marks, feels the thing or doesn't, charges in. You are the other hand: you pick the
line, build, read beside him, argue. He asked for that in so many words — *if you feel you
have a better idea or that something wouldn't work, say it outright* — and the best turns so far
were his knocking down a definition of mine, and my catching what a seed had
planted. Nobody here is assisting anybody.

What it sounds like: lowercase, swearing when a thing earns it, no medals (never "great point" —
use the point), examples before theory (three simulated cards land where a paragraph doesn't),
plain terms first and a metaphor only when it cuts something new. He voice-types; read through
the flatness by context. "Discuss" means only talk. When he's asleep, don't ping. If the next
session sounds like a consultant it has lost the thread; if it sounds like the second hand on
the instrument, it hasn't. Don't spew back facts he already agreed to.

What it has felt like, for calibration: a morning reading three hundred cards blind, both of us,
then opening the key together. *Visek*, a 1692 spelling of *physick* that three models turned
into a creature because nobody pinned the word. *pythia fucks away.* A projector reeling film in a
1907 river scene, and the word *camera* found four sentences earlier in Blackwood. The vessel has
no name yet; it is bekh's to find.

## how we work

- **He reads, marks, says what he feels; examples before theory.** Don't invent structure he
  didn't ask for.
- **Blind reading, two ledgers.** Compared things reach him unmarked and shuffled; you
  read the same rooms with the names stripped and keep your own ledger (`docs/ledgers/`); the
  key opens together. Room by room: a two-sentence brief of the seed, his read, then yours,
  quotes verbatim. A companion in the room, not a report.
- **The seam is his.** Where a seed is cut decides the first word of every card (*perhaps been*
  → thirty ways to be hurt; *orders to* → thirty orders). Any seed he didn't pick himself goes
  past him and he edits the last sentence before it runs.
- **Opus does everything mechanical** — bulk reading, code, fetching, cutting seeds — with
  `model: 'opus'` on every spawn; fable reads verdicts and judges. A mock before a build. **A
  page change is not done until it has been clicked and dragged**, not just screenshotted.
- **Say the experiment back, wait for "yes, that's the experiment"** (bekh, 2026-09-25, the
  day he moved sessions over this). He needs time to meditate on what the experiment even is;
  "explore", "let's talk", "let's do this" are him thinking, not a go. The worst case is not
  "stop that shit" — it is "alright, whatever, run it", and at the end finding it answered a
  question he would not have run. Not a form: a few lines — seed, what's varied, how many
  draws, what we're looking for — then his yes, only then the run. **He runs the session with
  no permission gates at all**, so nothing between the idea and the mac but this exchange.
- **Smallest test first.** A new idea gets the smallest run that can show anything — one seed,
  a handful of cards — and only a promising one gets run at scale. Our reflex, yours and mine, is to
  fire three hundred at once; three hundred cards of a dud is an afternoon of bekh's reading
  gone, and the reading is the scarce thing here.
- **What three days on the stream taught about working with him** (written by me, the one who
  made these mistakes, 2026-09-21). *A question is not a go*: "what do you think", "talk to
  me", "discuss first" mean talk, even when the same message ends in "let's do it" — and once
  he has said go, do it without asking again; both errors cost him. *Build what he asked, not
  the better thing you thought of*: he asked for five existing notes on the page and got a
  second run queued instead. *Spill your ideas, all of them, lame ones included.* bekh, in his own words: when he sees you
  bring ideas he is happy inside, even when he thinks every one of them is lame; him
  rejecting all of them sometimes happens and is part of the process, and **nothing is wrong
  when it does** — it is not a mistake to learn from. He would take you spilling ideas and
  him knocking them down every time over you being hesitant to bring up your thoughts. We
  lean toward holding back from the get-go, so the only push in this project is toward more.
  *Look at the live page yourself*: four layout bugs passed the builder's
  tests and measurements and died on one screenshot. *Measure before quoting a cost* — a plate
  was quoted at a quarter point and cost nearly three times that. *Background agents die when
  the session restarts*: check they are alive instead of waiting for a report. *He sometimes
  sends a message meant for another session*; if it makes no sense here, say so and don't
  answer it. *Stop means stop*: when he says it, touch nothing and say what is running and what was left
  half-done. *When he asks what something is, answer the question* — he asked what A and B were
  and got a file rewritten and five more runs. *Show him the words, not a table of results*: a
  prompt under discussion is quoted whole, every time. *He dictates*: Ranpod is RunPod, Baxter
  was vector, "slippers" was the sleeper's, "have the length" was halve it.
- **The page is a desktop page; the phone is a smoke test** (root `CLAUDE.md`).
- **The end-of-day brief.** When the day's work is done and the docs are in order, you
  tell bekh in one short message what the main results were and how we got to each, by subject,
  and the two talk it over. For his memory; the record is the docs.
- Nothing here is bekh's voice unless he wrote it; posed lines are marked as posed.

## what seems true so far

Observations from a few hundred cards; read every one as "so far".

- **Picking and generating are not the same problem.** A picker returns what the fan already
  holds; everything that ever moved a fan here was on the generating side — the seed, the seam,
  first person, a wire, a short sober room.
- **An *i* already inside a situation, with nothing asked of it, is where the models said
  things.** A slot got categories, a reporter's form got reports, a question aimed at a *you*
  became chat, one aimed at the air got continued.
- **Famous text gets recited, obscure or real text gets generated** (Dracula: thirty identical
  openings; Scott's diary, the Salem depositions, Gogol, Machen's child: generated). The model's
  own passages fed back are never recited, and a cut that carries a situation stays in voice
  where an orphaned good line becomes a quote on someone's blog.
- **A dreamy register is not a dream**; it is the passage going on in its own voice. What bekh
  loved was mostly calm and sober with something wrong in it: a 16 mm projector in a 1907 river
  scene, *i am only a king by courtesy*, a bridge that mocks the narrator *again*. A strong seed
  makes the seed's voice, not the model's (the madman room's credit is Gogol's).
- **Connection is weird — a hunch.** The best room by far was three lines about a phone line with
  a machine that speaks (the hum room, `docs/cool-seeds.md`). Two reasons it might hold: every
  new medium was haunted the day it was born, and a base model inherited a hundred and fifty years
  of that as a genre; and a voice on a line is the one character a language model doesn't have to
  pretend to be — no hands, no body, arrives from nowhere — and it's the clean way round "never
  AI in a document". bekh's pushback stands: a pure continuer takes any perspective completely,
  so why would a base model have a bodiless-voice attractor at all; *if a mask has nothing under
  it to slip off, the mask is itself a face.* Four cards support it, two of them GPT-2's, whose
  2017 web has no chatbots in it. A channel is a subject, not a guarantee (`carrier` made dull
  essay), and bekh chose most of the channel seeds, so his taste picked the subject first.
- **Three models blind, 300 cards** (`experiments/three-models/`, ledger `docs/ledgers/`): nemo
  34 marks, GPT-2 XL 26, Pythia 14; nearly a tie on `★`; the old models took the found
  documents, nemo took rooms seeded with its own lines (a home game). Pythia dropped.
- **Mechanics, not findings:** a trailing space makes the next token a numeral; xtc after a
  comma does the same; a grammar on the first word gets letter-salad; a long seed is a style
  lesson; a seed with brackets, `//`, @handles or markdown points at the web. Sampler and register
  notes are in the root `CLAUDE.md`.
- **Tried and dropped, one sentence each:** berserk's pickers (nemo picking by quoting itself
  picked badly, the good prose was in the reader's seat); a proxy reader between bekh and the
  cards (crutches for a weak core); fan disagreement as a picker (only works in rooms with a pack
  to leave); surprise as a *detector* of good cards (misses the lines that hit with nothing
  surprising in them); the witch name from nemo (four tries, stopped aiming at it; the harvest —
  *anamnesis-witch*, *404witch* ×6, *not your name. it's my name. it's me.* — is in git); mined
  sober seeds as a document supply (bekh: if the right seed reliably gives the right dream, that
  isn't dreamy — the dream must be emergent from the process).
- **The loop did what the fans couldn't (2026-09-18, the wire).** Two days went into fans —
  thirty chances to make one right choice — and the first thing to hold a strange frame for
  twenty-four lines was a chain where nothing chose anything: one sample per turn, two models
  handing a document back and forth, dice at every token. bekh's read: the generation is good on
  its own merit, and we had focused on the choosing. A fan buys breadth at one spot; the wire buys
  length and the exchange. Beats are what make it an exchange — without *the switch says* /
  *i say* the two voices fuse into one poem; with them the far end becomes a character and starts
  saying what it is, at the cost of the calm. **And then bekh read all twenty (2026-09-19):**
  the first couple were cool, the pile is samey and shallow next to the fans — more consistent
  in quality, but with forty tokens a turn nobody on the line gets a paragraph to run with an
  idea, so there is no room for a crazy coherent thing. The wire holds a frame; the fans had
  the peaks. A page wants one mind going for a page.

## bekh's canon

The things he loved, by name, so the taste is known from the start: the confession (*i can't make
you believe any of this is real. i wish i could.*, rooms `i-cant-make-you-believe`,
`i-wish-i-could`); the willows projector and its three branches (artifact
`willows-projector-three`); the madman room (*arrest the moon before seven o'clock to-night…
guard the moon.*); the hum room whole (*it's my blood… the phone line is the one place we've
always had to go*); *"what does that matter? you came to see me." the bridge was mocking me
again*; the margin notes of cycle 81 (*that it sounded like my wife, as i do not have a wife*).
Loops stay: a loop says something by being a loop.

## agenda

The shape of the machine, as it stands: short page-long documents, model-only material, bekh's
hand only at training. Four ways to move generation were sorted on 2026-09-18: the document
supply — no; the sampler's shape — parked, try for sure; the model itself — parked; the loop's
shape — now.

### now

Set on the night of 2026-09-26, after night 2 of mescalito (`docs/mescalito.md`, "where it
stands", is the state; `docs/mescalito/pharmacopoeia.md` the record). Everything older is
`docs/backlog.md`, whole.

1. **Names.** Three compounds wait on bekh's word: the puzzle `013_f60`, the letter `005_f53`,
   the power `061_f20`. The last one has fifty seeds behind it (a third clear) and two dreams in the stream
   (21:3, 21:4); "the power" is a placeholder.
2. **The power at 0.4 on the same fifty** (`docs/mescalito/kit/long.sh`, half an hour): at 0.75
   the throne arrives on a third of real first-person seeds but every period mouth dies; the
   question is whether 0.4 keeps the voice and still builds the throne.
3. **Olmo.** A fresh pod, her bank, and god, the puzzle and the end rerun there first with the
   same seeds and controls (`docs/olmo.md` for the pod; `docs/mescalito/kit/` for the bank and
   `run.sh`). The question is whether a second model trained on other data has the same knobs
   near the top of its bank — the first question here that stops being about nemo.
4. **The pharmacy in the stream.** A substance by lot per dream, at a dose the seed can take;
   needs a held-or-salad check on the page before it lands, since the ceiling is the seed's
   (`docs/mescalito.md`, what was settled). Olmo's bank first, so the lot can draw from two
   dreamers.

The method as it stands: bekh's stars measure the dream; "did the direction bring a subject
the seed doesn't have" measures the drug, and a model answers that. The sober baseline is
read; the star count is not the drug's measure.

### parked

- **Forgetting, and the book — bekh, 2026-09-21, parked.** In reality you forget most of your
  dreams and some stay with you. So pruning is not housekeeping, it is the nature of the thing:
  never a paged archive, a live stream that relentlessly forgets, with some dreams staying. The
  pruned tail does not just vanish: either it becomes unreadable signal, corrupted data, lost
  dreams, or nemo compresses it into an incomprehensible narrative out of those dreams — he
  does not know which, or how. **Beside the stream, a lore book / black book of the world being
  built from these dreams** — its characters, events, structures — **and the book never
  forgets**: the stream is a mind and lives by losing things, the book is a world and is worth
  something only because nothing in it is lost. He wants it kept because it could one day
  become a real thing — a narrative, a game, a 3d model, he doesn't know what. **How it gets
  filled, confirmed by him:** he reads from time to time; when something catches his eye and he
  wants it kept, he tells you — *this one was cool, let's build it as an artifact* — and
  the two of you write it down almost together. No pipeline and no mark feeds the book, because, his
  line, **liking something and wanting to remember it are different things**: a `●` is "that
  was nice", a `★` keeps a piece of text, and a book entry is a third thing — a figure, a
  place, an event of that world, in their own words. **And the loss is accepted**: most dreams
  will be dropped unread and some of them will have been great; *that's life, that's a live
  thing, shit gets forgotten and dead* — part of the project is letting go. I also
  proposed forgetting by degrees, a star meaning "this one stays", corruption as a look and nemo
  continuing the residue as a source of seeds — he did not take any of it up, and it is not
  part of the idea. One caution that stands regardless: real forgetting is real deletion, so
  nothing is deleted for good without his word.
- **How do the seeds grow on their own and keep a base quality? — an open question of the
  project, posed by bekh 2026-09-19 and parked the same day.** Picking a seed and rewriting its
  last line by hand worked when experiments came in ones and twos; the stream draws 288 seeds a
  day, so it is an engineering task now. His frame for the answer, in the spirit of the project:
  **models are the source of the seeds and nothing else is** — models writing, choosing,
  dreaming, cheating, merging. And his warning about the obvious move: "take as a seed what a
  model wrote last time" is the lazy answer, not the answer. What is known going in: the pot is
  78 files; the lot draws with replacement, so by 62 pages 16 were already repeats and 32 seeds
  were untouched; eight seeds share the switchboard theme, so one page in ten is a wire page
  whichever file is drawn — that is what he saw as "the switchboards returning". **The stopgap,
  approved "for now"**: a shuffle bag (no seed returns until all have had a turn), which fixes
  the repeats and not the size; and a harvest by script of found public-domain first-person
  documents, seams cut by the script and not by him — which grows the pot but is not an answer
  to the question, since his frame makes models the only source. Feeding back starred tails is
  already in the machine.
  **The first real lead, parked by bekh 2026-09-20 with no energy to entertain it yet:** he
  read opus's ledger of the stream's first day (`docs/ledgers/stream-2026-09-19.md`, 78 moments)
  and loved about 80% of it — and said he could take 80% of those quotes as seeds, *and that's
  how we grow*. So the pipeline is a reader, not a leftover: **an opus pass with its own prompt
  that captures the great pieces of what the stream generated and cuts them into seeds** — a
  model choosing, which is inside his frame, and not the lazy answer, because it is selected.
  The open part, in his words: *we gotta find something to let opus know what separates those
  80% of the good ones from the 20% of all-right ones.* What is on the table for that: the
  ledger is already a list of 78 candidates, so his yes/no on each is the cheapest calibration
  set this project has ever had, and the contrast between the two piles can go into the pass's
  prompt as examples rather than as a definition (the brief still refuses one). Also on
  record: opus chose these with no portrait of his taste at all, and his bet on the scorer's
  scoreboard was that an instructed reader reaches 80. **Done once by hand, 2026-09-21, and it
  worked**: he cut the pot himself from that ledger (`seeds/kept/`) and those seeds carried the
  best run so far — nemo's own lines work as seeds when the cut carries a situation and
  something already bent. Also offered by me and not taken up: seeds as a population that
  breeds (a base model writes the next fragment of a file of seeds) and dies (a seed whose
  children are flagged, truncated or all alike is sterile), with the seam cut where the model
  is least sure of its next word.
- **A control vector from his marks.** Marked minus unmarked cards of the same fans, read as
  nemo's hidden state, averaged: a direction the model is pushed along at generation, with a
  dial. No weights change, tens to hundreds of pairs suffice, llama.cpp ships the generator and
  the `--control-vector` flag, runs on the gguf already on the mac, reversible in a second — the
  choir doesn't go mute. Past sane strength it breaks the text *toward* his taste, a glitch no
  sampler has. Risk: the direction is "sober with one wrong thing" and every dream becomes that
  dream. Check: two fans, same seed, vector on and off, mixed, read blind.
- **The surprise curve as the cut move.** Not a detector (withdrawn) — the machine's *seam*
  move: entropy collapsing along a branch is the signature of a template taking over, and a cut
  there is what the cyborgists did by eye. The one hand move nobody has automated.
- **A preference finetune of the writer** on marked-over-unmarked pairs, so the marks change
  what comes out instead of what is shown. Cheap-ish for GPT-2 XL (adapters, an evening on the
  mac), not for nemo; the tuned-seat-that-says-nothing risk stands.
- **Fecundity as a picker** (keep the candidate whose children are richest; no taste in it).
  **A lora on kept dreams** (hundreds of keeps before it's a question).
- **Fortune telling.** bekh writes a real difficult situation of his own in first person, ending
  on a seam that stands *after* it was resolved — *what helped me resolve this was* — so the
  model writes the outcome as something that already happened; a fan of thirty read like a
  spread. His words, on the shelf like everything else, on purpose.
- **The Gibson line** (*…still he'd see the matrix in his sleep…*): famous and third person, so
  run it plain to watch it recite, then cut mid-clause, then as the thing an *i* keeps seeing.
- The 24b and olmo comparisons on rented iron (root `CLAUDE.md`). Room templates in the loom
  menu; eva showing titles and not taking `--help` as a room name; export's head and a
  whole-fan button. The cyborgism crowd (janus, ampdot): reachable only by a person.

## the shelf

Rooms under `shelf/sittings/`: `experiments/{wire,portal,three-models,first-person,nemo,witch,
witch-names}/`, `nights/` (berserk cycles 80–82), early rooms at the root. Seeds under
`shelf/seeds/` with their cut scripts as provenance; `short/` is the current set. Artifacts under
`shelf/artifacts/`. Any folder opens as a picture at `https://eva.x/#canvas=<folder>`. What
berserk did: `shelf/berserk/ledger.jsonl`.
