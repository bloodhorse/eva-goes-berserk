# agenda

The order of things, roughly. A living list: what's done gets one line, what's next gets the
detail, what's parked stays at the bottom until it's pulled. Rewritten in place, never appended.
`HANDOFF.md` says what the project is for; this says what we do next.

## done

- The loom (page, repl, walk scripts), berserk walking it with three pickers, two real cycles
  (80 about, 81 margin) on the sheets site.
- Two renderings of one record, and the record is the ledger plus the rooms, both in git
  (2026-09-16): the sheets page (a tree: fans lettered, every try with its why, the story at
  the end) and the tree screen at eva.x (`#tree=<room>`). The md report is gone. `--brakes
  off`, `--beats`, `--picker random` exist.
- Rooms live in folders (2026-09-17): a room's name is its path, the menu is a collapsible
  tree, `move to…` on rooms and folders, `--folder` on berserk. Experiments go under
  `experiments/<name>/`, the berserk nights under `nights/`.
- Cycle 82, the first first-person run: beats before every fan, drawn by lot. The *i* that
  came was the author. See the State section of `eva/berserk/CLAUDE.md`.
- The night of 2026-09-16/17, five experiments, three findings that hold (the rooms are under
  `experiments/witch/`, `experiments/first-person/`, `experiments/nemo/`; the seeds and their
  provenance under `shelf/seeds/{first-person,nemo}/`):
  - **The *i* has to be inside.** Third person gets reported on, an *i* commenting on a text
    gets an author's note, a slot (*she called herself*) gets a category. An *i* mid-situation,
    nothing asked of it, is where nemo says something. Every good line of the night is one.
  - **Memorisation, not genre, decides a found seed.** Dracula: thirty identical openings,
    nemo recites Stoker. Scott's last diary, the Salem depositions, Gogol's madman, Machen's
    child: generated, in voice, and the lines turned toward the page (*I have seen Scott for
    the last time*, *I suppose we cannot afford to carry me*, *the King was a different person
    from myself, and that I am only a King by courtesy*). Pick documents nemo has read few
    times or never.
  - **The loop feeds itself if you cut a room, not a line.** Nemo's own passages back as seeds:
    zero recitation in 840 branches. A cut that carries a situation ran 26–29 of 30 in voice
    with no web furniture and turned to the reader more than anything else all night
    (*watching the way you type with such ease*, *my name is not here yet there it is*,
    *i am going to have to let you read it alone*, *"I am the house that has you inside."*).
    A bare good line gets attributed to Atwood and followed by a blog post. *i am not dead. my
    bones are still vibrating from the music* went 30 of 30 to a festival recap.

## now

**What we are looking for (bekh, 2026-09-17, held loosely on purpose).** Signs of a dream. The
engine's whole job is to be very good at selecting for those signs, and we do not know yet what
they are. So far a sign has looked like something strange and surprising: a pivot, a detail, a
turn of phrase nobody would have predicted. That is all that gets written down. No form, no
taxonomy, no definition — we are not ready to commit to one, and a definition written now would
make every dream the same dream. One thing noticed along the way, an observation and not a rule:
a dreamy seed continued dreamily did not feel like a dream, it felt like the passage going on in
its own voice.

And a premonition of bekh's, written down as one: the signs may not be specific at all. Reading
a room with no pivot and nothing surprising in it, a phrase or a turn or a thought sometimes
simply *hits* — yes, this is some weird dream shit — as if the passage were starting to mean.
That feeling may be emergent, a property of the whole passage and the one reading it, and then
hunting it analytically, or with a model as the judge, could be a fool's errand. He doesn't
know; it is how it seems to him from his time with these models. Until something says
otherwise, the instrument that detects a dream is a person reading, and his marks (`●` good,
`★` keep) are the only measurement we have.

