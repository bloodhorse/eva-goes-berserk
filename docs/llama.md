# llama

Llama 3.1 70B base, the stage above olmo that the borrowed box made reachable (2026-10-05).
bekh picked her over DeepSeek V4-Flash-Base (292B, which the box can also hold): the family the
anthology's 405B pieces come from, a corpus that ends in 2023, dense and plain, and the biggest
one we could still give a bank. Cleanliness was set aside on purpose — his line: *cleanliness
is less important than being able to make a dream*, and it matters more the smarter the model,
because a smarter model is more with it.

## how she runs

`docs/olmo.md`, the box, is the runbook; this is hers. `box_serve.sh up llama` — loopback :8083
on the box, no tunnel to the mac yet. The file is `Meta-Llama-3.1-70B.Q4_K_M.gguf`, 39.6 GiB,
from `mradermacher/Meta-Llama-3.1-70B-GGUF` (the ggufs are not gated; Meta's repo is). She is
bigger than the card: 44 of her 81 layers on it (`NGL`, 23.1 of 24.5 GiB with a 4k window, one
slot), the rest on the cpu. So **she needs the card alone** — nemo and the painter off — and
writes at **1.7 tok/s**, about 100 s a page; on the cpu only, 0.9. Whatever writes to her from
the box talks to `http://127.0.0.1:8083/completion`; `llama70/pot.py` there is the example.

## what she is, sober (ten pages, 2026-10-05)

The storm girl, Scott, and eight of bekh's cuts from nemo's lines, one page each, the stream's
sampler at heat 2.2, seeds whole. Pages: `llama70/first/`, `llama70/pot/`, on one sheet as
`llama70-pot`.

- **She imitates, very well.** The storm girl came back as a seamless folk-magic prose poem —
  offerings, bones at a crossroad, a crow's secret, a name said three times. bekh: *reads like
  an imitation.* The one line in it that is not furniture: *"a dog came and ate the clippings."*
- **She recites what she has read.** On Scott she wrote the real diary's next sentence word for
  word (*"A very small measure of neglect and have a foot which is not pleasant to
  contemplate"*), one line of her own, and closed the entry — on both draws. Nemo and olmo both
  generated from that seed. Found texts are a weak probe of her; our own cuts are not.
- **She ends anything that looks finished.** Three of the eight nemo-made seeds got zero or one
  token and end-of-document (the bread, the bridge, i'm cold), a fourth closed at 65. Every one
  of those stops on a finished sentence; the two cut mid-clause ran the full page. With her the
  seam is not optional.
- **She amplifies what the seed hands her and supplies no strangeness of her own.** The one
  page that read like a dream came from the one seed that already had dream logic (the house
  that asks where): a man selling hot potatoes, *"shoving them into their skins before taking
  them out again and putting them back in their boxes"*, and *"the person who said this had
  not eaten any of the potatoes."* Plain seeds got tidy stories. She tracks a thread nemo and
  olmo drop (the hair, three beats running) and gives things consequences (the rabbit freed,
  killed, made into soup, its bones buried).

## where the thinking stands

bekh, 2026-10-05, on what a dream is to him — the first time he has said it: what feels like a
dream is that **nemo seems not to completely comprehend what the text is about**, the story in
it; he goes by feel, by associations and words, and that is why it reads unhinged — *like some
black hole that can actually look back at you and throw up the particular circumstances of
your death.* By that measure llama's competence is the problem itself: she always knows what
the text is about.

His turn before that: it is better to play to her nature than to change her against it — *how
can we get a dream out of her without trying to make another nemo.* Offered and not taken up
(none of it vibed): a handoff where nemo dreams a page and she continues it; olmo's and nemo's
drugged pages as her seeds; letting her run long; a famous text with one thing changed; her as
the sleeper who retells nemo's scenes; heat. Then, from scratch, *what can make a sane model go
insane* — the thought on the table when the session ended: a model has no world, only the
page, so its sanity lives in the page; a sane mind goes strange when it forgets how it got
here, when it must account for things it did not choose, when it is left alone too long. None
of those make her dumber; they change what her reason is given to work on. Open, his to
answer: whether the insanity he means is losing the thread or calmly explaining the
impossible — his reply (above) points at the first: not comprehending.

## a bank for her — weighed, not started

bekh did not say go. What was checked: three ungated mirrors carry Meta's 30 weight shards
(`NousResearch/Meta-Llama-3.1-70B`, `unsloth/…`, `SillyTilly/…` — identical hashes to each
other, identical sizes to Meta's, whose hashes are hidden). The bank needs only her layers up
to the window, about 50 GB of the 131; the box has 12 GB free, so olmo's full weights
(`olmo-hf`, 61 GB, re-downloadable) would go first. `melbo_bank.py --slice` needs two changes:
her front layers run once on the cpu (twenty of them do not fit the card), and the weights load
from a partial download (a trimmed shard index). Windows: 20 → 30 in bf16 (17 GB on the card,
~15 minutes by olmo's measure) or 20 → 40 in 4-bit (nemo's depth fraction, where olmo's
subjects were; an hour or more, a path never run; bitsandbytes 0.50 works on this card in the
painter's venv). About an hour to a bank; the slow part is reading it — each dosed page reloads
her and takes over two minutes.
