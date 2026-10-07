# night — running a run

Everything about a training run while it is alive: the five processes, the page, the look, the
detector, how to change a mix without stopping, how to stop, what happens at the end. The recipe of
a run is not here (`../day4.md`), nor the kit's insides (`../scratch/CLAUDE.md`), nor what is kept
afterwards (`../PRESERVATION.md`). What bit while running is `../PITFALLS.md` 5–7; read 7 before
the first look of a session.

## Looking

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run --python 3.12 night/mon.py <run>          # terminal monitor: probe, heartbeat, moving (--once for one reading)
open https://miniarch.tail004a72.ts.net:8446/school-<run>.html                               # the page, rebuilt every 2 min while the mac is awake
uv run -q --python 3.12 python night/turn.py <run>                                           # the verdict per shelf
```

**Where she is right now is one of those three, never a sentence in a doc.** Every status she has
written is `night/<run>/ledger.jsonl`; the page's sparklines are that file. The speed and `eta` in
`status.json` are a fifty-step window; the truth is the `elapsed` deltas of the log, and an end
time is now plus the newest log line's `eta`, worked out each time it is said (`PITFALLS.md` 7.4b).

## The five processes

Three on the training host, two on the mac. The mac's scripts and `mon.py` find the host through
`BOX` (default `BekmemetevVO@ds-dev2.x340.org`), `BOXDIR` (default `/opt/llama/magdra`) and `KEY`.

- **`run3.sh <name>`** / **`run4.sh <run> [init.pt] [hours]`** (host) — the trainer in a restart
  loop: it resumes from `runs/<name>/ckpt.pt`, stops on DONE or on a deliberate STOPPED, pushes
  silently at start and end. `run3.sh` is `day3` as it ran (batch 6 × 4, 8e-5, `--init
  ckpt-7896.pt`, the mix and fifty hours written in the file); `day4` runs under `run4.sh`. `run4.sh` is the same loop with
  nothing hard-coded: the mix from `MIX`, else `MIXFILE`, else `night/<run>/mix.txt`, else
  `runs/<run>/mix.txt` (one `bin:weight` a line); `STEPS=` or hours; `LR`, `WARMUP`, `BATCH`,
  `ACCUM`, `EVAL_EVERY`, `EVAL_ITERS`, `LOG_EVERY`, `CKPT_MINUTES` as environment overrides with
  `run3.sh`'s values as defaults; `DRY=1` prints the start and resume commands and starts nothing.
  It refuses to start on a missing mix, bin, init or budget, where `run3.sh` would burn thirty
  restarts and push "gave up". `night/<run>/` is not in git, so a mix kept only in `mix.txt` is
  not either: the tracked copy of a run's mix is its recipe doc. `run.sh` and `run2.sh` are
  `night1` and `day2` as they ran on the first box.
- **`guard.sh <name>`** (host) — pauses the trainer above 88 °C until 75 °C, exports a servable
  snapshot (`model-<step>-q8_0.gguf`) every hour and **keeps only the newest**, skips snapshots
  under 20 GB free, writes `guard down` when the trainer is gone.
- **`watch.sh <name>`** (mac, under `caffeinate`) — every two minutes: pulls status, samples and
  guard log, builds the page with `page.py`, posts it to the mini's sheets folder, then keeps the
  newest snapshot as `models/<name>/model-latest-q8_0.gguf` (its name in `models/<name>/latest`).
  Ends on `guard down`. It is a long-lived bash loop: never edit the file while it runs.
- **`pull_ckpt.sh <name>`** (mac) — every six hours (`EVERY=` seconds) streams the trainable
  `ckpt.pt` from the host straight to the mini's archive, never touching the mac's disk, and
  writes MATCH or MISMATCH by size to `night/<name>/pull.log`; once more at the end. It ran for
  `day3`; from `day4` on it is not started, so a run is four processes, and the end-of-run copy
  is made by hand (`../PRESERVATION.md`).

The mac's half needs the mac: awake, on the VPN, `KEY` in the environment the scripts were started
from. When it sleeps the page goes stale while the run is fine.

## The page — `page.py`

One self-contained page per run (markdown through pandoc), in the house palette — mint good, pink
fail, light blue context. Top to bottom: her age in tokens with a life bar; the stat cards; one
row per shelf with a sparkline, first and newest held-out loss, the last move and the detector's
verdict; **"the last thing she said"**; **"through the loom's sampler"** — the seeds of
`prompts.txt` drawn once each from the newest snapshot with min_p 0.08 and a repetition brake
(`loomed()` runs `/opt/homebrew/bin/llama-completion` on the mac when `models/<run>/latest`
changes and keeps the draws in `night/<run>/loomed.jsonl`), with the recitation meter beside
them; the trainer's own raw draws (temperature 1, no cut-off: her worst face); the guard log.
**Judge her from the sampled draws, never the raw ones**, and do not oversell her either.

**It follows the device's light or dark scheme**, with no toggle and no script: every colour is a
CSS variable declared at the top of the style block, once for dark and once under
`prefers-color-scheme: light`, and SVG marks take `currentColor`. A new element uses those
variables and never a literal colour. Dark is the original page, unchanged to the pixel; the light
palette is warm paper with a dusty mint (`#37796a`) and a dusty rose (`#a8556f`) — bekh threw out
a forest green and a magenta on sight, so a palette change is shown to him as a screenshot before
it is called done (`PITFALLS.md` 8). The `theme-color` metas land in the body because `watch.sh`
passes pandoc its own `header-includes`; the scheme itself is set in CSS and works.

