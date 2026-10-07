# scratch — the kit

The trainer and what stands beside it, as it runs on the training host. On ds-dev2 these files lie
flat in `/opt/llama/magdra/`; this folder is their home in git. **A file here and its copy on the
host must be the same file**, and during a run they must stay that way: `run3.sh` and `run4.sh`
restart the trainer from whatever `train.py` is on disk, so a new one copied over mid-run is
picked up at the next restart.

```bash
cd ~/tower/forge/eva-goes-berserk/school && md5 -q scratch/train.py night/run3.sh night/guard.sh
ssh -o ConnectTimeout=15 -i $KEY BekmemetevVO@ds-dev2.x340.org 'cd /opt/llama/magdra && md5sum train.py run3.sh guard.sh'
```

## What is here

- **`train.py`** — a Llama-style decoder from random weights or `--init <save>` (a warm start: the
  weights and a fresh optimizer and schedule); several token files with weights
  (`--data a.bin:2000 b.bin:1500 …`, a weight being the chance that a row of a batch is drawn from
  that shelf, at a random offset); held-out loss per shelf at every eval; a heartbeat
  (`status.json`); samples at each save; resumable from `ckpt.pt`. **A resume takes every setting
  from the save and ignores the command line**, the `--data` line included.
- **`prep.py`** — text to tokens. **One document per file in a flat directory: nested folders and
  `.jsonl` are skipped without a word.** By default it holds out every hundredth document (a shelf
  under a hundred gets its last 1%); `--val-frac 0` with a second run into `<shelf>.val.bin` is
  how a held-out set cut elsewhere gets in (`../data/CLAUDE.md`, `shelves.py`).
- **`export.sh`**, **`export_hf.py`** — a save to HF format to a servable GGUF. `bench.sh`,
  `archtest.*` — the measurements behind her shape. `fetch_gutenberg.sh`.
- **`RUN.md`** — the first box's copy-paste runbook: prep, start, warm start, resume, export,
  serve, stop. For `day4` the runbook is `../night/day4-RUN.md`.
- **`train_test.py`** — the trainer's proof, on a toy model on the mac:
  ```bash
  cd ~/tower/forge/eva-goes-berserk/school && uv run -q --python 3.12 --with torch --with transformers --with numpy python -m unittest scratch/train_test.py
  ```
  About three minutes. It pins the old trainer by its git blob and holds the new one to it.

## What changed for `day4`

Three things, none of which moves her path when they are not used — with no weights file the new
trainer gives the same losses, the same batches and a bit-identical model, optimizer and RNG state
as the old one, and an old save resumes under it unchanged:

- **`<out>/weights.json`, read at every eval** — the only way to change a mix inside a run
  (`../night/CLAUDE.md`). The weights in force are written into `status.json` and the save.
- **Training loss per shelf**, `train_per_file` in `status.json` beside `eval_per_file` (with
  `train_rows`, the sequences behind each), the mean over the interval between the last two evals,
  on the eval log lines as a trailing `| train fantasy 2.951 …`. Held-out rising while a shelf's
  training loss falls is memorising; both drifting together is trade. `night/turn.py` reads it.
- **`--eval-iters`** was always there and never set: at its default of 20, split over fourteen
  shelves, each shelf's held-out number in `day3` is one batch of six sequences, at positions
  drawn once from seed 0 — the same six every eval. `run4.sh` passes `EVAL_ITERS`; eight batches
  a shelf is 8 × the number of shelves on the line (`../PITFALLS.md` 7.4).

**It goes to the host only after `day3` has written DONE**, with `night/run4.sh`, keeping the old
trainer beside it as the way back (`cp -p train.py train.py.day3`); the copy step with its MATCH
or MISMATCH lines is in `../night/day4-RUN.md`. What the mac cannot prove is the card: the first
thing the new trainer does on the host is the forty-step smoke test (`../PITFALLS.md` 6.2), which
is also `day4`'s baseline, mainly for memory at 15 of 16 GB.

Known and left alone: after a resume `eval_per_file` and `train_per_file` are empty until the next
eval, and the first interval is partial (`train_rows` shows how partial).
