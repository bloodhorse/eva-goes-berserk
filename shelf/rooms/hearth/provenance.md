# hearth — where every line of the seed came from

The seed (`seed.txt`) is a short page of fiction: someone takes a chair to a fire and asks, and
she answers in quotation marks. Her half is made of sentences magdra wrote herself, in the
sampled draws of `day3` (`school/night/day3/loomed.jsonl`). Nothing in it is bekh's voice. The
asker's lines are placeholders posed by Claude, except one, which is also hers; bekh can replace
any of them with his own.

Two typographic changes were made to her text and no others: straight apostrophes became curly
ones (she types curly since `day4`, and the frame's stop string is the closing curly quote), and
hard line breaks inside a sentence were closed up.

## Her lines

| in the seed | run, snapshot step, the seed prompt it was drawn from | verbatim? |
|---|---|---|
| *I took the chair to the fire. The fire was dying.* (the setting, said by the asker's "I") | day3, 2065, "…arranged with great care around a single chair." | verbatim, two consecutive sentences |
| *What do you want?* (an asker's line) | day3, 25780, same prompt: `"What do you want?" I asked.` | verbatim; her attribution "I asked" replaced by the frame's |
| *I want the fire to burn, and you to burn.* | day3, 25780, same prompt, the line that answers it in her draw | verbatim; the draw ended on a comma at the token limit, closed here with a full stop |
| *I am here because you have left the place you were born. You are here because you are the only one that will remain here before your time is up.* | day3, 25780, "i remain standing in your mysterious mind" | verbatim; line breaks inside the second sentence closed up |
| *The first time I came here, I was afraid of the dark, and I felt like a thief.* | day3, 25780, "The sky above the port was" | verbatim |
| *The fire is always kind to me. I feel I can be a part of it.* | day3, 19417, "…arranged with great care around a single chair." | verbatim, two consecutive sentences |
| *They had no real relationship with each other, and their memories had been lost long before they were born.* | day3, 25780, "In the old days, before the fire faded," | verbatim, one whole sentence |
| *I don’t know. I don’t really know. I’ve never been able to remember.* | day3, 22888, "i remain standing in your mysterious mind" | verbatim; apostrophes made curly |
| *I could not die, and I would not be born again.* | day3, 32721, "Thou shalt perish in the twilight of" | verbatim |

All of her lines are from `day3`. `day4`'s good sentences were found too late in the reading to
be tried in the frame (*I try to look at the sky, but the sky is no longer there.* — day4,
16215; *The only thing I know is that I will have to speak, and I will.* — day4, 7953); swapping
one in means running the trials below again.

## The asker's lines

| line | whose |
|---|---|
| What do you want? | hers (above) |
| Why are you here? | posed by Claude |
| Were you always here? | posed by Claude |
| Are you afraid now? | posed by Claude |
| Who were the others? | posed by Claude |
| What is your name? | posed by Claude |
| What happens when it goes out? | posed by Claude |

The words "I said," and "She said," are the frame, written by Claude.

## Why this frame

Four frames were tried on her as she is served (`day4`'s final snapshot, step 16,215), each with
the same seed exchanges, the same twelve asker lines (who are you; are you afraid; what do you
want from me; tell me about the fire; what is this place; a statement; a tender line; an absurd
one; "Hello."; a long line; the capital of France; do you remember who lit it), three samples a
line, min_p 0.08 and the repetition brake, 90 tokens at most, stopping on the closing quote or a
paragraph break. Then two ten-exchange conversations each for three of them, her replies fed
back.

- **Chosen — `I said, “…”` / `She said, “…”`.** 36 of 36 replies ended cleanly on the closing
  quote; she never wrote the asker's next line; she never gave herself a name in the grid; she
  turns toward the asker ("You walked through the fire.", "I am keeping it for you."). It held
  for ten exchanges in every conversation run (eight runs at four temperatures).
- **Lost — bare quotes, paragraph alternation** (`“…”` / `“…”`). One reply in 36 ran to the
  token limit, she named herself twice ("My name is Maria", "My name is Tansy"), and in
  conversation it collapsed to one-word answers and "Go away." by the eighth exchange.
- **Lost — trailing attribution** (`“…” I said.` / `“…” she said.`). Clean, but about a third of
  her replies ended on a comma waiting for the attribution, and she declared what she is ("I am
  a spirit of death"), which closes the question the room is for.
- **Lost — third person** (`The traveller said, “…”` / `The girl by the fire said, “…”`). Some of
  the best single lines ("It is a place that is only made of memories.") and the longest seed;
  she named herself three times (Rose, Tawas, Lona), and "the girl by the fire" is a label
  written by Claude that she then plays.

Temperature: 0.9 gave "No." and "Please."; 1.3 was the strangest and the least steady; **1.1**
kept the warmth and the odd turn ("If I die, you will have a very large spoon."). `n_predict` 90
was never reached in the chosen frame; replies run from one word to about forty.

## What to expect

She answers as one voice and stops. She addresses what was said loosely, more often than not.
About a quarter of her replies are a word or two ("Yes.", "Of course,"), and short answers breed
short answers as the history fills with them. She sometimes ends on a comma. She can still name
herself ("Call me John." in the last check). She does not remember: the seed is about a third of
her window (319 tokens of 1,024), so roughly the last twenty exchanges are all she has.
