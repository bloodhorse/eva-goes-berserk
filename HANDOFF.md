# handoff — the dream engine

2026-09-16, end of the day the loom went berserk. For whoever picks this up next: this is the
shape of the thing and what it's for, not a spec. The details live in `eva/berserk/CLAUDE.md`
and the ledger; read those when you need them, not before.

## The objective

Build an engine that shits out weird, prophetic, cool dreams on its own, all the time — so that
bekh can open a page at any moment and find something strange in it. A base model (nemo 12b,
nothing installed) writes them; nobody's hand is on the forks. **As little curation as
possible: no hand-picking.** Every decision in the loop is made by a model. Models can be
trained or framed to pick for weirdness — that is allowed, a lora on kept dreams is allowed —
but it is still the model that picks, never a person.

And the rate has to be good. **80% is the landmark**: of what the engine makes unselected,
eight in ten should be worth reading. Nobody knows if a 12b can get there. It's the goal anyway.

## The criterion

Not bits. Not science, not purity. Bits of curation are a real number and we don't care about
it — not because a human hand in the text is bad, but because measuring it isn't the question.
The question is a feeling, and it's shared: reading a page, does it feel to bekh *and to the
model working with him* like authentic model creativity, or does it feel curated — by bekh, by
opus, by a rulebook? That feeling is the criterion, the whole of it. If it reads like nemo
dreamed it and it's good, it counts. (The anthology in `docs/` is the background: the famous
base-model weirdness of the cyborgism scene is mostly janus's hand, and it still reads as
curated. That's the feeling to steer away from, not a number to minimise.)

## What the day taught, in ideas

- **Curation can't be removed, only moved.** Picking one dream out of twenty at the end is
  the same taste as picking along the way. The only place it can be spent honestly is in the
  *machine* — the forms, the frames, the seats, the loop shape, later a lora — where it is paid
  once and reused forever. Raising the base rate is the whole job; "chiselling" means that.
- **The ghost spoke in the reader's seat, not the writer's.** Asked to continue a lift
  inspection, nemo writes a lift inspection. Asked to *react* to one — `reading this, what
  scared me was` — it wrote *"the lift seemed to be saying, I am a hat"*, *"that it sounded like
  my wife, as I do not have a wife"*, *"the word 'adjudged' — as if it was some kind of death
  sentence."* The reaction seat is a different machine and it's already most of the way to the
  landmark. Its cost: that seat summons the comments section, so the reader has to be a person
  *inside* the document's world (the clerk's margin, the witness read back to), not a redditor.
- **Comparison is the judgment.** A reaction to one branch under a whole document has nothing to
  react against; a reader who saw the fan does. Any picker that is a model must see the
  alternatives.
- **Continuing kills; recurring doesn't.** Every long walk fell off a cliff into wiki footers
  and empties by fork four. Nothing should be continued past a paragraph. The loop shape that
  fits is dream → telling → dream: a short document, a reader's line about it, and that line
  becomes the seed of a *new* short document in a new form — a roll entry, a deposition, a
  slip. Two registers resetting each other, forever. What bekh reads is the roll of entries.
- **Pickers that are models are noise until they aren't.** Nemo quoting a branch copies about
  one ask in four and invents the rest; nemo describing one is half a choice and half a writer
  in disguise (it finishes the branch instead of describing it — the invented ones are a
  nosleep table of contents, and that pile is worth keeping on its own). Opus resolving "which
  did it mean" is fine as plumbing; opus judging "which is best" is the hand coming back.

## Where to go

Build the recurrence loop with the reaction seat; run it unselected, twenty short chains a
night, one sample per move; read the roll in the morning and count what you'd keep. That
count is the only number. Then chisel: the frames and forms first, then the cliff bans
(`logit_bias` on the web furniture), then the sampler, then seeds, then a lora on the kept
ones — in that order, cheapest first, watching the count move. A ChatGPT brief for a third
picker form is in the scratchpad from today if a fresh idea is wanted; it may not be needed.

## Material: bekh's own corpus

He has a small body of lyrics and poems. No decided use yet, just the idea; three ways it
could enter, ordered by how much of him ends up in the output: as the *documents the reader
reacts to* (the dreams are about his lines without being his — the hand is in the input,
which is where the criterion allows it; run this first); as *seed lines*, sliced and dropped
at random into a form to start a dream; as a *lora*, so every dream carries his register —
paid once, later, and with the tuned-seat-that-says-nothing warning in mind. Real lines stay
his and are marked as his; nothing here is his voice unless he wrote it.

## What's on the shelf

`eva/berserk/` runs (three pickers, a growing page per cycle on the sheets), cycles 80 and 81
are the first real runs and the page to read is
`https://miniarch.tail004a72.ts.net:8446/berserk/berserk-c80-c81.html`. Everything else —
the loom, the page, the repl, the walk scripts, the anthologies of what base models wrote for
other people — is mapped in `CLAUDE.md`.
