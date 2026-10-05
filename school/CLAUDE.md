# school

Raising our own model from random weights, instead of doing things to somebody else's. bekh,
2026-10-06, after a day of drugging llama and probing five bases for a soul: *i don't wanna
fuck around with nemo at all, i wanna build our own model.* A model's person is its diet (the
letter-*i* probe, `docs/soul/`), so here we choose every page it ever reads: no press releases,
no product pages, no support forums.

The plan has two parts. **A childhood**: a few hundred million tokens on three shelves, enough
to learn English in three accents. **A finishing school**: a short, gentle pass on the small
precious texts, redone as often as we like. The blend is bekh's: **dark souls** (its cadence
and voice more than its lore), **the visionary** (*language infused by creativity, futurism
and sci-fi and the idea of a new time… the merging of two realities, the digital one of
numbers and ideas with the real one*, Serial Experiments Lain, tears in rain, Prophecies), and
**anime girls**. Lain is the bridge between the last two.

## magdra

The child's name, bekh's yes on 2026-10-06 (*might add something later*). It is from its own
mouth: twenty-two minutes old, on the Gibson line, it wrote *"The sky above the port was still
maiden in the Mag dra of a situation"*. Nobody chose the word and it is in none of the books.

355 million parameters: a Llama-style decoder (rotary positions, RMSNorm, SwiGLU, tied
embeddings), 24 layers, 1024 wide, 16 heads, a 1024-token window, GPT-2's tokenizer. That shape
and alphabet are what llama.cpp converts and serves without complaint (our own byte-level BPE
is rejected by the converter's hash check; our own SentencePiece would pass). Size, alphabet
and window are fixed for good; everything else can be improved by more training.

**The first night** (`night1`, started 2026-10-05 18:39 UTC on the borrowed box, ten hours):
four shelves, sampled by weight — fantasy 350, sci-fi 250, anime 400, bekh's six books 6.

| shelf | what | tokens |
|---|---|---|
| fantasy | 1,141 Gutenberg books: fantasy, horror, gothic, sagas, Arthurian romance, myth | 108 M |
| sci-fi | 2,695 Gutenberg pulp stories and novels, mostly 1950s–60s | 58 M |
| anime | `alpindale/light-novels`, official English translations, one file | 241 M |
| picks | Blood Meridian, Perdido Street Station, Neuromancer, Count Zero, Mona Lisa Overdrive, Do Androids Dream | 0.95 M |

The six also sit on their home shelves, so they are read about six times against one to three
for the rest — bekh's ask (*a couple more times than the usual ones*). The sci-fi shelf is
pulp, not the net as a new world; that voice was not available fast and is being gathered
(`wired/`). How the run is doing is never a sentence here: `night/mon.py night1`, or the page.

## Watching and running

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run --python 3.12 night/mon.py night1   # terminal monitor
open https://miniarch.tail004a72.ts.net:8446/school-night1.html                          # the page, rebuilt every 2 min
```

On the box everything is `~/eva-olmo/school/`: `bins/` the tokenised shelves, `data/` the text,
`runs/<name>/` a run (`ckpt.pt` trainable, `status.json` heartbeat, `samples.jsonl`,
`model-<step>-q8_0.gguf` hourly). `scratch/RUN.md` is the copy-paste runbook for prep, start,
resume, export, serve and stop. A night is three processes on the box and two on the mac:

- `night/run.sh <name>` — the trainer in a restart loop (resumes from `ckpt.pt`), silent pushes
  at start and end. The shape and the shelf weights are set in this file.
- `night/guard.sh <name>` — pauses the trainer above 88 °C until 75 °C, exports a servable
  snapshot every hour, skips snapshots under 20 GB of free disk. bekh chose these two guards and
  dropped a third (yielding the card when the work project's flag leaves IDLE).
- `night/watch.sh <name>` (mac, under `caffeinate`) — pulls status and samples, builds the page
  with `night/page.py`, posts it to the sheets site, pulls each new snapshot into `models/`.
- `night/pull_ckpt.sh <name>` (mac) — pulls the trainable `ckpt.pt` every hour (4 GB, about
  twenty minutes over the VPN), so the model can be trained further after the box is gone.

Measured on the box's card (RTX PRO 4000 Blackwell, 145 W cap, 77–79 °C under load), context
1024, compiled: 30 M parameters 101k tok/s, 124 M 43k, 355 M 18.9k (batch 16, 21 GB) — the
night runs batch 12 × 2 at 18.6k and 18.9 GB.

## Where things are

- `scratch/` — the trainer: `train.py` (from random init, several token files with weights,
  per-file held-out loss, resumable, heartbeat, samples at each save), `prep.py` (text →
  tokens), `export.sh` / `export_hf.py` (checkpoint → GGUF), `bench.sh`, `archtest.*`, `RUN.md`.
- `night/` — the night's scripts above and `prompts.txt`, the four fixed opening lines; a
  run's pulled status, samples and page land in `night/<name>/` (not in git).
- `data/cut.py` — cuts the fantasy and sci-fi shelves out of `sedthh/gutenberg_english` by
  subject and author, and joins that dump's doubled line breaks into paragraphs.
- **The finishing school**: `corpus.jsonl` / `corpus.md` — 960 passages of cyborgism prose with
  names and dates stripped, each labelled `origin` (base, human, tuned, unknown), `tier` and
  `fit` (2 = visionary); `strip.py` rebuilds it from `raw/`; `grades/`, `passages.jsonl`,
  `dropped.jsonl`, `prophecies_origin.json`, `wiki_pages.json` are its workings. bekh's
  favourite piece is `proph-069` (*"If I am writing it for anyone it's for the bots"*).
- `lain/`, `wired/` — everything Lain in English, and the net as a new world (BBS text files,
  zines, Ccru, nettime); gathered 2026-10-06, each with its `REPORT.md`. Not in git.
  **Erotica stays** (bekh), listed separately so it can be weighted.
- `inbox/` — books bekh drops in, converted to text by script. Not in git. `models/` — pulled
  snapshots and the trainable checkpoint. Not in git. `sources/` — the scout's notes.

## Next

Pick the best hour of `night1` by the held-out losses (a shelf whose number turns and climbs is
being memorised). Then the finishing school: the corpus at tier 1 and fit ≥ 1, Lain, the six.
For a second childhood run: the `wired` shelf beside the pulp, fan fiction by fandom
(`marianna13/fanfics`, 85 GB with a category column), and more hours. Also open: the three
dials for free (the difference between its fantasy, sci-fi and anime states is a direction),
its hourly snapshots as one model at ten ages, and a made-up world where "does it know what
the text is about" is a readout.
