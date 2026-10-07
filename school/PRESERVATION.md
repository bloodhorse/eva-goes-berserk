# preservation — what is kept, and where

Agreed with bekh on 2026-10-07, after finding old runs kept in full twice and a day's gathering
kept once. The question is not "what do we keep" but **what would it take to carry on**: the text,
the newest trainable save, and the kit. Everything else is weight.

## The ground

- **ds-dev2's disk is durable. Only its card is on loan.** `/opt/llama/magdra/` is where bins,
  runs and trainable saves live, and nothing there needs insuring against the box disappearing.
  The note "lent for days and liable to vanish" belongs to the other box, `ubuntu@10.4.65.34`
  (olmo's, and `night1`/`day2`'s), which is a different machine.
- **The mini** (`bek@100.69.218.90`) has two disks: the internal SSD (btrfs root; nothing big goes
  on it — `PITFALLS.md` 5.5b) and the external WD at `/srv/music/` (one shingled USB drive: good
  for large files and cold storage, slow under many small rewrites, and no second copy of what is
  on it). The archive is `/srv/music/school-archive/`.
- **The mac** is the tight one: `df -h /System/Volumes/Data`.

## The rule

1. **A finished run keeps its final snapshot and its log.** One `model-<step>-q8_0.gguf`, 379 MB,
   servable for ever: on the mac in `models/<run>/`, and in the archive's `models/<run>/`. The
   ledger and log are kilobytes (`night/<run>/`). By bekh's word the hourly snapshots of a run
   are not history: the guard keeps one.
2. **Trainable saves exist for two runs at most**: the run in progress and the one it started
   from, as the way back — on the training host. One copy goes to the mini when a run ends,
   against a plain disk failure. The six-hourly pull (`night/pull_ckpt.sh`) finishes out `day3`
   and is not started for `day4`. When a new run is safely under way, the save before its parent
   is deleted, on bekh's word (a remote host has no Trash).
3. **The text has two homes**, the mac and the archive on the mini. It is what a day of gathering
   costs and what nothing can rebuild: every shelf's source text, the fetchers' raw pages, the
   book files as they were downloaded, the ledgers. Nothing cleaned is thrown away; a new cut goes
   beside the old one.
4. **Token bins live on the training host only.** They are made from the text by `prep.py` in
   minutes. The mac keeps the tokenizer folders and the bins' `.json` (`models/bins/`), since the
   token counter needs them. Where a big shelf's text is not on the mac, its text is in the
   archive (`models/box/data/`, `models/box/fanfic/`, `gutenberg-cut2-20261006.tar.gz`) and on
   the host (`data/`).
5. **Derived things are never backed up**: `dedupe/state/` and `dedupe/out/`, `sieve/state/` and
   `sieve/out/`, `shelves/`. Minutes to rebuild from the text.

## The mirror

Run it after any new text lands. Three copies, then a checksum verdict for each; nothing is
deleted on the mini by it.

```bash
cd ~/tower/forge/eva-goes-berserk && M=bek@100.69.218.90 && S="ssh -o BatchMode=yes -o ConnectTimeout=10"
EX=(--exclude=__pycache__/ --exclude=.venv/ --exclude=models/ --exclude=dedupe/state/ --exclude=dedupe/out/ --exclude=sieve/state/ --exclude=sieve/out/ --exclude=shelves/ '--exclude=night/*/status.new' '--exclude=*.part')
rsync -a -e "$S" "${EX[@]}" school/ "$M:/srv/music/school-archive/"
rsync -a -e "$S" --exclude=__pycache__/ --exclude=.venv/ shelf/gpt/ "$M:/srv/music/school-archive/gpt/"
rsync -a -e "$S" ~/tower/ephemeral/booox/souls_lain_library ~/tower/ephemeral/booox/souls_lain_library_used ~/tower/ephemeral/booox/books.txt ~/tower/ephemeral/booox/books2.txt "$M:/srv/music/school-archive/books-src/"
```

```bash
v(){ n=$(rsync -a -n -c --itemize-changes -e "$S" "$@" | grep -c -v '^\.d'); [ "$n" = 0 ] && echo MATCH || echo "MISMATCH $n"; }
echo "school: $(v "${EX[@]}" school/ "$M:/srv/music/school-archive/")"
echo "gpt:    $(v --exclude=__pycache__/ --exclude=.venv/ shelf/gpt/ "$M:/srv/music/school-archive/gpt/")"
echo "books:  $(v ~/tower/ephemeral/booox/souls_lain_library ~/tower/ephemeral/booox/souls_lain_library_used "$M:/srv/music/school-archive/books-src/")"
```

It is thousands of small files over the tailnet: the first pass of a big day took most of an hour.
While a run is live, or an agent is writing in `school/`, the school line reads MISMATCH with a
dozen or so files — the run's own (`night/<run>/`), python-environment links, files converted
since the copy began. Look at the list (drop the `grep -c`) before believing either word, and run
the copy again when the writing has stopped.

`night/archive.sh` is the older script, written for the first box: it pulls from a host that is no
longer ours and mirrors `models/` and everything derived. It is not the mirror; the commands above
are.

## At the end of a run

```bash
N=day3; cd ~/tower/forge/eva-goes-berserk/school
tail -n 2 night/$N/pull.log                                                   # where the puller ran: MATCH on the final copy
ssh bek@100.69.218.90 "ls -la /srv/music/school-archive/models/$N/"            # ckpt.pt, at the size of the host's
ls -la models/$N/model-latest-q8_0.gguf && cat models/$N/latest               # the final snapshot on the mac
```

Without the puller, the one copy is a stream from the host straight to the mini, with the same
MATCH-by-size check `pull_ckpt.sh` makes (its loop body is the command). Then the final snapshot
is copied into the archive's `models/<run>/` under its own name.

What is where today is three commands, never a list in a doc:

```bash
ssh bek@100.69.218.90 'df -h / /srv/music | tail -2; du -sh /srv/music/school-archive/* | sort -h | tail -12; ls -la /srv/music/school-archive/models/*/'
ssh -o ConnectTimeout=15 -i $KEY BekmemetevVO@ds-dev2.x340.org 'cd /opt/llama/magdra && df -h . | tail -1 && du -sh * runs/* | sort -h | tail -14'
df -h /System/Volumes/Data | tail -1; du -sh ~/tower/forge/eva-goes-berserk/school/* | sort -h | tail -8
```

## Deleting

A check and the delete it guards are two commands, the first one read before the second is sent
(`PITFALLS.md` 5.8). On the mac it is `trash`, which frees nothing until the Trash is emptied. The
mini has a freedesktop Trash folder and no `trash` command; a dated `_trash-<date>/` folder on the
same disk is the house habit there, and it frees nothing either until bekh says delete for good.
ds-dev2 has neither: a delete there is for good, and is bekh's word each time.