**The watcher runs this file every two minutes for a live run.** Change it on a copy, build from
the real `night/<run>/` inputs to a temp path, replace the file only when that exits clean, then
run it once the way `watch.sh` does (`uv run -q --python 3.12 python night/page.py <run> >
/tmp/x.md`) and look at the exit status and the size.

## The recitation meter — `meter.py`

"Does she talk like it or quote it." When a snapshot's draws are new, `page.py` calls
`night/meter.py <run>` (130 s timeout), which sends each draw, seed and continuation together,
through `dedupe.py lookup` and counts only her words. It writes `night/<run>/meter.jsonl`, one
record per draw (snapshot, kind `loom` or `raw`, seed). The page shows the share of her words
inside verbatim runs of eight or more words and of twelve or more, the raw draws' share, a
sparkline of the eight-word share over snapshots, and under each draw any run of twelve or more
words with its source; shorter stock phrases are counted and not listed. About four seconds per
new snapshot, nothing on other cycles. On any error or timeout the page renders without the meter,
leaves `night/<run>/meter.err` and tries again after twenty minutes.

What it is checked against is the dedupe's index: every shelf of modern prose, the new pile, and
the old fantasy, plain-fiction and net-list text (`../dedupe/CLAUDE.md`, the three kinds of root).
**What it cannot see**: the light novels, the fan fiction and most of the pulp sci-fi, whose text
is not on the mac — a clean score clears her against the rest only, and the page says so. The
eight-word share is noisy (a snapshot is about 540 of her words) and is mostly stock phrases; the
twelve-word runs are the reading. It reads output; the detector reads loss. A model can pass one
and fail the other, and from `day4` on, where new fiction is read more than twice, this is the
gauge for how far the reads can be pushed.

## The detector — `turn.py`

`turn.py <run>` reads the ledger and, per shelf, compares the last three held-out evals with the
three before against the shelf's own swing (1.5 × its median eval-to-eval move, floor 0.004):
`learning`, `flat`, `rising`, `turned` (rising twice over).

- **Exit 0** nothing turned; **exit 2** a shelf reads turned on this eval only; **exit 3** a turn
  **confirmed** — turned on this eval and on the one before.
- `--json` for the page (keys are only ever added); `--ledger PATH` for another file.
- When the ledger carries `train_per_file` (the new trainer), each shelf also gets its **gap**,
  held-out minus training loss, and the gap's trend over the same windows: a turn with a widening
  gap reads `memorising`, a turn with a flat gap `drift or noise`. A hint to read the first gaps
  of `day4` by, and no more than a hint (forty steps of the smoke test, a few rows a shelf): on
  the small shelves `day3` read hardest — Strange Horizons, the released authors, the net core,
  each about one and a half times by its stop — training loss sat about half a point under
  held-out before `day4` had taught her anything, so those gaps start wide and it is their widening that would mean something.
- `--weights` prints, and does not write, the `weights.json` that would zero the confirmed shelves,
  with the one command that puts it on the host.

A `turned` is a reason to look, never by itself a reason to act: a human or the session decides.
In `day3` the verdicts were blunt for a reason that is not the detector's — each shelf was graded
on six fixed sequences (`PITFALLS.md` 7.4); from `day4` it is forty-eight — and "confirmed" only
filters a spike the next reading undoes, since the windows are three evals wide. It says nothing
until a run has six evals.

