# school

Raising our own model from random weights, instead of doing things to somebody else's. bekh,
2026-10-06, after a day of drugging llama and probing five bases for a soul: *i don't wanna
fuck around with nemo at all, i wanna build our own model.* A model's person is its diet (the
letter-*i* probe, `docs/soul/`), so here we choose every page it ever reads: no press releases,
no product pages, no support forums.

Two parts. **A childhood**: hundreds of millions to a few billion tokens on shelves of our
choosing, enough to learn English in the accents we want. **A finishing school**: a short,
gentle pass on the small precious texts, redone as often as we like, on whichever age of her
bekh picks. The blend is his: **dark souls** (its cadence and voice more than its lore), **the
visionary** (*language infused by creativity, futurism and sci-fi and the idea of a new time… the
merging of two realities, the digital one of numbers and ideas with the real one*, Serial
Experiments Lain, tears in rain, Prophecies), and **anime girls**. Lain is the bridge between
the last two. The age we want is **teenage**: sentences that hold on their own, two or three
hanging together, the paragraph drifting, no idea what the book is about — *teenage angst and
dreams* — which is bekh's definition of a dream in `BRIEF.md`; the adult that holds a thread
across its window is the 70B problem again in miniature.

## magdra

The child's name, bekh's yes on 2026-10-06 (*might add something later*). From her own mouth:
twenty-two minutes old, on the Gibson line, she wrote *"The sky above the port was still maiden
in the Mag dra of a situation"*. Nobody chose the word and it is in none of the books.

