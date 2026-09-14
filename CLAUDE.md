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

## State

Nothing built yet. Next: pick the small base for the mac off the sheet, pull it, run llama-server
on the completion route, and write the loom against it.