## Changing the mix inside a run — `weights.json`

**A resume takes every setting from the save and ignores the command line, the `--data` weights
included.** Stopping and relaunching with another mix changes nothing; only the prompts file is
read again at a start. With the new trainer (`../scratch/CLAUDE.md`; it runs from `day4`, not in
`day3`) the one lever is a file: at every eval the trainer reads `runs/<run>/weights.json`, a map
of shelf name to weight. Named shelves take the new weight (0 = no longer drawn, still evaluated),
the rest keep theirs; a bad file is ignored with one `MIX … ignored` line and the mix stays; a
change is logged once (`MIX step=N fantasy 409->0`) and written into `status.json` and the save.
Removing the file changes nothing — it is a command, the state lives in the trainer; to go back,
write the old weight.

```bash
cd ~/tower/forge/eva-goes-berserk/school && uv run -q --python 3.12 python night/turn.py <run> --weights
```

## The hourly look

bekh wants a run looked at on a clock. It is a session cron and dies with the session; a fresh
session re-arms it at twelve past the hour (`12 * * * *`; why hourly and why that minute is
`PITFALLS.md` 7.7) with this prompt, the run's name changed as needed:

> Check magdra's day4 run (read school/night/CLAUDE.md and school/PITFALLS.md section 7 once if
> you have not this session). day4 started 2026-10-07 about 15:25 UTC from day3's save at step
> 33509, 16,215 steps, 8e-5, new trainer, evals every 500 steps on 48 windows per shelf. On
> ds-dev2 (ssh -o ConnectTimeout=15 -i $KEY BekmemetevVO@ds-dev2.x340.org, read-only, inside
> /opt/llama/magdra): runs/day4/status.json (step, total_steps, tok_per_s, eval_per_file,
> train_per_file, weights, heartbeat age from its unix field), the last two lines of runs/day4.log
> (and any MIX line), the tail of runs/day4.guard.log, nvidia-smi memory and temperature, df free,
> and whether train.py, run4.sh and guard.sh are alive. On the mac: age of
> school/night/day4/status.json, tail of school/night/day4/watch.err, that night/watch.sh day4 is
> still running (there is no puller for day4), and the newest meter line on the page
> (school/night/day4/meter.jsonl: share of her words in lifted runs of 12+). Run the turn
> detector: cd ~/tower/forge/eva-goes-berserk/school && uv run -q --python 3.12 python
> night/turn.py day4 (exit 2: a shelf reads turned on this eval only; exit 3: a turn confirmed on
> two evals running; it needs six evals before it says anything). The baseline at step 40 of the
> smoke test was: fantasy 3.153 scifi 3.085 anime 2.383 fanfic 3.043 base 3.053 wired-core 4.102
> wired-bulk 3.826 literary 3.036 horizons 3.368 released 3.558 library 3.283 lain 2.959
> horizons-verse 4.015 modern 3.143 anth 3.270 serials 3.048 verse2 4.138. Report to bekh in at
> most six short lines: alive or not, step and percent, speed from the log's elapsed deltas, how
> the NEW shelves moved (modern, anth, serials, verse2) against the baseline and the previous
> check, which old shelves are rising (expected: fanfic at weight 0, anime, base, scifi drifting
> up is the plan; say how much), the train-minus-held-out gap for modern and anth and whether it
> is widening, the detector's verdicts, the meter, anything odd. Push to ntfy.sh/kk_alert
> (Priority high) only if something is wrong: trainer or guard dead, heartbeat older than five
> minutes, a snapshot failed, the detector exits 3 for modern or anth or library (once per shelf),
> any 12+ word lifted run on the meter, the overall or modern held-out loss above its baseline by
> more than 0.15 after step 2000, disk under 30 GB, card memory at the limit, or the work
> llama-server active again. An old shelf rising is the plan and is reported in chat, not pushed.
> Never restart, stop or change anything on ds-dev2 without bekh's word, including weights.json;
> if the run is dead, say what the log shows and wait. When status says the run is done, report
> the final numbers per shelf against the baseline, push once at default priority, and end the
> loop.

For another run: its name in place of `day4`, its own start line and baseline, `run3.sh` and
`night/pull_ckpt.sh` back in the lists if it is an old-kit run with a puller, and its own idea of
which shelves are expected to rise.

## Sitting with her on the loom

`eva.x` fans on whatever `llama-server` on the mac's port 8086 loaded when it started; it loads a
file once. bekh does not want it restarted at every snapshot, so it serves the hour it was last
started on until someone runs this:

