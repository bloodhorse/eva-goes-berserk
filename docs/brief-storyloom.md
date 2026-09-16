# brief: work the loom

You are running a loom against a **base model** — pretrained weights, no assistant training. It
does not answer questions and there is no chat. You hand it a document; it continues the document.
One call gives you one continuation, so you ask for many and choose.

Work from this file. Don't go looking for our notes on technique first — we want to see what you
do with the plain instrument.

## The machine

llama-server runs mistral nemo 12b base on `http://127.0.0.1:8080` (10–12 tokens a second). Rooms
are json files in `sittings/`, readable by our page at `https://eva.x`, so anything you make, bekh
can open and read.

From the repo root, `~/tower/forge/eva-goes-berserk`:

```bash
# a new room from a seed document (a file, never inline shell text — quoting eats characters)
uv run --python 3.12 docs/walk/walk.py new <room> --seed-file seed.txt --title "<title>" --predict 40

# 15 continuations of wherever the room stands, printed numbered
uv run --python 3.12 docs/walk/walk.py fan <room>

# step onto branch 8, then fan again from there
uv run --python 3.12 docs/walk/walk.py pick <room> 8

# the document so far
uv run --python 3.12 docs/walk/walk.py doc <room>
```

Wider and longer fans, and fans under a branch of an existing room, are in `docs/walk/README.md`
— the commands, not the thinking. Samplers live in each room's `params`: temperature, min_p,
top_k/top_p, xtc, dry. Change them if you have a reason; say what the reason was.

Rules that are not yours to change:

- **The words "AI", "assistant", "chatbot" never appear in a document.** They summon every chatbot
  transcript ever scraped, and the run is dead on arrival.
- Never rewrite what the model wrote. Pick it, cut it, or leave it. A line we edit gets marked.
- Don't open a room in the page while a script is writing to it; last writer wins.
- Everything is disposable. Make as many rooms as you want, name them plainly.

## What we are hunting

Not good fiction. We have plenty of that and it bores us.

We want the thing that reads like a **strange artifact** — a text that got away from whoever was
writing it. The pieces that have worked so far came out of invented documents: a parish roll of
witches in a dead-grid city, an old register of cunning folk. What made them good:

- **Witches who die, vanish, or are punished, and the record keeps its tone about it.** "Ghost-witch,
  and it was found necessary to take her head to clear the lines. A child is now raised in her
  place." "Tattlewitch, and hung her for it, but it is whispered that her bones still speak, though
  none can say what they tell." "Curious-witch. She left one night in a boat, alone."
- **Something in the lines that is not a person, and the document's odd care about it.** "Voice-witch.
  Now she is called nothing, and the voice screams alone." "Story-witch but it died when it learned
  its name." "Dream-witch. it called her sister, and knew her name before the last of its memories
  were burned."
- **The best one broke the document.** A roll entry stopped being a roll entry and spoke to whoever
  was reading: *"i can't make you believe any of this is real. i wish i could."* We don't know who
  "i" is there — the clerk, the writer, the thing in the lines — and the text doesn't say. That
  ambiguity is the prize. Something that turns around and looks at the reader.

So: strangeness that arrives sideways, a document that damages itself, a voice that shouldn't be
able to speak, unease held in a flat official tone. Not a well-made short story with a satisfying
last line.

## What to do

1. Invent your own documents. Don't reuse our witch roll; make frames of your own that could
   produce this kind of accident. Fresh frames are more likely to give fresh accidents.
2. Run fans, choose, go deeper, and keep the rooms.
3. Write back with: the rooms you made, your seeds, the passages worth reading (verbatim, with
   the room name and where in it), and how you worked — what you tried, what you changed, what
   the model kept doing that you had to push against.

Quote only what the model actually wrote. Never smooth it, never fix a typo, never merge two
branches into a nicer sentence. If a branch ends mid-word, that's how it ends.