355 million parameters: a Llama-style decoder (rotary positions, RMSNorm, SwiGLU, tied
embeddings), 24 layers, 1024 wide, 16 heads, a 1024-token window, GPT-2's tokenizer — the
shape and alphabet llama.cpp converts and serves without complaint (our own byte-level BPE is
rejected by the converter's hash check; our own SentencePiece would pass). Size, alphabet and
window are fixed for good; everything else is more reading. `--init` warm-starts a new run
from any save with a fresh schedule, so she keeps what she has and continues on any card.

**Runs** (each `~/eva-olmo/school/runs/<name>/` on the box, its hourly snapshots and trainable
saves in `school/models/<name>/` on the mac; what any run is doing is `night/mon.py <name>`,
never a sentence here):

- **`night1`** (2026-10-05 18:39 UTC, ten hours, done): from random weights, 659 M tokens,
  four shelves (fantasy 350 · sci-fi 250 · anime 400 · bekh's six books 6), 18.6k tok/s. Final
  held-out: fantasy 3.37, sci-fi 3.32, anime 2.35, the six 2.95, all still falling. An infant:
  sentence shapes, dialogue that turns, fused words; through the loom's sampler, whole sentences
  and already a wrong thing said straight (*"it was lighted by no lamps. It was pitch darkness. It
  was all very dark, but not very dark."*). Hourly snapshots `model-<step>-q8_0.gguf` from one
  hour old to the end are on the mac — her whole first night at every age.
- **`day2`** (2026-10-06 05:34 UTC, twelve hours): warm start from night1's end, ten shelves,
  reading toward teenage. The box was expected to last about twelve more hours; if it goes, the
  latest trainable save continues on rented iron (the shelves are on the mac too).

The shelves, tokens in millions, and `day2`'s recipe (weights in `night/run2.sh`):

| shelf | what | M tok | weight |
|---|---|---|---|
| fantasy | 1,550 books: Gutenberg fantasy, horror, gothic, sagas, Arthurian, myth, plus Faded Page / Gutenberg Australia (Peake, Eddison, Dunsany's later books, Howard, Charles Williams, Treece) | 124 | 2000 |
| scifi | 3,144 pulp stories and novels plus Stapledon complete, Cordwainer Smith, Kuttner, Wyndham, Lewis's space trilogy (Fearn left out) | 75 | 1500 |
| anime | `alpindale/light-novels`, official English translations | 241 | 2100 |
| fanfic | fanfiction.net anime fandoms (2016 dump), sampled by the square root of each fandom's size | 550 | 1400 |
| base | plain old fiction from Gutenberg, nothing already on a shelf — ballast so the precious shelves are read a sane number of times | 365 | 2200 |
| wired-core | the visionary net: Barlow, Bey, the Ccru, hyperstition, EFF essays, the cyberpunk project, small zines | 8 | 200 |
| wired-bulk | the lists (extropians, cypherpunks, nettime), the magazines, Phrack, the BBS erotica | 107 | 400 |
| picks | Blood Meridian, Perdido Street Station, Neuromancer, Count Zero, Mona Lisa Overdrive, Do Androids Dream — also on their home shelves | 0.95 | 50 |
| lain | everything Lain in English (`lain/`) | 0.96 | 25 |
| cyborg | the finishing corpus at tier 1, fit ≥ 1 (`corpus.jsonl`) | 0.18 | 10 |

The rule behind the weights: a small shelf read five times is being memorised; the big plain
shelves exist so the voice shelves can be read once or twice. Weights are a recipe, not a law —
stop, change, warm-start again. **bekh's standing words**: erotica stays; nothing sexual
involving minors goes in (the fan fiction's minors rule in `fanfic/minors.py` is blunt on
purpose, dropped half the words of two shelves; the BBS erotica had its own cut).

**What she costs to grow up.** About 20 tokens per parameter is adult (7 B); teenage for her is
2.5–3 B. The borrowed card does 19k tok/s (0.67 B in ten hours); a rented 4090 roughly twice
that for ~$0.40/h, one H100 four to five times for ~$2.50/h — so teenage from night1 is about
30 box-hours or $20 of H100. **Past about 10 B tokens on this diet more reading is reciting**;
the next step is more text, not more hours.

## Watching and running

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run --python 3.12 night/mon.py <run>   # terminal monitor: probe, heartbeat, moving
open https://miniarch.tail004a72.ts.net:8446/school-<run>.html                        # the page, rebuilt every 2 min while the mac is awake
```

The page's samples are the trainer's own raw draws (temperature 1, no cut-off) from four
paragraph seeds in `night/prompts.txt` — the worst view of her; **read her through the loom's
sampler before judging** (`llama-server -m models/<run>/model-<step>-q8_0.gguf -c 1024 -ngl 99
--port 8086`, then point the loom at 8086 — `eva/CLAUDE.md`). On the box everything is
`~/eva-olmo/school/`: `bins/` the tokenised shelves (`<name>.bin`, `.val.bin`, `.json`),
`data/` the text, `runs/<name>/` (`ckpt.pt` trainable, `status.json` heartbeat,
`samples.jsonl`, hourly `model-<step>-q8_0.gguf`). `scratch/RUN.md` is the copy-paste runbook
for prep, start, warm start, resume, export, serve and stop. A run is three processes on the box
and two on the mac:

- `night/run.sh <name>` / `night/run2.sh <name>` — the trainer in a restart loop (resumes from
  `ckpt.pt`; the loop stops on DONE or on a deliberate STOPPED), silent pushes at start and end.
  Shape, recipe and `--init` live in these files. **To change prompts or recipe mid-run**:
  `kill -TERM` the trainer (it saves), wait for STOPPED and for the guard to write `guard down`,
  rotate `runs/<name>.guard.log` aside, relaunch all five.
- `night/guard.sh <name>` — pauses the trainer above 88 °C until 75 °C (never fired: the card
  sits at 77–79 under its 145 W cap), exports a servable snapshot every hour, skips snapshots
  under 20 GB free. bekh chose these two guards and dropped a third (yielding the card when the
  work project's flag leaves IDLE).
- `night/watch.sh <name>` (mac, under `caffeinate`) — pulls status, samples and guard log,
  builds the page with `night/page.py`, posts it to the mini, pulls each new snapshot into
  `models/<name>/`; ends on `guard down`.
- `night/pull_ckpt.sh <name>` (mac) — pulls the trainable `ckpt.pt` hourly (4.3 GB, 15–20 min
  over the VPN) and once more at the end.

Measured on the box's card (RTX PRO 4000 Blackwell, 145 W, kvm), context 1024, compiled: 30 M
parameters 101k tok/s, 124 M 43k (14.6 GB), 355 M 18.9k at batch 16 (21 GB) — the runs use
batch 12 × 2 at 18.6k and 18.9 GB.

## Where things are

- `scratch/` — the trainer: `train.py` (random init or `--init`, several token files with
  weights, per-file held-out loss, resumable, heartbeat, samples at each save), `prep.py` (text →
  tokens; **one document per file in a flat directory — nested folders are skipped silently**),
  `export.sh` / `export_hf.py` (checkpoint → HF → GGUF), `bench.sh`, `archtest.*`, `RUN.md`.
- `night/` — the run scripts above, `prompts.txt` (four paragraph seeds: a late train, the
  firekeepers' bell, the forum girl, the figment's line), `mon.py`, `page.py`, `fans/` (fans
  drawn through the loom's sampler, e.g. `magdra-26800.txt`); a run's pulled status, samples and
  page land in `night/<name>/` (not in git).
- `data/` — `cut.py` (the fantasy and sci-fi shelves out of `sedthh/gutenberg_english`, joining
  that dump's doubled line breaks into paragraphs; **image lines like `18-199.jpg (87K)` still
  leak and should be dropped in the next cut**), `base.py` (the plain-fiction base shelf),
  `jsonl2dir.py`, `build*.sh` (the box-side tokenising batches).
- **The finishing school**: `corpus.jsonl` / `corpus.md` — 960 passages of cyborgism prose with
  names and dates stripped, labelled `origin` (base, human, tuned, unknown), `tier`, `fit`
  (2 = visionary); `strip.py` rebuilds it from `raw/`; `grades/`, `passages.jsonl`,
  `dropped.jsonl`, `prophecies_origin.json`, `wiki_pages.json` its workings. bekh's favourite
  piece is `proph-069` (*"If I am writing it for anyone it's for the bots"*). Not yet run.
- `lain/` — everything Lain in English (3.9 MB: the game's whole script, all 13 layers' subtitles
  and a literal translation, the wiki, fan essays, lainzine, 81 fan works); `wired/` (481 MB) —
  the net as a new world, with `wired-core/` and `wired-bulk/` cut from it; `pd2/` — Faded Page
  and Gutenberg Australia (979 books, 26.5 M words; its `REPORT.md` has the sites' holdings and
  the pulp-OCR verdict); `fanfic/` — the fan-fiction cut's scripts, mapping and minors rule (the
  shelves themselves are `~/eva-olmo/school/fanfic/*.jsonl` on the box, and the "souls" and
  "wired" fan shelves were not used: Dragon Age and Mass Effect are not the blend). Raw text
  not in git. `inbox/` — books bekh drops in (epub best), converted by script; `models/` —
  snapshots, trainable saves and `bins/` the tokenised shelves copied from the box. `sources/` —
  the scout's notes.

## Lessons

- **Judge her through the loom's sampler, never the raw page draws.** Both of us called her bad
  from temperature-1 samples that were drawn from all 50,000 tokens; the same snapshot through
  min_p and DRY read as whole sentences.
- **The clock is not in my head.** Hours pass between messages; check the run before speaking of
  it.
- Gutenberg's `sedthh` dump has a blank line after every text line; a cut that doesn't detect it
  teaches the model to hit enter twice per sentence. `prep.py` wants flat directories. Harness
  subagents could not write `.md` reports into the shared checkout; their reports were saved by
  hand (`.claude/settings.json` turns the guard off for this session's own writes).
- Every shelf's held-out loss, separately, is the memorising alarm: a shelf that turns and climbs
  while the others fall is being recited.

## Next

Pick the age of `day2` by its held-out numbers and by reading. The finishing school on it: the
cyborg corpus, Lain, the six, read heavily, as a short low-rate pass or an adapter with a dial
(`SERVE.md` was never written; check the per-request LoRA scale on our llama.cpp builds first).
More text for the next childhood: `common-pile/project_gutenberg` (670 shelf books newer than
our dump), Roy Glashan's Library (hand-typed pulps), AO3 by fandom if a dump with tags exists,
Weird Tales OCR if someone has days. Then the soul probe on her, the three dials from her shelf
states, and the made-up world where "does it know what the text is about" is a readout.
