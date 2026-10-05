# llama

Llama 3.1 70B base, the stage above olmo that the borrowed box made reachable (2026-10-05).
bekh picked her over DeepSeek V4-Flash-Base (292B, which the box can also hold): the family the
anthology's 405B pieces come from, a corpus that ends in 2023, dense and plain, and the biggest
one we could still give a bank. Cleanliness was set aside on purpose — his line: *cleanliness
is less important than being able to make a dream*, and it matters more the smarter the model,
because a smarter model is more with it.

## how she runs

`docs/olmo.md`, the box, is the runbook; this is hers. `box_serve.sh up llama` — loopback :8083
on the box, and **`127.0.0.1:8085` on the mac** through the tunnel job `com.bekh.eva-llama70`
(`eva/CLAUDE.md`, "llama at the mac's door" — that is also how the loom's fans reach her). The file is `Meta-Llama-3.1-70B.Q4_K_M.gguf`, 39.6 GiB,
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

## the shuffle — her reading, not her writing (2026-10-05)

The thought that answered bekh's definition: everything before had touched what she writes,
nothing had touched what she reads. `llama70/shuffle.py` (on the box beside `pot.py`): she
writes in pulls of 40 tokens, and before each pull the page is rebuilt — the last sentence
whole (at least eight words of it), everything before it as its own words, lowercased,
unpunctuated, in a fresh random order; `ignore_eos` so she cannot close. Sober sampler, heat
2.2. Pages and what she saw at each pull: `llama70/shuffle/`.

Two draws on the unsigned note, 400 tokens each, went opposite ways. **Draw 1 lost the story
and kept the sentences**: the man answering the note becomes a dialogue about a
disappearance, a child's house, a night on a porch, and ends *"before her there was no her
there were just men who came to my house… men who just talked in languages that sounded like
shooting stars falling across the"*. bekh liked it: not crazy like nemo — *dizzy,
disoriented*, the cartoon hammer and the stars round the head. **Draw 2 comprehended the
shuffle**: she read the scrambled words as a paper in the story (*"they are not lines at all
what do they mean if there is no word or sentence in it"*) and then wrote the paper out,
thirty lines of six scrambled words. Carried another 400 tokens, draw 1 stayed dizzy and did
not die: one unbroken sentence about a woman who is a star, and the seed's words coming back
as someone else's life (*"when my father disappeared my mother wrote me letters every few
days trying to explain everything"*). Seen in both: the shuffled part has no punctuation and
her own drains away with it.

## her bank (2026-10-05, night 4)

bekh said go that evening. `llama_s20.pt` on the box, `cv-llama/` its 256 directions and 16
random controls as control vectors, the numbers in `docs/mescalito/night4/`. Learned on layers
20 → 30 in bf16 through `melbo_bank.py --slice 1 --front cpu` (her first twenty layers do not
fit the card, so they run once on the cpu; the window's ten take 16.7 GB of it, peak 19.4):

```bash
MODEL=llama-hf ARCH=llama EMBD=8192 NL=80 S=20 T=30 SLICE=1 FRONT=cpu bash kit/box_bank.sh llama
```

Twenty minutes end to end; `R=3.346`, `R/|h_s|=0.48` (olmo's 0.42). The weights it learns from
are a partial download — shards 1–12 of `NousResearch/Meta-Llama-3.1-70B` with a trimmed index,
54 GB in `llama-hf/`. A direction is applied at layer 19 (`--control-vector-layer-range 19 19`)
through `llama-completion -ngl 44 -c 4096`, one reload of her per page: about 40 s for 60
tokens once she is in the page cache. **The top direction (`000_f53`) at ×1.0 is letter-salad**
where two sober runs were identical byte for byte, so the vectors bite and the reading doses
sit well below 1.0. Not read yet. The deeper window (20 → 40 in 4-bit, where olmo's subjects
were) is untried and needs more shards.
