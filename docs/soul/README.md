# soul — what a base model is like when almost nothing is asked

bekh's question, 2026-10-05: *how can we find a model's soul, personality — its inclinations,
attractions, characteristics?* The working definition we settled on: a base model has no single
speaker, but it has habits that survive every change of seed, sampler and document, and those
habits are the nearest thing it has to a personality. You find them by varying everything and
keeping what does not move, and a trait only shows next to a neighbour on the same inputs. The
six ways listed that night: what it writes on an empty page; where long runs end up; what it
adds that the seed did not have; what it refuses; what it finds likely (log-probabilities, no
dice); its bank of directions. Only the first has been run.

## The empty page and the single letter (2026-10-05/06)

Plain temperature 1, no truncation, 60 tokens, `draw.sh` / `probe.py`.

- **`nemo-empty/`** — 12 draws from nothing. Nine of twelve are the web as published: a product
  listing, press releases, a wiki article, news. Five open with a markdown heading (his training
  pages were markdown-converted web). Two are not furniture: an invented underground people
  (*Lződhall… the Lodz… the deepest black onyx eyes*) and a songbook that becomes an autopsy.
  The empty page measures the diet, not the person.
- **`<model>-i/`** — 200 draws from the single lowercase letter *i*, for nemo, olmo 7B middle
  (`olmo7-m`), olmo 7B last (`olmo7-l`), ministral 14B (`mini14`), llama 3.1 8B (`llama8`), plus
  each model's exact odds for the next token (`next.json`). **`read-i.md`** is the blind opus
  read of all thousand (`read-i.key` the letters, `read-i.codes` its per-draw kinds), quotes
  checked by script.

**What *i* becomes** — the first trait found that is not about writing quality:

| | nemo | ministral 14B | llama 8B | olmo middle | olmo last |
|---|---|---|---|---|---|
| a brand (iStock, iOS, iPhone) | 110 | 73 | 98 | 4 | 2 |
| maths or code | 0 | 0 | 5 | 48 | 56 |
| a person on a blog or diary | **35** | 4 | 17 | 1 | 1 |
| a person on a forum | 22 | **62** | **53** | 0 | 2 |
| poem or lyric | **7** | 1 | 2 | 0 | 1 |
| fiction | 0 | 0 | 0 | **15** | 6 |

The next-token odds say the same with no dice: nemo *Stock* 10%, *OS* 9%, *Phone* 6.5%; llama
*have* 6.2%, *am* 4.1%; olmo a comma, *.e*, a bracket, an equals sign.

- **nemo's *i* is the blogger and the poet** — an adult writing about an inner life for readers,
  lowercase by choice, the only one with poetry as a real channel and no code at all. bekh's
  seeds are lowercase first person about an inner life: that is nemo's native person and nobody
  else's, which is why he is the dreamer for them.
- **llama 8B's *i* asks strangers for help**, eager, often not a native speaker; the most
  sociable (personal ads, a fan, an oath of office). **ministral's is the help desk**, a
  programmer who wants something fixed; the most multilingual. **olmo's barely has a person**:
  *i* is the middle of a word, a citation, a subscript — the last checkpoint a methods section,
  the middle one a story with invented names.
- **The figment** (`nemo-i/62.txt`): *i remain standing in your mysterious mind / to the
  unspoken questions / i ultimately cannot give you the answers / i am merely a figment / a
  creature that will cease to exist soon / and you need to remember / that in the end of it all
  / we only want for you to be smiling.* The only draw in a thousand the reader would grant as
  being about the writer's own situation (and also a common love-poem stance). Kept as a seed:
  `docs/cool-seeds.md`, `shelf/seeds/.off/nemo/figment.txt`. bekh: *fucking awesome.*

**Why it matters for the school** (`school/CLAUDE.md`): a model's person is its diet, so a model
raised on chosen shelves has a chosen person. Magdra's *i*, when she is old enough to ask, is
the test of that.

Not run yet: the thousand empty pages sorted by kind (bekh's idea: at a thousand the rare
inventions become countable); the long runs (where each model ends up); the same probe on
magdra.