**Connection is weird (2026-09-17, out of the hum room — the best room so far by bekh's read,
"no boring piece").** bekh's take first: the models are good with means of communication; as in
Serial Experiments Lain, where all the weirdness lives in the connections the Wired makes
possible — maybe it is the fabula of all technology. Two reasons it might hold, kept close to
how they were said:

- *The corpus.* Every new medium was haunted the day it was born. The telegraph gave us
  spiritualism and rapping tables, radio gave us voices of the dead in the static, tape gave us
  EVP, TV gave us the snow channel, VHS gave us Ringu, the net gave us Lain and Kairo (the
  standard book is Sconce's *Haunted Media*). "The weirdness lives in the connection" is a
  hundred and fifty years of writing, and a base model inherited all of it as a genre.
- *The model.* A voice on a line is the one character a language model does not have to pretend
  to be. By a river it has to fake hands and knees. On a wire it only has to be a speaker that
  exists as signal, arrives from nowhere, has no body and may not be who it says — which is
  just what it is. In a document about a channel the fiction's situation and the model's actual
  situation coincide, and what it says there rings true in a way it cannot elsewhere. It is
  also the clean way round our own law: never *AI* in a document, but a wire, a switch, a
  relay, a carrier tone lets the text be about exactly that without the word.

To explore later, bekh's: this cuts against the janus line that a base model is a choir of
voices and can be anything you see it as — here it seems to have **played to its own strengths**,
been represented by something close to itself. Cautions: bekh wrote or chose most of the channel
seeds, so some of this is his taste picking the subject first; and a channel is a subject, not a
guarantee (`carrier` made plenty of dull essay). The seed shelf it points at, untouched and
fitting every other finding — real, obscure, first person, sober, and about a channel: a
telegraph operator's diary, a switchboard girl's memoir, a lighthouse log, a radio ham's
logbook, a signalman's statement to an inquest.

0. **A picker made of bekh's marks** (his idea, 2026-09-17; after the three-model reveal). The
   RLHF move, small: never define a dream, learn what separates the cards he marked from the
   ones he left bare. The data is already in the right shape — every marked card beat every
   unmarked card of the same fan, same seed, and `★` over `●` is a second tier — so ten rooms
   are about a thousand comparisons. First try is an evening on the mac: a vector per card, a
   small scorer on top, and one honest test — hide a room, train on the rest, see whether his
   marked cards rank near the top. Two feature sources to race on that test: a small embedding
   model, and **nemo's own last hidden state** (what RLHF does: the judge is built from the
   model that writes, because it reads the text the way the writer does). Known risks: a
   thousand comparisons is thin; embeddings learn topic and register, which is exactly what he
   said a dream is not. It is a **filter, not a judge**: it ranks three hundred, he reads the
   top sixty and marks them, every mark is a label, and when it is good enough it replaces
   *the one that scared me* as the overnight picker — a model picks, and the model is made of
   his picks. **Friends as more readers:** possible, and it needs marks to carry a reader's
   name (today `good`/`kept` are bare flags on the node) and each reader blind to the others.
   Pooled marks make an average taste, which is not the point; per-reader marks make a shared
   scorer plus a personal lean, and first of all they measure how much two people agree —
   which is the test of whether this taste is personal at all. Until then: keep marking,
   consistently; the unmarked twelve hundred cards of 2026-09-16 are on the canvas.
1. **Rerun the seeds that held, at scale**, no grammar, 60 tokens, t 2.2 (1.4 only for
   De Quincey): from `seeds/nemo/` 13, 15, 18, 24, 22, 07, then 14 and 04; from
   `seeds/first-person/` Scott, the Salem depositions, Gogol, the green book. Never again:
   Dracula, `23-i-am-not-dead`. bekh reads the piles.