```bash
cd ~/tower/forge/eva-goes-berserk/school && kill $(lsof -tnP -iTCP:8086 -sTCP:LISTEN) ; \
  (nohup llama-server -m models/day3/model-latest-q8_0.gguf -c 1024 -ngl 99 --host 127.0.0.1 --port 8086 --no-jinja > night/day3/serve.out 2>&1 < /dev/null &)
```

Which hour it is serving is the snapshot's mtime against the server's start time
(`ps -o lstart= -p $(lsof -tnP -iTCP:8086 -sTCP:LISTEN)`). A walk on her is the walk scripts with
`LOOM_LLAMA=http://127.0.0.1:8086` (`eva/cli/walk/README.md`); her first, `experiments/magdra-prophecy`
and its cut, was made at step 911. A snapshot exported on ds-dev2 sets `add_bos_token` and one
from the first box did not, so fans from the two are not the same experiment (`PITFALLS.md` 6.3).

## Stopping, and starting again

SIGTERM to the trainer makes it save and exit; the wrapper exits with it, the guard sees that,
takes a last snapshot and writes `guard down`, and the watcher ends on that line. Two things the
chain does not do by itself: the puller sleeps six hours and never sees `guard down`, so the mac's
watcher and puller are killed by pid; and the mac's own copy `night/<name>/guard.log` still says
`guard down`, so it is moved aside, with the host's `runs/<name>.guard.log`, before all five start
again. A stop and a start is for new seeds in `prompts.txt` (read only at start) or for the
machine; it does not change a mix (above). Done once, at step 911 of `day3`: a minute, and the
resume kept the plan (`RESUME from … step=911 total=84103`).

## When a run ends

The trainer writes DONE and pushes; the guard takes a last snapshot and writes `guard down`; the
watcher builds the page, pulls that snapshot and stops. **The page is built before the pull**, so
the final snapshot is never drawn or metered by the watcher: run `page.py <run>` once by hand
after it stops, then post the page. The puller, where it runs, makes one last copy
(`night/<run>/pull.log` says MATCH). Then `../PRESERVATION.md`: one trainable copy to the mini,
the final snapshot kept on the mac, the run before last's trainable save deleted. Then bekh reads
her and marks; whether the work project's `llama-server` goes back on is his and the team's call.

## The runs so far

What any run is doing is `mon.py`, never a sentence here; this is what each was.

