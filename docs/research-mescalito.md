# mescalito: the answer

The answer to the mescalito brief (deleted once answered; git `b4446e8`), 2026-09-24. The brief
asked whether a *uniform* perturbation of a base model — the weights charged like a bath in
electrolysis — could make it strange while locally coherent, and asked for a verdict, a table of
mechanisms, three evenings' experiments, sources, and gaps. Seven research slices went into it (weight
noise and quant, stochastic and activation noise, attention and layers, samplers and flags, the
loom scene, the reddit sweep, MELBO), about 49k words, each written by an opus researcher with
web access; the slices are in `mescalito/`, the scripts they wrote and left unrun in
`mescalito/kit/`. Two amendments bekh made while it ran: the model is not fixed to OLMo, any
open-weight base is fair game; and nothing is ruled out, tunes included. Every number below
carries its source. "Bench" means a researcher's own run on a small stand-in (a 1.5B Qwen, a 7B
OLMo stage1): read those as anecdote with a ruler, not as fact.

## 1. The verdict

No. Nothing that charges every weight the same way gives lightning, and the reason is geometry,
not dose. Isotropic weight noise, low quants, jitter on the Q4 block scales, random LoRAs: all
of them drown the model's smallest singular components first, and that is where the rare
associations live (LASER's mechanism: same slot, other noun). So a charged model doesn't go
strange, it goes **average**. The IQ1 gemma writes the same cactus metaphor five times where Q8
writes "a bottled rain", and on a 1.5B bench seven different perturbations landed on one
divergence curve. It doesn't even fail the way the brief feared: "slur, then salad" is how
*heat* fails; damage inside the network fails **variety → loop → salad**, and the drop into the
loop is sudden (the gpt-2 noise thread; DRµGS's "very sudden fall-off to echolalic
degeneracy"). Random directions on the residual stream are absorbed at steering size and break
past it, with no sweet spot between (Turner's random-vector control; Mack: "no Goldilocks value
of R" for random vectors). What bends a model without breaking it is a direction the model
**owns**: learned with no text and no target (MELBO/DCT), cut from its own activations, its own
singular band turned up. And the brief's metaphor already says how to deliver one: briefly. A
push held for a page is a mood or a genre switch; a push held for a clause and released leaves
an arrival, with the ground still there. Uniformity moves from the vector to the lot: a bank of
owned directions, one drawn at random per strike. Nobody has built that. **First:** learn a DCT
bank of 256 directions on Mistral Nemo 12B base (one rented A40, minutes of compute), read it
frozen and blind against sixteen random directions of the same size, then strike with the
survivors through two llama-servers. Beside it, the one free edit that has already produced
frame-kept strange pages on a 7B stand-in: OLMo's attention sharpened ×2 by writing into its
F32 q-norm vectors.

## 2. The table of mechanisms

Two facts make the table readable. First, **the failure order is a fingerprint.** Loops mean you
damaged the inside or overdrove one direction. Salad with a few lovely fragments means the
sampler reached the tail. Fused-token misspellings (*"i didnth write it"*) mean the layer order
was broken. Second, **architecture decides where a push bites.** Nemo, Mistral Small and Llama
are pre-norm, so noise *inside* a block writes straight into the residual. OLMo 2/3 is
post-norm: each sublayer's output is renormalised before the add, so in-block noise can only
rotate what a block writes, never make it louder. One paper found an OLMo 3.1 32B shrugs off
activation noise 60× larger than Llama-3.1-8B does before a comprehension check breaks (σ_max
0.66 vs 0.011, Fornasiere 2026; not our checkpoint). So on OLMo the stance is a push on the
residual stream, which it reads unnormalised. In-block noise belongs on the pre-norm bases.

Model key: **nemo** = Mistral Nemo 12B base (pre-norm, clean, fast, the debug model) · **small**
= Mistral Small 3.1 24B base (pre-norm, clean) · **olmo** = OLMo 3 32B stage1-step656000
(post-norm, QK-norm, checkpoints published) · **olmoe** = OLMoE-1B-7B (MoE, open checkpoints).
Qwen and nemotron bases are not clean.

| mechanic | what it does | reported feel | dose · cliff | on llama.cpp + Q4 | model | cost (32B) | bet |
|---|---|---|---|---|---|---|---|
| **dead: uniform damage** | | | | | | | |
| gaussian on all weights | W + σ·std(W)·ε per tensor | "ouchddenreeoraoraora" (8B at σ 2 on one layer) | σ_rel 0.05 → ppl +2%, 0.2 → +64% (8B paper); knee sudden | no flag: bf16 → noise → requant | any | ~1 h per dose | average, then loop |
| same, by family / depth | restrict by tensor regex and layers | none published; bench: same curve at matched KLD | mid ffn_down needs 2× the dose (1.5B bench); early layers 5× more fragile (8B paper) | as above | pre-norm bites; olmo softens | ~1 h | slur with an accent |
| Q4 block-scale jitter | d, dmin × e^(σz) per super-block | σ 0.1: "fluent confabulation" (bench) | σ 0.2 ppl ×1.36, 0.4 ×700 (1.5B bench) | `q4k_gain.py`, in place | any k-quant | minutes | calibration tool only |
| low quant (Q2/IQ2/IQ1) | rounding noise, worst on fine distinctions | "drunk PhD"; "smear concepts together" | tail explodes below ~3 bpw (Mistral-7B KLD table) | `llama-quantize --tensor-type` | any; MoE tolerates it | 20 min per variant from bf16 | toward the generic |
| random LoRA | ΔW = B·A, gaussian, rank r | "rarely produce a consistent theme" | ×2 ok, ×8 gone (1.5B bench) | `--lora`, per-request scale | any | seconds | control only |
| isotropic residual noise, per token | h + α·RMS(h)·ε every step | "0% collapse" at α 0.175 (7–9B instruct, stories) | only safe point published; no prose sweep | patch, or refill the cvec per token | any | ≈ stock speed | temperature with an accent |
| random control vector, whole page | one random direction per layer | "doesn't change much"; mood set "atmospheric, melancholic" | at 10× norm still coherent, Shrek goes female (front-only injection); sense goes at 1–2× (Rogue Scalpel, instruct) | `--control-vector-scaled`, startup only | any | free | negative control |
| DRµGS rotation, per token | rotate H/Q/K/V/A by random angle | "vary the outputs nicely, or else immediately break and start repeating" | author: "shouldn't go past 0.1" rad; 30B coherent at 1.0; 7B loops at 1.0 | transformers only; ~150-line port | pre-norm llama/mistral | ≈ free at runtime | coherent diversity |
| stochastic weights per token | fresh weight draw per token | nothing reported | — | impossible on Q4 (requant per token) | — | — | dead |
| rope base far too low | slow bands rotate inside the page | pure sentence loops (7B bench, base 5000) | cliff between 50k and 5k (7B bench) | `--rope-freq-base` | any | free | done; loops |
| KV cache quant | noise in the cache | ppl 13.58 vs 13.55 (7B bench) | nothing at page length | `-ctk/-ctv q4_0` | any | free | non-dial |
| random head dropout | mask heads per token | argued: frame heads drop, prior fills in | — | patch | any | patch | banal |
| layer skip / shuffle | skip or reorder blocks | "i didnth write it", "you shouldnthing it" | one swap inert; 12-wide shuffle ppl ×3 (7B bench) | `gguf_layers.py` | any | minutes | slur, literally |
| **alive: owned directions** | | | | | | | |
| MELBO / DCT bank vector | learned vector that most changes a later layer; no text, no target | "a 'dream-like' stream of consciousness" (1.8B backdoored chat, arithmetic) | Goldilocks R; onset to mostly-nonsense ×1.6 in R (1B instruct replication) | HF to learn → cvec `direction.{s-1}` | nemo first, then olmo | minutes of GPU | ≤5% hybrids per bank |
| real-difference strike | doc-A activation minus doc-B, pushed briefly | "I don't detect an injected thought. The ocean remains calm and undisturbed." | strength 2–4 at ~⅔ depth (Claude's units); restate as 0.5–1× \|h\| | `llama-cvector-generator --method mean` | olmo, nemo | free | lightning candidate |
| covariance-shaped noise | random, shaped like the stream's own spread | "cov-random ≈ real" directions (GPT-2) | untested | `rand_cvec.py` + imatrix diag | olmo only (imatrix trick) | free | middling |
| singular band amplified | late up/gate band 64–512 × (1+c) | "I am a voice in my mother's dreams…" then n=5 didn't hold (1.5B bench) | c 0.1–0.4; ×2 gone (bench) | LoRA gguf, per-request scale | pre-norm or olmo | SVD minutes | 1 in 4 (its author) |
| neuron cross-wiring | neuron j also writes neuron j′'s column | untested ("synaesthesia") | calibrate to \|h\| | `rand_lora.py --mode wire` + column copy | nemo | seconds | untested |
| checkpoint delta | θ + α·DARE(θ₆₅₆ₖ − θ₆₅₅ₖ) | never read as prose | α unknown; several units | SVD → LoRA | olmo only | +65 GB download | temperature-like |
| damaged twin | clean model masks, drunk twin ranks | "fluent but unreasonable" (a subtracting paper) | mask = min_p 0.1 on clean | two servers + a driver | olmo + its Q2, or nemo + cvec | ~half speed, 48 GB | real candidate |
| MoE router noise | a different trained expert answers | nobody | unknown | edit `ffn_gate_inp` | olmoe | a cheap night | unknown |
| **knobs: attention, layers, samplers** | | | | | | | |
| attention sharpening (q-norm) | q_norm × a ⇒ every logit × a | ×2: "as if my own name were a cage" (7B stage1 bench) | ×1.25–2.0; flattening ×0.6 doubles ppl | `gguf_dial.py … attn_q_norm 2.0 all` | olmo (F32 norms in Q4) | free | lightning-leaning |
| `--yarn-attn-factor` | scales rope'd Q and K ⇒ logits × x² | ordinary pages at 0.7/1.3 (7B bench) | — | flag | nemo/small/llama: all layers; olmo: 16 of 64 | free | weak on olmo |
| post-norm gain | ffn_post_norm × b: associations louder | ×1.3 baseline register (7B bench) | ×1.5–2.0 untested | `gguf_dial.py … post_ffw_norm` | olmo | free | untested middle |
| block-scale gain on attn_q | pre-norm twin of the q-norm edit | untested | as q-norm | `gguf_gain.py` | nemo, small | minutes | worth a row |
| middle-block repeat | a 4–8 layer block runs twice | "a slightly tipsy Miqu after a glass of wine" | one copy; avoid first/last 15% and 56–65% depth | `gguf_layers.py "0-31,24-63"` | olmo, small | +12.5% time | split verdict |
| min_p floor | cut on the *unheated* logits | "prevents garbage from the long tail" | 0.08 → 0.05 → 0.03 | per request | any | free | the real dial |
| XTC | drop top choices at forks only | "creativity is off the charts" / "randomness increased, not creativity" | olmo: 0.05 / 1.0; or low threshold, very low probability | per request | any | free | changes which, not weather |
| adaptive-p | surprise budget: forks spend what furniture saves | "My blood turns to icy slurry…" | target 0.30, decay 0.9 | per request, list `adaptive_p` | any | free | the sampler to try |
| mirostat | bits-per-token feedback | "doing literally nothing" | τ 2.5–4, not 8–12 | per request | any | free | trap: kills DRY, min_p, XTC |
| top-nσ, dynatemp | adaptive gap; entropy temperature | "Nsigma felt like mirostat 2; very strange" | n ~1 | per request | any | free | nothing new with temp-last |
| page-fixed logit bias | random vector through the unembedding, held for 170 tokens | untested | sd 0.5–2 nats; cliff near 2.5 | `logit_bias`, per request | any | free | the sampler's bridge |
| glitch token by id | an untrained token at one position | base models "swerve", can't repeat it | one token | mixed-id prompt | olmo (139 at init) | free | a swerve, not weather |
| **fair game now: LoRA and tunes, ranked by flavour you'd smell by page five** | | | | | | | |
| LoRA on strange text | a tune on dream reports, backrooms logs, the shelf's stars | Oneirogen (DreamBank): "physical law violation, teleportation"; truth_terminal | fractional scale; pulsable | `--lora`, per request or `/lora-adapters` | nemo, small, olmo | a QLoRA evening | strong flavour: smellable by page two |
| CPE / MELBO adapters | rank-1 o_proj LoRAs from a content-free objective | "obsessed with a certain topic" | R = 1 spectral norm | per-request `lora` | needs an OLMo patch | cheap | flavour = one obsession each |
| tunes toward its own geometry | band amp, checkpoint delta, random LoRA, entropy tunes | re-phrasings, sameness | as above | LoRA | any | cheap | no flavour: not smellable |

Five places where reports disagree, each settled in a sentence. Report 05 says overdriven
isotropic noise ends in salad; the forum curves and the 1.5B bench say it loops first and salads
last, and I go with the loop. Report 04 argues that a perturbation fixed for the whole page is
the one a strong model can't heal; report 07 answers that a vector held all page gives an
obsession (CPE's own judge defines success that way), and report 02 argues for strikes. I pick
the strike: correlated over a clause (so it isn't healed like per-token noise), released before
it hardens into a theme. On middle-block repeats, report 03 leans lightning from Goliath lore,
and the self-merge threads call repeats "weirdly deterministic", so it stays a knob, not a bet.
Report 01 bets 1 in 4 on the amplified singular band and then reports its own n=5 set failing to
reproduce; the bet rests on mechanism only. XTC on OLMo: report 04 wants threshold 0.05 at
probability 1.0 because a sharp model rarely has two tokens above 0.1; -p-e-w-'s rare-lightning
setting is a low threshold at a very low probability. Try the second first, since it's the one
that is rare.

## 3. The three experiments

Each is one evening on one rented A40 48 GB ($0.49/h on RunPod, the card that carried the
olmo night), image `ghcr.io/ggml-org/llama.cpp:full-cuda`. The full image, not `server-cuda`,
because it carries `llama-completion`, `llama-quantize`, `llama-imatrix`,
`llama-cvector-generator` and the converter. Every script named below is in
`docs/mescalito/kit/`: `melbo_bank.py` and `export_cvec.py` (report 07's recipe, cut out
verbatim), `strike.py` (the two-server driver, new, tested only against stub servers),
`blind.py`, `gguf_dial.py`, `gguf_layers.py`, `rand_cvec.py`, `q4k_gain.py`, `noise_lora.py`.
They live under `docs/` and not `eva/` on purpose: provenance of the research, not an
instrument yet; they move when one of them has run for real.
**The kit had its dry run on the mac on 2026-09-24** (smollm2-135m in bf16 on mps for the bank,
the real nemo Q5 and a smollm gguf for the llama side, torch 2.14 / transformers 5.17): every
script ran end to end, no hook or layer-path trip. The one edit it needed is `--device`
on `melbo_bank.py` (default `cuda`, `mps`/`cpu` for a toy). Two things it showed: the top
directions by strength at 1.0×R flattened the 135m's page into pure newlines — the dose can be
too high as well as too low, so if the screen reads dead across the board, rerun the top 16 at
0.5×R before 2.0×R; and llama.cpp doesn't check `controlvector.model_hint` (a vector tagged
`olmo2` loaded into nemo without a word), so a wrong `--n-embd` is the only guard against
feeding one model the other's bank. `strike.py` ran its three arms against two live servers:
token ids cross the seam, spans land in the row, and the sober server picks up in a new
register after a strike even on the toy.

Traps, one line each. The server's libs live in `/app`: `export LD_LIBRARY_PATH=/app` or it dies
on `libllama-server-impl.so`. Mirostat silently switches off DRY, min_p, XTC and top-nσ. Control
vectors load at startup only (no request field; PR #24740 would add `/cvectors`, still open). A
per-request `lora` change clears that slot's KV cache, while `POST /lora-adapters` doesn't.
`direction.k` is added after block k (0-based); a DCT vector trained at the input of layer s is
exported as `direction.{s-1}`. `--rope-freq-scale` and `--yarn-attn-factor` reach only 16 of
OLMo's 64 layers; `--rope-freq-base` reaches all. **OLMo stage1's special tokens are untrained**
(every one except `<|endoftext|>`, `<|im_start|>` included), and llama-server turns their
literal strings in a seed into those tokens, so a seed quoting `|||EMAIL_ADDRESS|||` injects
noise. The server README says `repeat_penalty` defaults to 1.1; the code says 1.00.

Pod setup, the same every night:

```bash
export LD_LIBRARY_PATH=/app PATH=/app:$PATH          # the image keeps its libs beside the binaries
curl -LsSf https://astral.sh/uv/install.sh | sh && . ~/.local/bin/env
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python torch transformers accelerate gguf numpy "huggingface_hub[cli]"
mkdir -p seeds/train seeds/read
# from the mac: kit/ up, and two seed sets. The bank is trained on one set and read on the
# other, so it can't have memorised the seeds it's judged on.
#   scp -r -P <port> kit shelf/seeds/short/*.txt  root@<pod>:~/            (then mv *.txt seeds/train/)
#   scp    -P <port> docs/olmo-seeds/*.txt         root@<pod>:~/seeds/read/  (the heat/rope nights' ten)
```

The stream's sampler, used everywhere unless an arm says otherwise: temperature 2.0 (the stream
draws 1.8–2.5), min_p 0.08, top_k 0, top_p 1, DRY 0.8 / 1.75 / 2, repeat 1.05 over 512. That's
`strike.py`'s default.

**Experiment 1: the bank, frozen, blind against random (nemo).** It answers two questions.
Does a direction the model owns do something a random one of the same size doesn't? And what
does a base model's switchboard look like: genres, obsessions, or weather?

1. Weights, and a Q4 of them (~8 min download at the 50 MB/s the olmo night saw, ~10 min
   convert and quantize). The full bf16 is needed anyway to learn the bank:
   ```bash
   .venv/bin/hf download mistralai/Mistral-Nemo-Base-2407 --local-dir nemo-hf     # accept the licence on HF first if it asks
   python3 /app/convert_hf_to_gguf.py nemo-hf --outtype bf16 --outfile nemo-bf16.gguf   # the image's own python has the converter's deps
   llama-quantize nemo-bf16.gguf nemo-q4km.gguf Q4_K_M
   ```
2. Learn 256 directions, source layer 10, target 20 (DCT's constant horizon; nemo has 40
   layers). The script calibrates R so the response is half nonlinear (λ 0.5), and prints R,
   the median residual norm at layer 10, and their ratio. **Write the three numbers down.**
   They're the dose unit for everything after, and nobody has published R/|h| for any model.
   ```bash
   .venv/bin/python kit/melbo_bank.py --model nemo-hf --seeds seeds/train/*.txt --s 10 --t 20 --m 256 --out nemo_s10.pt
   mkdir -p cv && .venv/bin/python kit/export_cvec.py nemo_s10.pt llama     # cv/000_f*.gguf … each a single direction.9, pre-scaled by R
   ```
3. Sixteen random directions of exactly the same length, as controls:
   ```bash
   R=<printed R>; A=$(.venv/bin/python -c "print($R/5120**0.5)")     # rand_cvec sizes a vector as alpha·sqrt(n_embd)
   for s in $(seq 0 15); do .venv/bin/python kit/rand_cvec.py cv/rand_$s.gguf --n-embd 5120 --n-layer 40 --layers 9-9 --alpha $A --seed $s; done
   ```
4. One page per vector on one read seed: the top 64 by strength plus the 16 randoms, same RNG
   seed, 80 pages at a few seconds each:
   ```bash
   SEED=seeds/read/2026-09-21-1645.txt; mkdir -p screen
   for f in $(ls cv/0*.gguf | head -64) cv/rand_*.gguf; do
     llama-completion -m nemo-q4km.gguf -ngl 99 -f $SEED -n 170 --seed 1 -no-cnv --no-display-prompt \
       --temp 2.0 --min-p 0.08 --top-k 0 --top-p 1.0 --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 \
       --control-vector-scaled "$f:1.0" --control-vector-layer-range 9 9 \
       > screen/$(basename $f .gguf).txt 2>/dev/null
   done
   .venv/bin/python -c "
   import json,glob,os
   with open('raw.jsonl','w') as f:
       for p in glob.glob('screen/*.txt'):
           f.write(json.dumps({'cond':os.path.basename(p)[:-4],'seed':'$SEED','text':open(p).read()})+'\n')"
   .venv/bin/python kit/blind.py        # blind.md to read, key.json sealed: don't open it
   ```
5. Read blind, on the sheets site (from the mac:
   `scp -P <port> root@<pod>:~/blind.md . && pandoc -s blind.md -o blind.html && scp blind.html bek@100.69.218.90:~/sheets/`).
   Mark every page 0 (nothing), 1 (odd), 2 (the frame held and something arrived). Then open
   the key.

**What to read for the verdict.** Count the 2s among the 64 owned directions and among the 16
random ones. If random scores like owned, the geometry argument of this whole answer is wrong,
and uniform noise is back on the table. Say so and stop. If owned wins, take every owned 2 onto
three more read seeds (same loop, `SEED` changed) and sort them by report 07's test. The same
genre on all three seeds is a genre switch. The same noun on all three is an obsession. **Three
frames held, with three different arrivals, is weather.** Those vectors are the bank. Report
07's own guess for a 256-bank: about half do nothing, a quarter switch genre or language, a
fifth obsess, and at most 5% are hybrids. If the screen shows nothing at 1.0×R, rerun the top 16
at 2.0×R before concluding (`:2.0` in the flag). Mack multiplied his calibrated R by 4 on a
Mistral.

**Experiment 2: the strike (nemo).** Frozen against pulsed, on the same vectors. This is the
design's core bet, tested cheaply.

1. Three servers on one card (nemo Q4 is ~7.5 GB each): sober, struck with an owned vector,
   struck with a random one of the same norm.
   ```bash
   llama-server -m nemo-q4km.gguf -ngl 99 -c 2048 -np 1 --port 8080 >/dev/null 2>&1 &
   llama-server -m nemo-q4km.gguf -ngl 99 -c 2048 -np 1 --port 8082 \
     --control-vector-scaled cv/rand_0.gguf:1.0 --control-vector-layer-range 9 9 >/dev/null 2>&1 &
   # 8081 gets a new owned vector per seed: the lot. A restart from page cache takes seconds.
   start81() { [ -n "$P81" ] && kill $P81; llama-server -m nemo-q4km.gguf -ngl 99 -c 2048 -np 1 --port 8081 \
     --control-vector-scaled "$1:1.0" --control-vector-layer-range 9 9 >/dev/null 2>&1 & P81=$!
     until curl -sf localhost:8081/health >/dev/null; do sleep 1; done; }
   ```
2. Four arms per read seed. The strike: after a sentence ends, a 25% chance the next 12 tokens
   come from the struck server; at most 3 strikes a page. The frozen arm is the whole page on
   8081:
   ```bash
   V=(cv/<weather-1>.gguf cv/<weather-2>.gguf cv/<weather-3>.gguf)   # the survivors of night one
   : > raw.jsonl; i=0
   for s in seeds/read/*.txt; do
     start81 "${V[$((i % ${#V[@]}))]}"; i=$((i+1))
     .venv/bin/python kit/strike.py $s clean  --sober 8080                              >> raw.jsonl
     .venv/bin/python kit/strike.py $s frozen --sober 8081                              >> raw.jsonl
     .venv/bin/python kit/strike.py $s struck --sober 8080 --struck 8081 --p 0.25 --len 12 >> raw.jsonl
     .venv/bin/python kit/strike.py $s random --sober 8080 --struck 8082 --p 0.25 --len 12 >> raw.jsonl
   done
   .venv/bin/python kit/blind.py
   ```
3. Read the 40 pages blind, same marks, then open the key. Each row in `raw.jsonl` carries its
   strike spans in tokens, for after the key.

**What to read for the verdict.** Struck-owned against frozen is the design question. Frozen
should read as one theme all page. Struck should hold the seed's frame at token 170 and carry
one or two arrivals that don't belong to the seed. Struck-random against clean is the control:
if struck-random scores like struck-owned, the strike itself is doing the work (a hiccup the
sober model builds on), not the direction, and the bank is decoration. After the key, check
where the 2s landed. A 2 that sits *after* a strike, in the sober stretch, is the ground
answering the lightning. That's the thing we're after.

If night one's bank came back empty, run the same night with real-difference vectors instead:
`llama-cvector-generator -m nemo-q4km.gguf --positive-file a.txt --negative-file b.txt --method
mean -o diff.gguf`, one per pair of unrelated shelf documents. It writes unit vectors on every
layer, so load at `:<0.75 × median |h|>` with `--control-vector-layer-range 26 26` (~⅔ depth,
where concept injection worked).

**Experiment 3: the read (olmo 32B).** Nemo was the debug. This night asks whether the 32B
carries it, and it puts the free attention edit and the matched-surprise sampler beside it, so
the evening settles the sampler question too.

1. The Q4 (6 min) and the bank's shards. Only layers 0–19 plus the embeddings are needed,
   roughly a third of 64 GB. If `from_pretrained` insists on every shard anyway, pull the lot
   (~22 min); the pod needs ~100 GB of disk either way:
   ```bash
   .venv/bin/hf download Tricit/Olmo-3-1125-32B-stage1-step656000-Q4_K_M-GGUF --local-dir olmo-q4
   H=allenai/Olmo-3-1125-32B; REV=stage1-step656000
   .venv/bin/hf download $H --revision $REV --include "*.json" "tokenizer*" --local-dir olmo-hf
   SH=$(.venv/bin/python -c "
   import json,re; m=json.load(open('olmo-hf/model.safetensors.index.json'))['weight_map']
   n=lambda k: re.search(r'layers\.(\d+)\.',k)
   print(' '.join(sorted({f for k,f in m.items() if 'embed' in k or (n(k) and int(n(k).group(1))<20)})))")
   .venv/bin/hf download $H --revision $REV --include $SH --local-dir olmo-hf
   ```
2. The bank on olmo (layers 0–19 in bf16 is ~20 GB; report 07 puts 0–31 at 32 GB; fits the A40), exported
   with the olmo hint. Screen the top 64 and 16 randoms exactly as in night one:
   `--n-embd 5120 --n-layer 64 --layers 9-9`, model `olmo-q4/*.gguf`, and sampler
   `--temp 3.0 --min-p 0.08 --xtc-probability 0.5 --xtc-threshold 0.1` with DRY (her range from
   the heat night). Keep the ones that held three frames with three different arrivals.
   ```bash
   .venv/bin/python kit/melbo_bank.py --model olmo-hf --seeds seeds/train/*.txt --s 10 --t 20 --m 256 --out olmo_s10.pt
   rm -rf cv && mkdir cv && .venv/bin/python kit/export_cvec.py olmo_s10.pt olmo2
   ```
3. The free edit: a copy with every attention logit doubled. It's 64 F32 vectors, no requant:
   ```bash
   cp olmo-q4/*.gguf olmo-q20.gguf && .venv/bin/python kit/gguf_dial.py olmo-q20.gguf attn_q_norm 2.0 all
   ```
   Report 03's 7B stand-in gave the strangest frame-kept pages of its run at ×2.0. Its failure
   is anaphora loops, which DRY exists to brake. ×1.6 there gave argument loops.
4. Five arms on the ten read seeds, 50 pages. Two olmo servers fit 48 GB at `-c 2048`
   (~40 GB with buffers, per report 02). So run arms A, B and D on the sober 8080 + struck 8081
   pair, then stop 8081 and start the q20 copy on 8081 for arm C:
   ```bash
   O='{"temperature":3.0,"xtc_probability":0.5,"xtc_threshold":0.1}'          # her range: t3, min_p 0.08, xtc, DRY
   M='{"samplers":["penalties","dry","min_p","adaptive_p"],"min_p":0.03,"adaptive_target":0.30,"adaptive_decay":0.9,"dry_allowed_length":3,"repeat_penalty":1.0}'
   # A clean       strike.py $s clean   --sober 8080 --sampler "$O"
   # B matched     strike.py $s matched --sober 8080 --sampler "$M"    (no temperature at all: adaptive-p replaces it)
   # C sharpened   strike.py $s sharp   --sober 8081 --sampler "$O"    (8081 = olmo-q20.gguf, no vector)
   # D struck      strike.py $s struck  --sober 8080 --struck 8081 --p 0.25 --len 12 --sampler "$O"   (8081 = start81 with an olmo survivor, one per seed)
   # E nemo        copy the ten "struck" rows from night two's raw.jsonl in (its own sampler: the scale question, not a controlled one)
   # start81 here is night two's function with olmo-q4/*.gguf in place of the nemo file
   ```
5. `blind.py`, read on sheets, marks 0/1/2, then the key.

**What to read for the verdict.** B against A answers report 04's question: is nemo's dream just
its surprise level? Target 0.30 asks olmo to be as surprising per token as nemo's 212 stream
pages, which average a chosen-token probability of 0.32. If B collects the 2s, the sampler was
enough and no weights need to change. D against C against A answers whether the owned strike
beats the free global edit. D against E is the scale question (bekh picks the pile with the
ghosts). If C wins, the answer is a 64-vector edit and this whole design is overbuilt, and
that's a fine outcome.

**The design: what nobody has built.** Five parts, each taken from somewhere else. Nobody has
put them together.

*A bank of owned directions.* The survivors of the three-seed test (weather, not genre, not
obsession), plus their negations. The exponential DCT isn't sign-symmetric, so −v is a new probe
for free. Second source: real-difference directions, one document's state minus another's.
Third, weight-side and pulsable too: LoRAs (a strange-text LoRA, the amplified singular band),
because `POST /lora-adapters` swaps the global adapter set without clearing the KV. Starting
size: whatever survived; 8 is enough to begin.

*The lot.* Uniform over the bank, one draw per strike, sign at random. This is where the
brief's "uniform" lives now: uniform over the model's own switchboard, not over its weights.

*The pulse.* Off by default. After each sentence end, with probability **p = 0.25**, the drawn
direction goes on for **n = 12 tokens** (range 4–16), at most **3 strikes a page**, then off.
The dose is **1.0 × R** for a DCT vector (calibrated R, window roughly 0.6–1.6× going by the
1B replication's band) and **0.5–1.0 × median |h|** for a real-difference vector. Layer: the
DCT source layer (nemo and olmo: s = 10, exported as `direction.9`); ~⅔ depth for
real-difference vectors. The sampler stays at her range. The charge goes inside, not into the
sampler.

*Memory of the strike*, a dial between two semantics. Re-read sober (the two-server trick: after
the strike the sober server re-prefills the page, so the struck words are just text now), or
the past stays struck (one server, the vector turned off mid-page, the KV of the struck tokens
kept). Start with re-read sober. It's the free one, and it's the "ground still there
afterwards" in its purest form.

*Three routes, cheapest first.* **v0, tonight:** two servers and `strike.py`. The lot is per
page, because the struck server restarts to change vectors. **v1:** cherry-pick PR #24740
(`GET/POST /cvectors`, open). Load the whole bank at scale 0, and the driver POSTs one scale per
strike without clearing the KV. One server, the lot per strike, no C++ of ours. **v2, the ~80-line
patch** (report 02, recipe b3): a `maybe_charge()` in `server_context::decode()` right before
`llama_decode`. It strikes on the token after punctuation, draws from a preloaded pool, scales
to `alpha × |h_k|`, releases after `strike_len`, logs each strike's token span into the
response, and fixes `set_adapter_cvec` so it stops forcing a scheduler re-reserve on every call.
Knobs by env (`MESC_ALPHA`, `MESC_LAYERS`, `MESC_P`, `MESC_LEN`, `MESC_POOL`), so a condition is
a restart, not a plumbing job. It's also the only route with per-token precision. In the stream,
the writer calls the driver instead of `/completion` directly; streaming word by word survives,
per chunk.

Why the pulse, in one line: per-token noise is white and a strong model heals it (report 04's
self-recovery; DRµGS's "drowns that noise out"); a push held all page is a leash (CPE's
"obsessed with a certain topic"; random vectors' mood palette); a clause-long push is long enough
to put something in the page and short enough that the model has to *argue it into the frame*,
which is what bekh already likes olmo for.

## 4. Sources

Grouped by mechanism, deduplicated, only what the answer uses or a reader would check. *paper* =
peer-reviewed or preprint; *scene* = practitioner write-ups, repos, the loom crowd; *forum* =
reddit, GitHub issues, HN.

**Uniform weight noise and why it averages**

- *paper* Dak, "Perturbation Robustness Profiles," 2026, Zenodo 20403835, https://zenodo.org/records/20403835 — Llama-3.1-8B-Instruct: "perplexity 12.87 → 13.14 (σ 0.05) → 13.93 (0.10) → 16.02 (0.15) → 21.07 (0.20)"; "It is token-level incoherence: short fragments repeated, occasional cross-script characters, no syntactic structure."; "the sharp σ = 1.0 → σ = 2.0 transition is more consistent with a regime change in the model's coherent-generation capacity than with a graded loss of any specific learned content."
- *paper* Sharma, Ash, Misra, "LASER: The Truth is in There," arXiv 2312.13558 — "these components describe either a different response of the same semantic category as the correct answer or generic high-frequency words … their conflicting responses produce a sort of 'average answer'."
- *paper* "Neural Thickets," arXiv 2603.12228 — "diverse specialists whose behavior is qualitatively different from the singular pretrained weights" (σ 0.005, Qwen2.5 0.5B–32B; task accuracy, never prose).
- *paper* Mack, Panickssery, Turner (CPE), arXiv 2606.29604 — "Random LoRAs rarely produce a consistent theme (nearly all mass lies at zero)"; "random perturbations produce only local noise that quickly dissipates."
- *forum* MrVodnik, r/LocalLLaMA, "Model 'neurodegeneration' at different noise levels," 2024-03-05, https://reddit.com/r/LocalLLaMA/comments/1b7e4mf/ — GPT-2 124M: at 0.001 "I love ice cream. I love ice cream. I love ice"; at 0.03 "Mr. Gonzalez's unopened canned chicken each Sunday each Sunday each Sunday"; at 0.08 "arilyarily that that that that".
- *forum* phree_radical, r/LocalLLaMA, https://reddit.com/r/LocalLLaMA/comments/1b6wd34/ — Mistral 7B, std 1e-4 on every parameter: 'night' 0.069 → 0.0515, 'flight' and 'fight' climb.

**Quantization as noise**

- *forum* atineiatte, r/LocalLLaMA "671B IQ1_S vs 70B Q8_0," 2025-06-03, https://reddit.com/r/LocalLLaMA/comments/1l1r366/ — "lower quants smear concepts together"; gemma3-4b IQ1_S: "Cactus are known for their ability to withstand the elements." ×5; Q8: "The cactus is a bottled rain, holding onto every precious drop."
- *forum* LocoLanguageModel, https://reddit.com/r/LocalLLaMA/comments/1hrogx6/ — "Highly quantized larger models = drunk PhD who can still give you better domain information than the intern."
- *forum* ikawrakow, llama.cpp PR #5453 (IQ1_S), https://github.com/ggml-org/llama.cpp/pull/5453 — "This is why she wants to go back to her house, where it is not yet 1870's and all over a little bit of 20th century."

**Random directions, plateaus, and the loop cliff**

- *paper/scene* Turner et al., "Steering GPT-2-XL by adding an activation vector," https://www.lesswrong.com/posts/5spBue2z2tw4JuDCx — "the random vector doesn't modify the qualitative distribution of completions … +10-random-steered GPT-2-XL begins referring to Shrek with female pronouns. However, the outputs are still comparably coherent"; "the anger vector changes the output tokens less than the random vector does."
- *scene* Mack, "Mechanistically Eliciting Latent Behaviors," https://www.lesswrong.com/posts/ioPnHKFyy4Cw2Gr2x — "for random steering vectors, there is no Goldilocks value of R which leads to meaningfully different continuations … uninteresting re-phrasings of the model's unsteered continuation, if they even lead to any changes"; "it is possible to cram exponentially many almost-orthogonal directions within the residual stream."
- *paper* Danilov et al., "Many Are My Names," arXiv 2608.07852 — "their content narrows down to a small mood registered set: 'atmospheric', 'grounded', 'melancholic', 'soft'."
- *paper* "The Rogue Scalpel," arXiv 2509.22067 — random unit directions at 0.25–2.0 × mean norm: "excessive coefficients degrade output coherence, producing nonsensical responses".
- *paper* Janiak et al., "Characterizing stable regions in the residual stream," arXiv 2409.17113 — "stable regions … become more defined as training progresses or model size increases." (measured on OLMo and Qwen2)
- *paper* Lee & Heimersheim, arXiv 2410.12555 — "Cov-random mixture directions influence the model's output more significantly than isotropic random directions."
- *paper* Fornasiere et al., arXiv 2604.17465 — σ_max "Llama3.1-8B … 0.011 … Olmo3.1-32B … 0.66".
- *paper* Khalid, Shapsough, Zualkernan, "Noise Steering," arXiv 2604.03380 — "α is a fixed scaling coefficient set to 0.175"; "0% collapse rate for every model"; "Embedding noise (EMBED) causes complete collapse on Phi-4-mini (100%)".
- *paper* Templeton et al., "Scaling Monosemanticity," https://transformer-circuits.pub/2024/scaling-monosemanticity/ — "±100× their observed maximum … repeating the same token indefinitely."
- *scene* Theia Vogel, https://vgel.me/posts/representation-engineering/ — "We have a global pandemic that has caused a global pandemic that has caused a global pandemic".

**DRµGS**

- *scene* EGjoni, https://github.com/EGjoni/DRUGS — "You probably shouldn't go past 0.1"; "we can add quite a lot of noise in earlier layers and the model very quickly drowns that noise out with its own signal"; porting guide: "the residual stream is your model's only tether to sanity."
- *code* the "random" direction is uniform, not centred. `drugs/generation/utils.py` at commit `3c053ea`, https://github.com/EGjoni/DRUGS/blob/3c053ead813b2d903df23a33f9b25b6ba3c25c1e/drugs/generation/utils.py#L52-L67:
  ```python
      random_vectors = torch.rand_like(input_vectors)
      projections = input_vectors * (torch.sum(random_vectors * input_vectors, dim=-1, keepdim=True) / 
                     torch.sum(input_vectors * input_vectors, dim=-1, keepdim=True))
      orthoshifts = random_vectors - projections
  ```
  `rand_like` draws U[0,1). Report 02 measured two successive draws at cosine 0.75 with each
  other, so the "random" rotation mostly points one fixed way. A port should use `randn_like`.
- *forum* qrios (the author), r/LocalLLaMA, https://reddit.com/r/LocalLLaMA/comments/18toidc/ — "a pretty big range of both safe and effective doses, followed by a very sudden fall-off to echolalic degeneracy"; "It mostly seems to either vary the outputs nicely, or else immediately break and start repeating the same word over and over."
- *forum* llama.cpp #4704 (closed by the stale bot), https://github.com/ggml-org/llama.cpp/issues/4704 — "The method requires intimate contact with the kv-cache."

**Owned directions: MELBO, DCT, CPE, concept injection**

- *scene* Mack & Turner, MELBO, https://www.alignmentforum.org/posts/ioPnHKFyy4Cw2Gr2x — "for most examples I tried there was an intermediate 'Goldilocks' value of R which led to diverse but fluent continuations"; "they seem to exhibit a 'dream-like' stream of consciousness, splicing together seemingly incongruous concepts in peculiar ways, similar to human dreams." (Qwen-1.8B-Chat with two backdoors, one arithmetic prompt, the leftover vectors of a 100-bank)
- *scene* Mack & Turner, DCT, https://www.alignmentforum.org/posts/fSRg5qs9TPbNy3sm5 — "one can learn 512 generalizable steering vectors in ~30 seconds on a single H100"; "for a constant depth-horizon t − s = 10, a value of λ = .5 works across a variety of models"; "larger models are better able to rationalize why they are talking about a certain concept"; "Qwen-1.5-7b is less sensitive to the choice of R than, say, Mistral-7b."
- *paper* CPE, arXiv 2606.29604 — judges told each persona "tends to be obsessed with a certain topic, bringing it up in response to almost everything."
- *forum* 25Hour & submarat, ARENA replication, https://www.lesswrong.com/posts/YhTnnKHQ5yQrAmi5p — diversity "seems to peak … at 0.7 and drop sharply both before and after it"; coherence "starts dropping after 0.55 … about 0.9 … mostly nonsense."
- *paper* Lindsey, "Emergent Introspective Awareness," https://transformer-circuits.pub/2025/introspection/index.html — "I don't detect an injected thought. The ocean remains calm and undisturbed."; "At high steering strengths, the model begins to exhibit 'brain damage,' and becomes consumed by the injected concept".
- *code* https://github.com/amack315/melbo-dct-post (`src/dct.py`) · https://github.com/amack315/cpe
- *paper* Zhu et al., arXiv 2407.10795 — skipping layers makes a model "generate fluent but unreasonable content" (used to subtract; nobody samples toward it).

**Attention and layers**

- *paper* Yu et al., "Thermometer of Thoughts," ACL 2026, https://aclanthology.org/2026.acl-long.200/ — "stable for attention temperatures between 0.9 and 1.1 … below 0.5 or above 1.7 frequently lead to reasoning chains irrelevant to the input".
- *paper* Sun et al., "Transformer Layers as Painters," arXiv 2407.09298 — "Repeating a single layer is worst"; "Mathematical and reasoning tasks are more order dependent than 'semantic' tasks."
- *forum* r/LocalLLaMA "Best Miqu and Llama-3 Frankenmerge (Self)," https://reddit.com/r/LocalLLaMA/comments/1cpct22/ — "performs like a slightly tipsy Miqu after a glass of wine - a bit sluggish but full of inspirations"; Caffeine_Monster: "the interleave size is mostly a tradeoff between creativity and smarts".
- *forum* MikeRoz, https://reddit.com/r/LocalLLaMA/comments/1aj2jw0/ — self-merge: "infinite stammering … weirdly deterministic".
- *forum* AlpinDale on Goliath, https://reddit.com/r/LocalLLaMA/comments/17rsmox/ — "it tends to make slight spelling mistakes - it hallucinates words."
- *forum* Drew Smith, https://reddit.com/r/LocalLLaMA/comments/1rvxmnh/ — Qwen2.5-32B, 56–65% depth: "Delete it = output dies. Duplicate it = reasoning dies."
- *forum* Sabin_Stargem on rope, https://reddit.com/r/LocalLLaMA/comments/1ev8n2s/ — "it sometimes changed the personality … [it] produced an afterlife spa hotel. Unexpected, but interesting and read very nicely."

**Samplers**

- *scene* ddh0 / MrJackSpade, adaptive-p, llama.cpp PR #17927, https://github.com/ggml-org/llama.cpp/pull/17927, https://github.com/MrJackSpade/adaptive-p-docs — "Adaptive-P cannot create choices that don't exist."; "A target of 0.3 encourages more surprising choices."
- *scene* p-e-w, XTC, https://github.com/oobabooga/text-generation-webui/pull/6335 — "The creativity is off the charts, while the coherence is virtually unchanged."; r/LocalLLaMA 1ev8n2s: "pairing a low xtc_threshold with a very low xtc_probability … occasionally, XTC will force a highly unlikely continuation"; Mart-McUH, https://reddit.com/r/LocalLLaMA/comments/1fv5kos/: "with XTC I feel like randomness increased, not creativity."
- *forum* cynerva, https://reddit.com/r/LocalLLaMA/comments/1ev8n2s/ — "MinP=0.125, temperature=infinity … more creative and engaging, less repetitive, and still coherent"; https://reddit.com/r/LocalLLaMA/comments/1ip8imy/: "If temperature is applied last … MinP remains stable at higher temperatures."
- *forum* turboderp, 1ev8n2s — mirostat "was doing literally nothing--except that turning it on also disabled all the other samplers."
- *paper* Banayeeanzade et al., arXiv 2605.11128 — "no decoding method that relies on top-token filtering can effectively recover diversity".
- *forum* HeavyConfection9236, https://reddit.com/r/LocalLLaMA/comments/1kmmq6d/ — Qwen3 0.6B at temperature 20: "Soisahn Cășe Oread Recipe … Maybe warm stones, cooked bread" (heat without a floor: salad with fragments).

**The scene, glitches, accidents**

- *scene* janus, 2024-04-02, generative.ink/archive/repligate/tweets_2024-04/ — "I think it's due to runtime dynamical basins, not changes in the sampler."
- *scene* janus, 2024-10-30, …/tweets_2024-10/ — steering vectors "doesn't seem sufficient to produce profound changes"; 2024-10-23: "steering vectors make it much more likely" to break spelling and grammar.
- *scene* janus on the Feb-2024 kernel bug, …/tweets_2024-02/ — "despite being strange it's very regular, crystalline."
- *forum* OpenAI status, https://status.openai.com/incidents/ssg8fh7sfyz3 — "the model chose slightly wrong numbers"; sample via The Register: "Drape all affairs and pamphlet in a strip of prudence".
- *run* report 05's scan of OLMo stage1: untrained rows at norm 1.40 vs 11.2 trained; every special but `<|endoftext|>` untrained.

**Fair game: tunes**

- *forum* antcroca159, "Oneirogen," https://reddit.com/r/LocalLLaMA/comments/1dqfl5r/ — Qwen2 tuned on DreamBank: "Dreams have phenomenological properties such as physical law violation, teleportation, less sensorial content".
- *forum* Nathan Helm-Burger, https://www.lesswrong.com/posts/buiTYy75KJDhckDgq — "Andy didn't fine-tune Claude, he prompted it" (truth_terminal is the tune: Llama 3.1 70B on ~500 backrooms logs).

**llama.cpp, read from source (master d2e5458, 2026-09-23)**

- `tools/server/README.md` — per-request `lora`: "If a LoRA adapter is not specified in the list, its scale will default to `0.0`."; PR #24740: "POST applies the new scale immediately without clearing slot KV caches".
- `common/common.h` default chain `penalties; dry; top_n_sigma; top_k; typ_p; top_p; min_p; xtc; temperature`; `src/models/olmo2.cpp` (no pre-norm, `build_cvec` after the FFN add, hard-coded kq_scale, sliding layers at attn_factor and freq_scale 1.0).

## 5. What could not be found

Nobody has published generated prose from a weight-noise sweep, at any dose or on any tensor
family. The papers measure perplexity, accuracy and specialisation. Nobody has noised Q4 block
scales (only trained them), used a random LoRA for its writing, or read what a "thicket"
neighbour writes.

Nobody has run MELBO, DCT or CPE on a base model with an open-ended document. The base runs were
a one-shot arithmetic prompt. The "dream-like" quote comes from a backdoored 1.8B chat model's
leftover vectors. There's no Goldilocks plot from the authors, the only R curve is a 1B instruct
replication, nobody has expressed R relative to the residual norm, and nobody has reported where
the weird vectors sit in a ranking.

Nobody has pulsed any of this. No strike schedule, no per-n-token vector swap, no aesthetic
generation from transplanted activations (Patchscopes and concept injection are interpretability
tools). Nobody samples *toward* a damaged twin; every contrastive paper subtracts it. No DRµGS
port to llama.cpp, koboldcpp, exllama or vLLM exists, and its author never compared rotation to
additive noise.

Prose is missing for attention temperature (papers score reasoning only; report 03's pages are
the first, n=3 on a 7B), for mirostat at τ 8–12, for top-nσ at T 3–5 on a base model, for
entropix, and for adaptive-p beyond its authors' samples. No sampler schedules heat by position
in the page. No one has tried a page-fixed random logit bias.

The scene did almost nothing to the machine: 38 months of janus's archive shows steering-API play
on a tuned model, one question about fp8, and no noise, ablation or random vectors. If ampdot,
doomslide or the Act I operators did machine-side work, it's in invite-only Discords (Act I,
Cyborgism, chapter II) or deleted X threads. Nitter is dead, janus's archive stops at 2025-05,
and aidan_mclau's fp8-vs-bf16 tweet on Hyperbolic's 405B survives only through janus's replies.
No text-model version of Klingemann's neural glitch exists as art.

Reddit was only partly reachable. The Arctic Shift archive rate-limited seven researchers
through most of the session ("Too many requests", "Timeout. Maybe slow down a bit"). Comment-body
search in r/LocalLLaMA timed out even in three-week windows, so the sweep ran on title search,
~60 whole threads by id, and author-scoped searches of the regulars. Anything good buried in a
thread with an unrelated title is unsearched, not absent. That goes for random control vectors,
DRµGS reactions beyond the two announcement threads, and 2024 low-quant prose in
r/SillyTavernAI. Every frankenmerge and quant "feel" on record is from instruct or roleplay
tunes. None is from a base model.

About the fair-game rows: the seven slices were briefed while tunes were still ruled out, so
nothing here measures how a LoRA on strange text reads by page five. Oneirogen and truth_terminal
are named, not read. And nothing here was run on the 32B itself. OLMo's residual norms, its KLD
curve for quants, and every OLMo prediction above are inferred from a 7B stage1 stand-in, from
OLMo 2 papers, or from the layout of the graph.