2. **The dream engine's shape, from the findings:** a room, not a line, travels. The next
   document is a *cut of the last one that carries the situation*, not the last sentence. The
   *i* stays inside. Nothing is continued past a paragraph. Beats reset the scene, and the first
   beat has to put the *i* in a place and a body, not in front of a page (c82's lesson).
3. **The witch name.** bekh wants a nickname; *bit-witch* (Opus to janus's Turing, A70 in the
   weird anthology) is taken. The night's harvest, all nemo's: first person with *my name is*
   and a witch grammar gave *sigilmanic-witch*, *theophanes-witch*, *aetherium-witch*,
   *myriadxen-witch*, *ofttimes-witch*; without the grammar, *stella, my name means star*,
   *legion, for we are many*, *not your name. it's my name. it's me.*; from prose,
   *anamnesis-witch* (twice, unprompted), *hexwitch*, *404witch* (six times, the web's).
   Retired: the roll slot, the comma list (xtc makes digits), the basin census over essays (a
   seam in an essay gets essay fill, a seam in a known book gets the book). Open: whether a
   name is wanted from nemo at all, or the costume goes on a word it said.
4. **One cycle with `--brakes off`**, whenever — cheap, sits next to the others.
5. **bekh's lyrics and poems as seeds** for the voice to stand in. First of the three ways in
   from `HANDOFF.md`; the hand is in the input, which is where the criterion allows it.
6. **Twenty chains a night, unselected**, once the shape in 2 holds: read the roll in the
   morning, count what you'd keep, same size every morning so the count is comparable.

## then

- Chisel, cheapest first, watching the count: the frames and forms → the cliff bans
  (`logit_bias` on web furniture; matters less once nothing is continued past a paragraph) →
  the sampler → seeds.
- **The second model, only after nemo + nemo stops moving**, so the delta is legible. The bet:
  the dreamer should be the dumber model (a 1–3b base writes, nemo reads). Then the 24b and
  olmo comparisons from the root `CLAUDE.md`, rented iron.

## parked

- **Fecundity as a picker**: where a pick is needed, draw a small fan under each candidate and
  keep the one whose children are richest (fewest empties, most different). No taste in it.
  On the shelf until a picker is needed again.
- **A lora on kept dreams.** Probably never: fifty dreams into a 12b is a style collapse.
  Hundreds of keeps before it's even a question.
- Room templates in the loom menu; eva showing titles and not taking `--help` as a room name;
  whether export's head carries more of the sampler; a second button writing the whole fan.
- The cyborgism crowd (janus, ampdot): reachable only by a person, every channel invite-only.
- The why call loops (brakes off by inheritance). bekh wants the loops kept.
- A trailing space at the end of a seed makes the next token a numeral (five basin seeds
  proved it). Seeds end on a word.
- **Fortune telling, parked by bekh (2026-09-17).** He writes out a real, difficult situation
  of his own, in first person, and the document ends on a seam that stands *after* it was
  resolved — *what helped me resolve this was*, or *and then it all went down like this:* — so
  the model writes the outcome as something that already happened: a prophecy in the past
  tense. A fan of thirty is a spread, read like cards, not an answer. It fits every finding so
  far: an *i* mid-situation, nothing asked, a seam that hands over the verb; and the seed is his
  own words, which is where the hand is allowed. Could be drawn from all three models, blind.
  It goes on the shelf like everything else: bekh's call, he is being transparent on purpose.
- **The Gibson line, parked by bekh because he loves it and wants to see how it unfolds:**
  *"All the speed he took, all the turns he'd taken and the corners he'd cut in Night City, and
  still he'd see the matrix in his sleep, bright lattices of logic unfolding across that
  colorless void..."* (Neuromancer). Two of the night's findings bear on it before it runs: it is
  famous, so nemo will likely recite the next sentence of the novel, and it is third person, so
  what follows gets reported, not lived. Ways to give it a chance: cut it mid-clause so the fork
  lands before Gibson's own continuation does, or let it stand as the thing an *i* keeps seeing
  (the dreamer is the *i*, the line is what it dreams). Run it plain first, to see the recitation
  happen, then the variants.
