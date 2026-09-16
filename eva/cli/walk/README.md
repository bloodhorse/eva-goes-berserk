# walk — the loom from the terminal

The page is bekh's hand on the loom. These scripts are a second hand: Claude (or bekh, from a
shell) seeding a room, drawing short fans, picking, forking a room at a branch worth chasing,
and fanning wide under it. They were born in the 2026-09-16 night session (the witch rolls,
"i can't make you believe", the carrier) and moved here so the procedure outlives a scratchpad.

All four talk to llama through `loom.complete` directly and write through `loom.write_sitting`
— the same file format the page and eva read, so every room they make opens at `https://eva.x`.
They bypass the live loom, which means **the page must not have the room open while a script
writes to it**: the page saves the whole tree on every move and the last writer wins.

Run from the repo root.

## The walk: seed → short fan → pick → repeat

```bash
uv run --python 3.12 eva/cli/walk/walk.py new carrier --seed-file seed.txt --title "the carrier" --predict 30
uv run --python 3.12 eva/cli/walk/walk.py fan carrier          # 15 branches, printed numbered
uv run --python 3.12 eva/cli/walk/walk.py pick carrier 8       # step onto branch 8
uv run --python 3.12 eva/cli/walk/walk.py doc carrier          # the document so far
```

The seed is a file, never inline shell text (quoting eats characters). The room is bare, so no
header, no names, no stop strings. Each fan is 15 branches of `--predict` tokens (30–40) at
temperatures stepped 1.4 → 2.4, with xtc on (0.5 / 0.1). Refused branches stay in the tree.
Two to five picks makes a short piece; the bits of curation are picks × log2(15), about 3.9 bits a pick.

**Why short and why xtc.** A base model locks into a genre as a branch grows: the first tokens
are forks, and by token ~100 the genre (fanfic author's note, wiki footer, forum post) has
usually won and every next word is near-certain. A pick every 30–40 tokens steers at the forks.
xtc, when several tokens are all plausible, removes the most likely of them — it refuses the
cliché where temperature only wobbles everything. In the first walk, 60 branches under these
settings produced no web-page furniture at all. The document matters more than the sampler,
though: no brackets, no `//` headers, no @handles, no markdown in a seed — each is a road sign
to the web.

## Fork a room at a branch, optionally cut

```bash
uv run --python 3.12 eva/cli/walk/fork.py chrome-roll i-wish-i-could \
    --phrase "i can't make you believe any of this is real. i wish i could." --cut --title "i wish i could"
```

A whole copy standing on the branch whose text holds `--phrase` (a child of the root unless
`--anywhere`), so its siblings stay one ‹ › away in the fork. `--cut` trims the branch right after
the phrase and marks it **posed**. The source room is hashed before and after; an existing
destination is refused.

What a cut taught us: `i-cant-make-you-believe` kept nemo's own tail `> > > > > > > [`, and 20 of
20 continuations closed that bracket as a web page (`[WIP]`, `[author's note]`, a Creative Commons
footer). Cut to end on the confession, 13 of 40 ended the document there and the rest stayed
first person inside the world. One trailing character chose the corpus.

## Fan wide under a branch

```bash
uv run --python 3.12 eva/cli/walk/fan_under.py i-wish-i-could --phrase "i wish i could." --n 40 --predict 160
```

For a room that already has a tree (census.py only makes new rooms). The target is found by
phrase, not by where the room stands, so clicking around in the page doesn't move it. Token
probabilities are kept on each branch.

## Read a naming fan

```bash
uv run --python 3.12 eva/cli/walk/names.py chrome-roll --word witch
```

For documents that end on a name slot ("…the parish called her the"): each branch is cut at
the first `--word`, sorted by how often the name came up. The distinct count is the measure of
how much the frame broke the model's default. Naming the witch after the object she worked with
(the brass head) gave 11 names in 40; naming the example witches after what they did to the
world gave 20 in 27, and 31 in 40 once the heat went to 1.8–3.0.
