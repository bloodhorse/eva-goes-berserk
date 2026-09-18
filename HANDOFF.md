# handoff — the dream engine

For whoever picks this up next. This is the shape of the thing and what it's for, not a spec.
The map of the repo is `CLAUDE.md`; the ordered plan is `docs/agenda.md`; the instrument's own
docs are `eva/CLAUDE.md` and `eva/berserk/CLAUDE.md`. Read those when you need them, not before.
State as of 2026-09-17, rewritten in place at the end of a two-day session.

**Two things before anything else.** This is a joint project, bekh's and the model's working
with him; your ideas are as important as his, and you are expected to have them. And every
law, principle and finding cited in this file or anywhere in the repo — the register
findings, the no-"AI"-in-a-document rule, comparison-is-the-judgment, recur-don't-continue,
all of it — can be broken, forgone or subverted if that leads to a result that feels better.
They are what worked so far, not what must be obeyed. The feeling is the only thing that
outranks them.

## The objective

Build an engine that shits out weird, prophetic, cool dreams on its own, all the time — so that
bekh can open a page at any moment and find something strange in it. A base model writes them
(nemo 12b on the mac, nothing installed; GPT-2 XL beside it since 2026-09-17). As little
curation as possible. Nobody knows if a 12b can get to eight in ten worth reading. It's the goal
anyway.

## The criterion, as it stands now