- **`night1`** (2026-10-05, ten hours, the first box): from random weights, 659 M tokens, four
  shelves (fantasy, sci-fi, anime, bekh's six books), 18.6k tok/s. Final held-out: fantasy 3.37,
  sci-fi 3.32, anime 2.35, the six 2.95, all still falling. An infant: sentence shapes, dialogue
  that turns, fused words; through the sampler, whole sentences and already a wrong thing said
  straight (*"it was lighted by no lamps. It was pitch darkness. It was all very dark, but not
  very dark."*). Last snapshot `model-26800`.
- **`day2`** (2026-10-06, stopped by bekh when the first box's time ran out): warm start from
  night1's end on ten shelves. The first attempt at 2e-4 knocked every held-out number up a
  quarter point; the second at 8e-5 recovered half the knock in twenty-five minutes and was
  stopped at step 7,896 of 26,946. About 0.95 billion tokens read in her life at that point. Last
  snapshot `model-7896`; its trainable save `ckpt-7896.pt` is what `day3` started from.
- **`day3`** (ds-dev2, 2026-10-06 19:22 UTC to 2026-10-07 15:15 UTC, stopped by decision): warm
  start from `ckpt-7896.pt` at 8e-5 with 300 warm-up steps, batch 6 × accum 4 (24,576 tokens a
  step; batch 8 benches and dies at the first eval), fourteen shelves at the weights in
  `run3.sh`, planned as fifty hours, 84,103 steps and 2.07 billion tokens, about 11.8k tok/s,
  15.0 of the card's 16.3 GB. Stopped once at step 911 to add three one-line seeds, and for good
  at step 33,509 — 823.5 million tokens, about 1.77 billion in her life — with its overall
  held-out number at 3.253 on its own ruler of six windows a shelf. Why it was stopped: from
  about step 30,000 twelve of thirteen shelves read `flat` and the overall number moved in
  thousandths; the thirty hours left would have fed her the diet `day4` abandons; a stop writes
  a save that resumes; and it freed the card. The detector called fantasy `turned` once, at step
  25,000, and the next eval took it back. Its numbers per shelf were readings on six fixed
  windows and several were off by tenths (the light novels read "under 2" there and 2.38 on
  forty-eight windows; the net core 3.6–3.7 there and 4.1): `day4`'s baseline in `../day4.md` is
  where she really stood. Last snapshot `model-33509`; its save is `ckpt-day3-final.pt` on the
  host and in the mini's archive, and `runs/day3/ckpt.pt` holds the same bytes, which is where a
  resume of `day3` itself would start from.
- **`day4`** (ds-dev2, started 2026-10-07 about 15:25 UTC): warm start from `ckpt-day3-final.pt`
  at 8e-5 with 300 warm-up steps — a small step up from the 5.6e-5 she was living at — batch
  6 × accum 4, 16,215 steps, 398.5 million tokens, about ten hours. Nineteen shelves on the line
  (`../day4.md`, the mix; on the host `runs/day4/mix.txt`): new fiction a little over half at two
  and a half reads, fan fiction and the rough anthologies at zero, the other old shelves cut
  small. The first run on the new trainer (`weights.json`, training loss per shelf) and under
  `run4.sh`, with evals every 500 steps on forty-eight windows a shelf. No puller. The old kit
  is `kit-before-day4/` on the host.

## The machines

- **ds-dev2** (`~/.claude/docs/hosts.md`): a team box — RTX 5060 Ti 16 GB, Ryzen 5 3500X, 30 GB
  RAM, Ubuntu 26.04. **Its disk is durable; only the card is on loan to us.** Ours is
  `/opt/llama/magdra/`, the kit flat in it: `bins/` the shelves as the first box tokenised them,
  `bins2/` the re-cut and new ones (`<name>.bin`, `.val.bin`, `.json`, `.tokenizer/`), `data/` the
  text and the Gutenberg source, `.venv` python 3.12 through uv with torch 2.14.1+cu130,
  `runs/<name>/` (`ckpt.pt` trainable, `status.json` heartbeat, `samples.jsonl`, the newest
  `model-<step>-q8_0.gguf`), `kit-before-20261006/` the kit as it came from the first box. bekh's
  yes (2026-10-06) covers the venv, work inside `/opt/llama/magdra/`, and the stop of the work
  project's `llama-server.service`; anything else on that host is shown and asked first. That
  service is *enabled*: `sudo systemctl start llama-server.service` brings it back, and so does a
  reboot, which would take the card from a run (`PITFALLS.md` 5.1).
- **The first box** (`ubuntu@10.4.65.34`, an RTX PRO 4000 Blackwell 24 GB; `docs/olmo.md`): the
  one that was lent for days and can vanish. `night1` and `day2` ran there under
  `~/eva-olmo/school/`, same layout; `../scratch/RUN.md` is its copy-paste runbook. Measured on
  it, context 1024, compiled: 30 M parameters 101k tok/s, 124 M 43k (14.6 GB), 355 M 18.9k at
  batch 16 (21 GB); the runs there used batch 12 × 2 at 18.6k and 18.9 GB.
- **What she costs to grow up.** About 20 tokens per parameter is adult (7 B); teenage for her is
  2.5–3 B. That rule counts any tokens: it says how much she has eaten, not what she has become,
  and thirty more hours of fan fiction would have crossed the line without changing how she
  writes. She was about 1.77 B when `day3` stopped and is about 2.17 B after `day4`; read her,
  not her age. The first box did 19k tok/s (0.67 B in ten hours), ds-dev2 does 11.8k; a rented 4090
  roughly twice the first box for ~$0.40/h, one H100 four to five times for ~$2.50/h. Renting is
  out of the question for now.

## Files here

`prompts.txt` — the seeds (four paragraphs: a late train, the firekeepers' bell, the forum girl,
the figment's line; three one-liners since step 911 of `day3`). `fans/` — fans drawn through the
loom's sampler by hand. `day4-RUN.md` — the runbook `day4` was started from: upload, tokenise,
start, stop, rollback, every check a MATCH or a MISMATCH; the shape to copy for the next run. `archive.sh` — the first box's mirror script, from
before the pile; it copies `models/` and everything derived, so it is not the mirror any more
(`../PRESERVATION.md` has the one that is). A run's pulled files land in `night/<name>/`, not in
git: `status.json`, `ledger.jsonl`, `samples.jsonl`, `guard.log`, `loomed.jsonl`, `meter.jsonl`,
`page.md`, `school-<name>.html`, `pull.log`, `watch.err`.
