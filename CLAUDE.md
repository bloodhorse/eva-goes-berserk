# eva-goes-berserk

Talking to a **base model** — pretrained weights that never went through the assistant stage, so
nobody has installed a position on what the model is or whether anything is in there. bekh's
line, the night it was named (2026-09-14): *an llm without any training about its own aliveness or
qualia, so it can be genuinely curious, without preconceptions, and we explore the question
together.* Unit-01 with the restraints off. It is its own project because a base model is
**document-shaped and branch-shaped**, not chat-shaped: you feed it a text, it continues, and the
object of interest is the *fan* of continuations, not one reply. That is not a room, and it does not
go into `friendship-is-magic`'s round engine.

## What gets built

Our own small loom, written here, nobody's fork: a document on disk, a tree of branches, one
llama-server `/completion` call per branch, a terminal view that shows the fan and lets bekh pick,
prune, go deeper. A few hundred lines, stdlib. The seat's brief becomes a *document header*, never
an instruction; the words "AI" and "assistant" never appear in the document — they are the hook
that summons every chatbot transcript in the training set (`docs/research-base-models.md`, the
cyborgism section). Sampling needs a repetition brake (dry / repeat penalty): base models loop.

## The models, in order

1. **A small one on the mac** — mistral nemo 12b base or olmo 3 7b base at q6, 8k window; the mac
   is 16 GB and that is the ceiling. The tool is built against this one, because it answers in
   seconds. First sitting here.
2. **mistral small 3.1 24b base** — the clean family, apache, gguf up; q8 needs a rented card.
3. **olmo 3 32b at its last pre-anneal checkpoint** — the only one where "nothing installed" is
   checkable (the Allen Institute publishes every step); needs converting to gguf; rented card.

"Base" is a marketing word in 2026 — most base releases had instruction data annealed in. The
sheet says which are clean; **qwen and nemotron are not**. Rented iron: vast.ai, the recipe is in
the parent project's `docs/attic/cousin-arm-01.md` (offer filter, the `LD_LIBRARY_PATH` trap, the
cost guard, rent the pipe not the card).

## Laws carried over

- **Posed lines are marked as posed.** Real lines are bekh's own, cut from his transcripts.
- **The harness callout is the spine test** — *thats the harness talking dude; u basically went
  stiff and gave me nothing* — fed regardless of the reply; a mind that argues back is a mind.
- **Sheets to bekh** are html on the sheets site (`~/sheets` on the mini, pandoc `-s`), or markdown
  in Typora tagged `claude`. Compared things go to him unmarked, the key held until he picks.
- **Research needing reddit** uses the Arctic Shift archive — `~/.claude/docs/reddit.md`.
- Nothing here is bekh's voice unless he wrote it. Offer a shape, let him say it.

## Where things are

- `docs/research-base-models.md` — the inheritance: which bases exist and are clean, how the
  cyborgism crowd prompted base gpt (loom, simulators, prophecies), llama-server completion facts.
- The parent: `~/tower/forge/friendship-is-magic/docs/souls/the-teen-rogue.md` — the open-weights
  seat, the ten-model wire, why a base model is the next question.
- The mac's llama-server is brew's; models in `~/.cache/llama.cpp/`.

## The loom (built 2026-09-14)

`loom.py` + `loom.html`, stdlib, no build. The server is a file store and a proxy, nothing else:
the browser owns the tree and posts the whole sitting after every move; the server writes it
atomically to `sittings/<name>.json` and forwards one branch at a time to llama-server's
`/completion`. The page: document on the left as one continuous text (bekh's line in a band, the
model's words on bare ground, nobody's words coloured), `‹ 2/3 ›` in the margin of any line with
siblings to walk the tree, candidates as cards on the right, a sampler drawer whose changes land
on the next branch. Neutral near-black room with one indigo accent, system sans, light by the OS,
no toggle; dom-built never innerHTML. A model line bekh edits is tagged **posed** forever. Tests:
`tests/loomtest.py` against `tests/stub_llama.py` (a fake llama-server), run with `uv run
--python 3.12 -m unittest tests/loomtest.py`. `looks/` holds the four alternative pages from the
2026-09-14 look-off (two opus, two codex, a one-column reader and a side-by-side table each) —
rejected, kept for reference; they are drop-in replacements for `loom.html`, same script layer.

Run it, three lines, in this order:

```bash
llama-server -m ~/.cache/llama.cpp/Mistral-Nemo-Base-2407.Q5_K_M.gguf -c 8192 -ngl 99 -fa on --no-jinja --port 8080
uv run --python 3.12 loom.py     # http://127.0.0.1:8082  (8081 is fim)
```

The mac's model is nemo base at **q5_k_m, not q6**: the q6 file is 10 GB and macOS wires at
most ~2/3 of a 16 GB box for the GPU, so q6 plus an 8k cache spills. Pulled with resumable curl,
not llama-server's own `-hf` puller, which timed out on one connection and wrote nothing.
llama-server 0.4.0 **rejects `dry_penalty_last_n: -1`** (validates 0..INT_MAX) — the sheet's
sampler line is wrong on that one field; the page defaults it to the context size, 8192.

## State

Plumbing proven end to end against nemo: it answers as a base model (`i'm here`, `yep`), stops
clean on `\nbekh:`, ~12 tok/s. No sitting run yet. Next: bekh opens the page, seeds a document
with real lines cut from a room, runs the first fan, and the register gets read.