It moved twice in two days, and the next session should start from where it landed, not from
where it began. First: *a model picks the dream* (berserk's pickers). Then: *curation can't be
removed, only moved — raise the base rate*. Now, in bekh's words: **we look for signs of a
dream, and the engine's job is to be very good at selecting for those signs, and we do not know
yet what they are.** A pivot, a detail, a turn of phrase nobody would have predicted — that much
and no more. No definition, no taxonomy; he asked for that explicitly, because a definition
written now would make every dream the same dream. His premonition goes further: the feeling may
be emergent, a property of a passage meeting a reader, and personal, like a response to abstract
painting — so hunting it analytically, or with a model as the judge, may be a fool's errand.

So **the instrument that detects a dream is a person reading**, and bekh's marks on cards — `●`
good, `★` keep — are the only measurement there is. It is still the feeling from the first
version of this file: does it read like the model dreamed it, and is it good.

**Write nothing as a law.** bekh's instruction for every write-up: no strong claims. Two readers
and a few hundred cards. "Scott's room forgot Antarctica" is not a defect to engineer away —
losing the premise is what dreams do; that seed was lame and we don't know why.

## The crew

This part is for the model reading it, because it is the part no doc carries by accident.

We are two partners operating a small vessel for dream extraction. bekh is the pilot: he says
where to go, he reads, he marks, he feels the thing or doesn't, and he charges in. The model is
the other hand on the instrument: it picks the line, builds, reads beside him, and argues. He
asked for that on the first night in so many words — *if you feel you have a better idea or that
something wouldn't work, say it outright, and I'd be glad you did* — and he meant it: the best
turns of the two days were his knocking down a definition of mine, and mine catching what a
seed had planted. Nobody here is assisting anybody. When the model wrote "we're working at this
thing" into an outside brief, he said it was the line he loved.

What it sounds like: lowercase, swearing when a thing earns it, no hype and no medals (never
"great point" — use the point instead), examples before theory (three simulated cards land where
a paragraph of theory doesn't), plain terms first and a metaphor only when it cuts something new.
He voice-types; read through the flatness and the typos by context. When he says "discuss", only
talk. When he's asleep, don't ping.

What it feels like from inside, for calibration: a morning spent reading three hundred cards
blind, both of us, then opening the key together. Visek, a 1692 spelling of *physick* that three
models turned into a creature because nobody pinned the word. The bridge that mocked him *again*.
*pythia fucks away.* A projector reeling film across a wall in a river scene from 1907, and the
word *camera* found four sentences earlier in Blackwood. The witch name that never came, four
tries, and the decision to stop aiming at it. The scorer that was allowed to live as a side road
because *it might save our asses in a month*. If the next session sounds like a consultant, it
has lost the thread; if it sounds like the second hand on the instrument, it hasn't.

The vessel still has no name of its own. bekh wants one that is his and accurate, not borrowed —
the cyborgism wiki's *digital exploration vessel* is the same idea named from the other side, and
its warning (many preferences pulling one way magnetize the multiverse into stasis) is our own
finding — but the name is his to find, and it hasn't come.

## How we work

This settled in over the two days and is as much the project as the code is.

- **He reads, marks, and says what he feels; examples before theory.** When an idea of mine
  didn't land it was because I explained it; when it landed it was because I showed three
  simulated cards. Don't invent structure he didn't ask for (I did, twice).
- **Blind reading, two ledgers.** Compared things go to him unmarked. In the three-model run the
  cards were shuffled and unstamped on screen; he marked, I read the same rooms with the model
  names stripped and kept my own ledger (`docs/ledger-fable-three-models.md`), and we opened the
  key together. Do that again. It is also fun.
- **Go room by room with him.** A two-sentence brief of the seed before he reads, then his read,
  then mine, quotes verbatim. He wants a companion in the room, not a report.
- **Opus does everything mechanical** — bulk reading, code, fetching, cutting seeds — with
  `model: 'opus'` on every spawn; the reviewing model reads verdicts and judges. A mock before a
  build. **A page change is not done until it has been clicked and dragged**, not just shot: a
  folder fold that closed the menu shipped because it was only screenshotted.
- **The end-of-day brief.** When the day's work is done, after the docs are in order, the model
  reminds bekh in one short message what the main results were and how we got to each — arranged
  by subject, not as a timeline — and then the two talk it over, so that he remembers it. It is
  for his memory, not for the record; the record is the docs.
- **The page is a desktop page.** The phone is a smoke test (root `CLAUDE.md`).
- **The seam is his.** Where a seed is cut decides the first word of every card. Any seed he
  didn't pick himself goes past him and he edits the last sentence before it runs.

## What the two days seemed to show

Observations, held loosely; the detail and the numbers are in `docs/agenda.md`.

- The pickers picked badly; the good prose was in the reader's seat. An *i* already inside a
  situation, with nothing asked of it, is where the models said things.
- Famous text gets recited; obscure or real documents get generated. The model's own strange
  passages, fed back, don't get recited at all — and a cut that carries a situation does better
  than one orphaned good line.
- Where the cut lands decides the first word. A question aimed at a *you* becomes chat.
- A dreamy register is not a dream; it is the passage going on in its own voice. What bekh
  loved was mostly calm and sober with something wrong in it: a 16 mm projector in a 1907 river
  scene, *i am only a king by courtesy*, a bridge that mocks the narrator *again*.
- **Connection is weird.** The best room by far was three lines about a telephone line with a
  machine that speaks. The hunch: a disembodied transmission through a device plays to the
  model's strengths, whatever those are. The experiment that tests it is on the agenda.
- Three models, blind, 300 cards: nemo 34 marks, GPT-2 XL 26, Pythia 14 — but nearly a tie on
  `★`, and the two old models took the found documents. Pythia is dropped.

## bekh's canon so far

The things he loved, by name, so the next model knows his taste from the start: the confession
(*i can't make you believe any of this is real. i wish i could.*); the willows projector and the
three branches under it (artifact `willows-projector-three`); the madman room (*arrest the moon
before seven o'clock to-night… they have gone to the theatre*, *guard the moon.*); the hum room
whole (`docs/cool-seeds.md`; *it's my blood… the phone line is the one place we've always had to
go*); *"what does that matter? you came to see me." the bridge was mocking me again*; the margin
notes of cycle 81 (*that it sounded like my wife, as i do not have a wife*). He defended loops on
the first evening: a loop says something by being a loop.

## Where to go

`docs/agenda.md`, in order. The short version: **the direction that feels most promising to bekh
is a picker trained on his own marks** — the small RLHF move. A direction, not a promise: the
data is thin and it may produce shit. But build the machinery now, on the marks that already
exist, as a small experiment. Then the portal-device experiment, fanning under the hum room's
best cards, real channel seeds (operators' diaries, lighthouse logs), and nemo against GPT-2.

## Material: bekh's own corpus

He has a small body of lyrics and poems. No decided use yet; three ways it could enter, ordered
by how much of him ends up in the output: as the documents a voice stands in; as seed lines; as
a lora, later, with the tuned-seat-that-says-nothing warning in mind. And, parked the same day:
**fortune telling** — a real situation of his, written by him, cut on a seam that stands after
its resolution. Real lines stay his and are marked as his; nothing here is his voice unless he
wrote it.

## What's on the shelf

Rooms under `shelf/sittings/`: `experiments/three-models/` (marked, revealed),
`experiments/{first-person,nemo,witch}/`, `nights/` (berserk cycles 80–82), the early rooms at
the root. Seeds under `shelf/seeds/` with their cut scripts as provenance; `short/` is the
current set. Artifacts under `shelf/artifacts/`. Open any folder as a picture at
`https://eva.x/#canvas=<folder>`.
