# handoff — read once, then delete this file

Written 2026-10-06 by the session that raised magdra's first two runs. **Disposable: read it
whole, `trash HANDOFF.md`, commit the removal, and work from `school/CLAUDE.md`, `BRIEF.md`
and the docs.** Everything durable is in those; what is only here is the state of this hour,
the job bekh set, and how the last day felt.

## 1. the job: move magdra's training to ds-dev2

bekh's last words: *we're getting the training to ds-dev2.* The box (`ubuntu@10.4.65.34`) ran
out of time; the training continues on **ds-dev2.x340.org** (`~/.claude/docs/hosts.md`: RTX
5060 Ti 16 GB, Ryzen 5 3500X, 30 GB RAM, Ubuntu 26.04, a team box with nine users, the team's
green light for LLM work from 2026-08-25, everything ours under `/opt/llama`, its own
`llama-server.service` for the work project — **that one is work's, leave it**). ds-dev2 is not
the mini and not the box: **the default host rule applies — show each command, wait for yes**,
until bekh gives a standing word for it the way he did for the box.

What has to get there, all of it on the mac already (and mirrored on the mini at
`bek@100.69.218.90:/srv/music/school-archive/`):

- the trainable save: `school/models/day2/ckpt-7896.pt` (4.3 GB, the pull may still be finishing
  when you start — check its size is 4,261,775,021 bytes, not a `.part`);
- the tokenised shelves: `school/models/bins/` (or `models/box/bins/`, same files; 2.9 GB, ten
  `.bin` + `.val.bin` + `.json`);
- the trainer: `school/scratch/` (`train.py`, `prep.py`, `export.sh`, `export_hf.py`, `RUN.md`);
  the night scripts `school/night/` (`run2.sh`, `guard.sh`, `watch.sh`, `pull_ckpt.sh`,
  `prompts.txt`, `mon.py`, `page.py`) — all written for the box's paths (`~/eva-olmo/school`,
  the box's address, its `/opt/llama/tools/hf` cli, its `status.sh` idle flag); they need ds-dev2's
  paths, address and user put in, and the guard's work-flag line dropped or replaced.

What ds-dev2 changes:

- **16 GB, not 24.** The runs used batch 12 × accum 2 at 18.9 GB. Expect batch 6 × accum 4
  compiled, about 12 GB; measure with `train.py --bench` first, as the box was measured
  (`bench.sh`). Expect 9–12k tok/s. If it does not fit, `--ctx 512` halves the activations.
- **A venv must be built there**: torch for a Blackwell card (sm_120 — the box's `.venv-train` had
  torch 2.14+cu130; check what pip offers for Ubuntu 26.04), transformers, numpy; the `gguf`
  package and a llama.cpp checkout for `convert_hf_to_gguf.py` (ds-dev2's `/opt/llama` probably has
  one — look, don't assume). 30 GB of RAM is enough; the bins are memory-mapped.
- **Disk**: unknown; `df -h` first. Shelves 2.9 GB + checkpoint 4.3 GB + a run's growth
  (ckpt.pt 4.3 GB, hourly 380 MB snapshots) — plan 20 GB.
- **The recipe**: `night/run2.sh`'s `--data` list and weights are the agreed mix (fantasy 2000,
  sci-fi 1500, light novels 2100, fan fiction 1400, base 2200, net core 200, net bulk 400, the
  six 50, lain 25, cyborg 10) and `--init` the latest save with `--lr 8e-5 --warmup 300` —
  **not** 2e-4; that knocked her back (day2's first attempt). Set `--hours` to the real window;
  teenage is about two billion more tokens, two to three days at that card's speed.
- The watcher and the page: `watch.sh` builds the sheets page on the mini and pulls snapshots;
  it needs the new host in its `scp`/`ssh` lines. The terminal monitor `mon.py` has the box's
  address as `BOX`.

Say the plan back to bekh with the measured speed and the fitted batch before starting; he said
yes to the mix already, not to a run on a machine he has not seen numbers for.

## 2. how things are left

- **The box**: card at 0 MiB, nothing of ours running. `~/eva-olmo/` is 228 GB and still there
  (shelves, text, runs, the small models, llama 70B, olmo's gguf and banks, the painter is
  `~/eva-paint`). Deepseek's weights are gone (bekh's word). If the box is reclaimed, nothing
  there is unique: the archive has the shelves, text and saves; the big ggufs are re-downloadable.
  Leaving properly is `docs/olmo.md`, the box: copy off, `box_serve.sh down`, and bekh decides
  about `rm -rf ~/eva-olmo`.
- **The mac**: serves `school/models/day2/model-7896-q8_0.gguf` on `127.0.0.1:8086`
  (`llama-server`, started by hand, not launchd — gone after a reboot) and the loom's job points at
  8086, so `eva.x` fans on magdra. Nemo's own address 8080 answers nothing (he is off the box's
  card and the mac's job is not loaded); `eva go` would start the mac's nemo. The gpt-2, olmo and
  llama tunnel jobs may still be loaded (`launchctl list | grep eva`); harmless, they just fail.
- **Background on the mac when this was written**: the final pull of `ckpt-7896.pt` and then
  `night/archive.sh` (`/tmp/school-final-pull.log`; `school/night/archive.log` ends with
  `PULL-DONE` when both are through).
- **The mini**: `/srv/music/school-archive/` is a mirror of `school/` as of 09:48 UTC plus whatever
  the final archive run added; 94 GB free on that disk; the mini's root is nearly full (5.7 GB),
  never put anything there.
- **Git**: everything committed and pushed through the wrap; `.claude/settings.json` (untracked)
  holds `worktree.bgIsolation: none` so this session could write in the main checkout — the
  harness otherwise forced a separate copy, which bekh refused.

## 3. bekh, this day

- He reads her raw page samples and finds them deflating — *grammar, no feeling, no thread* — and
  he is right for her size; **read her through the loom's sampler before judging**, and don't
  oversell her: nemo is the poet, she is the one we can open.
- Renting is **out of the question for now**. ds-dev2 is free iron; a 5060 Ti of his own was
  weighed (the stream around the clock on our own iron is the argument for it).
- **Text is the accumulated knowledge**: nothing cleaned or tokenised is deleted; the archive is
  the rule. Erotica stays; nothing sexual involving minors goes in (the fan-fiction rule is blunt
  on purpose).
- He wants the twenty-minute watch when a run is on (`ScheduleWakeup`-style checks; the one that
  caught the bad learning rate was his question, not a monitor). He accepted a restart made
  without asking when the clock was running, and offered to be asked first — not answered.
- The six-small-models sheet (`small-first.html`) is still unread by him; the key is
  `docs/small/first-sheet.key`.
- He dictates: "car/card", "Almo" olmo, "cyber decent" cyborgism, "Eichmann" Aickman, "Mjövel"
  Miéville, "Tinux" tmux, "motor" model, "spin the topes out" spin the opus out.

## 4. things that bit, so you skip them

- The clock is not in your head: hours pass between his messages; read the run before speaking
  of it. Two bad statements this day came from assuming no time had passed.
- Temperature-1 samples with no cut-off are the worst view of a small model; the page shows them
  and bekh judged her by them.
- `prep.py` skips nested directories silently — flatten first. The `sedthh` Gutenberg dump has a
  blank line after every text line. Gutenberg image lines (`18-199.jpg (87K)`) leak through
  `cut.py` and showed up in her writing — drop them in the next cut.
- Agents could not write `.md` reports into the shared checkout; they returned the text and it
  was saved by hand. Spawn with `isolation: "worktree"` or keep the settings override.
- A trainer stopped with SIGTERM makes the wrapper exit and the guard shut down, which makes the
  watcher and the puller stop too; to change prompts or rate mid-run, stop everything, rotate the
  guard log, relaunch all five (`school/CLAUDE.md`, watching and running).
- zsh: `$B:path` is a modifier, write `"${B}:path"`. The local Bash tool refused a command that
  used `/tmp` and `rm -rf` together; use a folder inside `school/` and `trash`.
