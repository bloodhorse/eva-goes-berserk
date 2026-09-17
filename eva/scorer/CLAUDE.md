# eva/scorer — a small picker made of bekh's marks

**A side road, not the avenue.** Agenda item 1: it eats what the work produces anyway, it
gets looked at once a month, and the first decision rides on one curve — does a tiny scorer
trained on bekh's `●`/`★` get better as it gets more marks. Rising → keep feeding it.
Flat → the features can't see what he sees, more labels won't fix it, shelve it without
grief. Nothing else in the project depends on it, and it never picks anything for him.

Not part of the loom. The loom is stdlib-only; this is an analysis tool and runs under `uv`
with numpy and scikit-learn.

## The monthly ritual

One command. It re-embeds only the cards it has never seen and rewrites the report.

```bash
uv run --python 3.12 eva/scorer/curve.py --folders experiments/three-models
```

Next month, name the new folders too — that is the whole update:

```bash
uv run --python 3.12 eva/scorer/curve.py --folders experiments/three-models nights experiments/portal
```

The servers have to be up first, or the sources whose cache is cold are skipped with a line
(a source already in the cache needs no server at all). Start them, run, kill them **by
numeric pid** — `pkill -f` kills the shell that ran it:

```bash
cd ~/.cache/llama.cpp
nohup llama-server -m nomic-embed-text-v1.5.Q8_0.gguf --host 127.0.0.1 --port 8085 \
  --embedding --pooling mean -c 2048 -ngl 0 --no-webui > /tmp/nomic.log 2>&1 & echo $! > /tmp/nomic.pid
nohup llama-server -m gpt2-xl.Q8_0.gguf --host 127.0.0.1 --port 8086 \
  --embedding --pooling last -c 1024 -ngl 0 --no-webui > /tmp/gpt2emb.log 2>&1 & echo $! > /tmp/gpt2emb.pid
kill $(cat /tmp/nomic.pid) $(cat /tmp/gpt2emb.pid)
```

Nemo's hidden state costs more: the live nemo on 8080 has no `--embeddings`, and a second
nemo does not fit in 16 GB. So it means taking the loom's model down and putting it back.
Before the bootout: no `census.py`/`berserk.py` running, no `shelf/berserk/state.json`.

```bash
launchctl bootout gui/$(id -u)/com.bekh.eva-llama
cd ~/.cache/llama.cpp && nohup llama-server -m Mistral-Nemo-Base-2407.Q5_K_M.gguf \
  --host 127.0.0.1 --port 8087 --embedding --pooling last -c 2048 -ngl 99 -fa on \
  --no-jinja --no-webui > /tmp/nemoemb.log 2>&1 & echo $! > /tmp/nemoemb.pid
uv run --python 3.12 --with numpy eva/scorer/features.py --folders <folders> --sources nemo
kill $(cat /tmp/nemoemb.pid)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bekh.eva-llama.plist
curl -s http://127.0.0.1:8080/health          # must say ok before you walk away
```

Always check 8080 last. `https://eva.x` is dead for the length of that window.

Before trusting any number: `uv run --python 3.12 eva/scorer/curve.py --selftest` — planted
signal must come out near AUC 1, random labels near 0.5. A bug that flatters us is worse
than no scorer.

## The pieces

- `features.py` — rooms in, one vector per card out. Takes **folders**, so new rooms are
  picked up by naming their folder. Two variants per card: `card` (the card alone) and
  `seedcard` (the last ~100 words of the seed, cut back to a sentence, plus the card).
  `--sanity` probes a server: same text twice must give the same vector, two texts must
  differ. Cache in `shelf/scorer/cache/<source>-<variant>.npz`, keyed by room + node id +
  a hash of the text, gitignored and rebuildable in minutes.
- `curve.py` — the experiment and the report. `--selftest` for the synthetic check.
- `blind_view.py` — prints one split: training rooms with marks, test rooms shuffled,
  unmarked, model names stripped, each card under an opaque display id.
- `score_picks.py` — opens the key on a picks file. The moment the blind comes off.
- `portrait.md`, `portrait-B.md` — what two agents wrote about bekh's taste from one half of
  the rooms, to pick blind in the other half. `picks-A.json`, `picks-B.json` are what they
  picked.

## The two marks

`●` is "i liked it". `★` is "it made me feel something" — the one that matters. The graded
target is **★ = 2, ● = 1, unmarked = 0**, and it is what the pairwise ranker trains on.

**`STAR_MEANS_MARKED` in `features.py` is the caveat that makes this honest.** `●` did not
exist when bekh read three of the ten rooms —

    experiments/three-models/07-the-green-book
    experiments/three-models/10-madmans-diary
    experiments/three-models/11-scotts-diary

— so there `★` meant "i liked it", which is **28 of the 39 stars on the shelf**. In those
rooms a star is counted as grade 1 and star-only metrics are skipped, which leaves 11 true
stars in seven rooms. That is far too few to train on or conclude from. **If bekh ever
re-reads one of those rooms with both marks, delete it from that set** — nothing else needs
changing, the math reads the config.

An unmarked card is not a card he disliked. It may be a card he never read, or one he read
and didn't press anything on. A room with no marks at all is dropped from training with a
line saying so.

## What the numbers mean

Everything is **leave-one-room-out**. Mark rates run 13%–47% by room, so a scorer tested on
a room it trained on can look brilliant by learning "this is the madman room" and nothing
about taste. For each held-out room: train on n cards drawn from the other nine (stratified
by room, 30 random draws; at n = the whole pool there is only one draw, so it runs once),
score that room's 30 cards.

- **P@k** — of the k cards the scorer would show, how many bekh marked, where k is how many
  he marked in that room. Recall at that k equals it by construction, so only one number is
  printed. Directly comparable to "of my picks, how many were his".
- **P@6** — the same at a fixed 20% budget.
- **AUC** — the whole ranking, chance 0.5.
- **★ P@k**, **★ mean rank** (1 best, chance 15.5), **NDCG** over the grades.
- **±** is the spread across rooms and draws, not a standard error. With ten rooms it is
  wide, and it is the number that decides whether anything here is real.
- **The permutation test** shuffles labels *inside each room* 200 times and runs the same
  pipeline. Whatever survives that is room structure, not taste.

Candidates are chosen by inner cross-validation on the training rooms only — never on a
test room. The family: logistic regression and a within-room pairwise ranker, each on raw
and on **room-centred** features (each room's mean vector subtracted, so the model can only
learn what separates two cards of the same fan), with and without PCA to 16/32/64.

`meta/facts` is the control: model name, temperature, card length, nothing else. If it
keeps up with the embeddings, the embeddings have learned nothing a lookup table doesn't
already know.

## Caveats that do not go away by running it again

- Ten rooms. Every "±" is over ten things.
- Two readers, one of them a model.
- Nemo wrote the seeds of six of the ten rooms — a home game, a confound built in before
  any of this.
- The instructed-reader contest is **one agent doing it once**. An anecdote, kept separate
  from the scorer's numbers on purpose.
- Agent-written portraits are contaminated by `HANDOFF.md`'s canon, which quotes cards
  bekh loved from specific rooms. The report says which split that hurts.

The reports live in `docs/scorer/`, one per run, named by the day. Everything above the
`## verdict` heading is written by the script; the verdict and the instructed-reader section
are written by hand after reading the numbers, to the project's rule — no strong claims, "so
far". A rerun on a new day writes a new file and leaves the old one standing.
