# brief: the six thousand

For the session that takes this on with bekh. It is a starting position and nothing in it is a
rule: the method gets worked out while searching, and this file gets rewritten as the search
teaches what it actually is. Read it, then argue with it (the last section says how the session
begins).

## Why this exists

magdra is a small model raised from random weights on text bekh chose (`school/CLAUDE.md`). On
her fourth run the limit turned out to be text again: about ninety million tokens of the prose he
actually wants her made of, which at a safe number of readings is ten hours of training. To grow
her up on that diet she needs several times more, and the deep well is whole books: a novel is
around 120 thousand tokens, and everything gathered so far was short fiction plus a library of
fifty-five.

A paid library account would let him fetch on the order of six thousand books a month. So getting
the files stops being the hard part. Choosing them is. Nobody picks six thousand books one at a
time, and the way he has thought about books until now, in ones and tens, does not reach that far.
The task is to find a way of choosing at that size that is still his taste and not a blur.

## The stance

**His taste, built up in conversation, is the source.** What he is going for can be talked into
focus: the books he loves, why, particular sentences, images, articles, people, ideas, the feel
of a thing. That takes days of talk, and it is the work, not a preamble to it.

**Borrowed authority is not a reason.** Award lists, canons, "hundred best" books, an imprint's
catalogue, a famous editor's choices: all of these are somebody else's taste, and he does not
want his corpus curated by strangers with reputations. They are fine as places to look and as a
phone book for checking that a book exists. "It is on a list" is never why a book goes in.

**A book wants a reason.** Something that can be said in a line and argued with: what this book
does, what it would put into her. A title without one is a vibe.

**Lean toward the book as the unit, and hold that loosely.** One good book does not make a
backlist good. It is also true that for many writers most of what they wrote belongs, and that
excluding a backlist by reflex would be its own mistake. So: take a whole author when the session
can say why the whole author, and a single book when that is what is true. Decide case by case
and notice which way the cases keep falling.

**What he does not want matters as much as what he does.** A no with its reason sharpens the
picture faster than a yes. Keep the nos.

## A shape the work might take

This is one way through, sketched before any of it was tried. Expect it to change.

1. **Talk until the vision can be written down.** The understanding must not live only in one
   session's head, because sessions end. So the talk gets distilled, as it goes, into a document
   any later session or any other model can read cold: what he is after, in his terms; the
   passages and images that carry it; the yeses and the nos with their reasons. What already
   exists to start from: the three lists and his own words for them in `school/library.md`, the
   reading list in `~/tower/shittalk/fable-book-club/reading-list.md`, the registers named in
   `school/CLAUDE.md` and `BRIEF.md`, and the fifty-five books on the shelf.
2. **A first few hundred by hand, each with its reason.** As many as the session can honestly
   produce while it still knows why each one is there. Two hundred was the number said aloud;
   it is a guess.
3. **Other families, cold.** GPT, Gemini, Kimi, whoever is at hand, given the same document and
   asked for their own lists without seeing anyone else's. They are not there for better taste.
   They have different blind spots. A book several name independently is solid; a book only one
   names is either invented or the obscure find, and those are worth a look by hand.
4. **Branch.** From the first few hundred, still talking about what makes them right, outward.
   How far talk alone can reach is unknown; past some point every model starts choosing by
   reputation, which is the thing being avoided.
5. **Let the chosen books pull the rest.** Once a few hundred books he stands behind are on
   disk as text, likeness can be measured on the prose itself instead of on fame: fetch widely
   and loosely, then keep what reads like the chosen ones. His marks on passages, yes and no,
   calibrate that. `eva/scorer/` is this idea in small. Whether it works at the size of a book,
   and on what unit (a first chapter, sampled pages), nobody has tried.

Other ways in may turn out better: starting from sentences he loves and finding where such
sentences live; starting from what magdra writes when she is good; starting from a single shelf
and widening. If one shows itself, follow it.

## What is known to go wrong

- **A model repeats the same famous few hundred, and then invents.** Past the books everyone
  names, a session produces plausible titles by real authors that were never written, and states
  them with confidence. Every title is checked to exist before it goes on a list. A catalogue of
  the field (the Internet Speculative Fiction Database publishes its whole database) does that
  job, and gives exact editions, which makes a fetch ask for one specific book. It is the phone
  book. It does not get a vote.
- **A file is not always the book its name says.** On the day this was written, of eighteen
  volumes of one annual five were mislabelled and one was an error page repeated thirty times;
  others came as a single story under a book's title, or as a different novel altogether.
  Identity is read from the text (`school/PITFALLS.md`, finding text).
- **One voice can take a shelf without anyone choosing it.** Five of eight web serials were one
  writer and became two thirds of that shelf. Whatever the method, something should notice when
  a single author or a single kind of book is becoming a large share.
- **Scanned books convert badly.** PDF-derived text arrives one paragraph to a page with headers
  fused into sentences. Prefer real ebooks; a rough copy can wait for a clean one.
- **Six thousand is a quantity that hides things.** At that size nothing gets read by a person.
  So whatever does the choosing has to be checked on a sample a person does read.

## What is already built

Everything after "the file is on disk" exists and is described where it lives:
`school/data/CLAUDE.md` (the converter that turns ebooks into text and records what it dropped),
`school/dedupe/CLAUDE.md` (what repeats across shelves, and a lookup that says whether a passage
is lifted from something she has read), `school/sieve/CLAUDE.md` (fiction from the rest),
`school/SHELVES.md` and `school/day4.md` (how shelves become a mix, and what a number of readings
means), `school/PRESERVATION.md` (where text is kept). The fetch list the downloader reads is one
`Author - Title` per line; how bekh fetches is his own business and is not this brief's subject
(`school/CLAUDE.md`, where the text comes from).

What does not exist: the written vision, any way of measuring a book against it, and the list.

## What comes out

Probably, and loosely: the vision as a document that keeps being rewritten; a list in which every
entry has its reason and, where it was dropped, its reason for that; and whatever tool the
branching turns out to need. Where these live and what they are called is for the session and
bekh to settle when there is something to name.

## How the session starts

By discussing this file with bekh, before doing anything else. What in it is wrong, what is
missing, what was said in the heat of one evening and should be taken back, what he would put
differently now. Rewrite it together first. Then begin.
