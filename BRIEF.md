# brief — the dream engine

Read this first, whole. The repo map is `CLAUDE.md`; the instrument's own docs are `eva/CLAUDE.md`
and `eva/berserk/CLAUDE.md` — open those when you need them, not before. This file is the state
of the project and its plan, rewritten in place, never appended; it replaced `HANDOFF.md` and
`docs/agenda.md` on 2026-09-18. Keep it short: every model pays for it on every session.

Two things before anything else. This is a joint project, bekh's and the model's working with
him; your ideas count as much as his and you are expected to have them. And nothing here is a
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
reads, marks, feels the thing or doesn't, charges in. The model is the other hand: picks the
line, builds, reads beside him, argues. He asked for that in so many words — *if you feel you
have a better idea or that something wouldn't work, say it outright* — and the best turns so far
were his knocking down a definition of the model's, and the model catching what a seed had
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
- **Blind reading, two ledgers.** Compared things reach him unmarked and shuffled; the model
  reads the same rooms with the names stripped and keeps its own ledger (`docs/ledgers/`); the
  key opens together. Room by room: a two-sentence brief of the seed, his read, then the model's,
  quotes verbatim. A companion in the room, not a report.
- **The seam is his.** Where a seed is cut decides the first word of every card (*perhaps been*
  → thirty ways to be hurt; *orders to* → thirty orders). Any seed he didn't pick himself goes
  past him and he edits the last sentence before it runs.
- **Opus does everything mechanical** — bulk reading, code, fetching, cutting seeds — with
  `model: 'opus'` on every spawn; fable reads verdicts and judges. A mock before a build. **A
  page change is not done until it has been clicked and dragged**, not just screenshotted.
- **Smallest test first.** A new idea gets the smallest run that can show anything — one seed,
  a handful of cards — and only a promising one gets run at scale. The model's reflex is to
  fire three hundred at once; three hundred cards of a dud is an afternoon of bekh's reading
  gone, and the reading is the scarce thing here.
- **The page is a desktop page; the phone is a smoke test** (root `CLAUDE.md`).
- **The end-of-day brief.** When the day's work is done and the docs are in order, the model
  tells bekh in one short message what the main results were and how we got to each, by subject,
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

1. **The dream stream — live since 2026-09-19** (`eva/stream/CLAUDE.md`, reader at
   `https://eva.x/stream`). bekh's call: stop fucking around, build the stream, whatever comes
   out comes out, and it corrects itself slowly as he reads; he comes back to the rest when the
   interest does. Nemo writes one 350-token page every five minutes, seed and heat (1.8–2.5) by
   lot, nobody picking; the filter below hides web furniture from the phone; a `★` feeds the
   page's tail back into the seed pot (one star weighs what one seed weighs, capped at half) and
   survives as an artifact; rooms and ledger are untracked and disposable. **It must be live,
   never pre-recorded** — a nightly batch was proposed and killed as against the vibe. The mac is
   the smoke test; the writer is one url, and the ladder for it: **(a) the box** — a 16 GB
   5060 Ti on ubuntu at bekh's employer's office, his to use, not as comfortable as our own rig,
   so it is only ever the muscle (llama-server bound to localhost, reached by ssh tunnel, mistral
   small 3.1 24b base at a 4-bit quant; nothing of ours lives there; a runbook he runs himself);
   **(b) by the token** — swept 2026-09-19: Featherless.ai is the only host left serving true
   bases on a raw completion endpoint (llama 3.1 70b base, mistral small 24b base; min_p yes,
   **no logprobs**), but its per-token plan starts at $50 a month; hyperbolic's 405b base is
   decommissioned, openrouter has none; **(c) a rented pod** only for the day we want weights
   (the vector, olmo). If the box writes while the mac sleeps, the worker's natural home is the
   mini — the same shape as the parked loom cutover. Open: pruning (nothing deletes old unmarked
   pages yet, and every `/api/stream` call walks the shelf); the filter reads the page only, so
   a seed that is itself web furniture passes.
2. **The wire** — done (`experiments/wire/`, twenty rooms); the verdict is under "what seems
   true". Not the stream's shape. What it leaves behind: a plain reading surface matters more
   than the loom for finished text, and a wire room is marked as a whole.
3. **Elimination as a column, not a knife.** Finding good cards can be posed as removing lame
   ones: a regexp flags footers, author's notes, web furniture, templates. The flag is a column
   on the card, never a deletion — those cards can still be cool. On the canvas a fan shows the
   unflagged cards, and the flagged ones sit in a collapsed section under it that expands for a
   skim, so bekh still reads everything and the marks stay unbiased. The filter is audited by
   his marks (how many marked cards did it flag?). At training, run with and without flagged
   negatives and keep the better curve — removing easy negatives sharpens the lesson, the near
   misses are what teach taste. Unattended, the machine drops flagged cards before the phone;
   they stay on the shelf.
4. **The scorer on bekh's marks — a side road that lives beside the work.** A vector per card
   (a small embedding model, or nemo's last hidden state — race them), a tiny scorer on top,
   trained on 100/200/300 marks, always tested on rooms it never saw. First curve:
   `docs/scorer/`. Rising → alive; flat at 300 → shelve without grief. Nobody labels for its
   sake: bekh marks what he reads at his own pace, every experiment is its food. Monthly
   retrain, one curve. Scoreboard on held-out rooms: chance 27%; fable blind beside him 62% of
   picks his; an instructed reader (his taste in a portrait plus five rooms of marks) as one
   more contestant, never a gatekeeper — bekh's bet is 80. Friends' marks carry a reader's
   name, blind to each other; pooled marks make an average taste, which is not the point.
5. **The portal-device experiment** — a small introduction, then immediately something weird
   speaking through a device; does the hum room's quality hold? First data point unread:
   `experiments/portal/01-fainter-than-air`, bekh's own four lines, thirty cards nemo and GPT-2.
6. **Fan under the hum room's best cards**, seed plus card as the room: `442ab836` (blood) and
   `4aec75fc` (*the humming is happening to me*) first.
7. **Real channel seeds**: a telegraph operator's diary, a switchboard memoir, a lighthouse log,
   a ham's logbook, a signalman's statement to an inquest — public domain, cut by script with
   provenance (as `shelf/seeds/first-person/cut.py`), short, seam past bekh.
8. **Nemo against GPT-2 XL**, fifteen cards each, blind, on the rooms from here.
9. **Generating levers untried**: a seed with one strange thing already in it (the only fan with
   three keeps in twenty grew under the projector line); heat as a shape — very hot for the
   first tokens, cool after; contrastive decoding; one berserk cycle with `--brakes off`.
10. **bekh's own lyrics and poems as seeds**, and fortune telling (parked below): his words in the
   input, which is where the hand is allowed.

### parked

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
