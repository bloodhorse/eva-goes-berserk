# handoff — read once, then delete this file

Written 2026-10-05 by the session that ran night 3, at the end of its context. **This file is
disposable: read it whole, then trash it (`trash HANDOFF.md`), commit the removal, and work
from `BRIEF.md` and the docs.** Everything durable in here is already in a doc; what is only
here is the state of this hour and how the last one felt.

## 1. first thing to tell bekh

Right now **llama holds the box's card, and nemo and the painter are off.** Nothing answers on
`127.0.0.1:8080` or `:8189` on the mac, so the transurfers stage has no nemo and no painter and
the stream cannot dream. bekh ordered the eviction (*"evict everyone for the model"*) and has
not said to put them back. Don't restore unasked — say it in your first message and let him
call it. The way back, when he says:

```bash
~/tower/forge/eva-goes-berserk/eva/stream/nemo.sh box        # takes llama down by itself, nemo up, tunnel on 8080
~/tower/shittalk/transurfers/gpu-test-drawing-pipeline/paint.sh up
```

Check any of it yourself before saying it: `eva/stream/nemo.sh status`, and
`ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@10.4.65.34 '~/eva-olmo/kit/box_serve.sh status' </dev/null`.

## 2. the box — how to handle it properly

`docs/olmo.md` ("the box") is the runbook and `eva/CLAUDE.md` ("nemo on the box", "olmo at
the mac's door") is the mac side. This is what a week of it taught, in the order it bites.

**What it is.** A work machine lent to bekh "for a day or two from 2026-10-01" and still there:
`ubuntu@10.4.65.34`, behind the work VPN, an RTX PRO 4000 Blackwell (24.5 GB), 16 vCPU, 109 GB
RAM, a 290 GB disk. It can vanish; results come off it as they land. Its owner is the work
project: DeepSeek (`llama-server.service`) is theirs and is **off**; it stays off unless bekh
says. Never read `~/sq1-r3vi3w` or `~/burn`, never print `/opt/llama/etc/api-key`, never edit
under `/opt/llama`. The one allowed touch: `bash ~/sq1-r3vi3w/eval/gputest/status.sh | sed -n 3p`
must say `IDLE` before you take the card.

**bekh's standing word on it.** Operate there freely — he has never wanted a yes per command.
Kick things off the card when a model needs it; **never put something back unasked** (he was
annoyed both times: DeepSeek restored unasked, and me running a 70B on the cpu to spare the
stage after he had said go). `rm` on the box still needs his word: it has no trash.

**Ours is two directories**, and leaving is deleting them: `~/eva-olmo/` (olmo, nemo and llama
live here despite the name: weights, the torch venv, our `llama-completion` build, the kit, the
banks, the pages) and `~/eva-paint/` (the stage's painter).

**The card holds one of ours at a time.** Sizes on it: nemo 9.5 GB, olmo 20.8, llama 23.1 (44
of her 81 layers; the rest runs on the cpu at 1.7 tok/s), the painter 10–13. Only nemo and the
painter fit together.

```bash
ssh … '~/eva-olmo/kit/box_serve.sh status'            # who holds the card
ssh … '~/eva-olmo/kit/box_serve.sh up olmo|nemo|llama' # takes the other of ours down first; refuses if the painter holds the card
ssh … '~/eva-olmo/kit/box_serve.sh down'
eva/stream/nemo.sh box | mac | off | status            # nemo behind 127.0.0.1:8080, on the box or the mac
~/tower/shittalk/transurfers/gpu-test-drawing-pipeline/paint.sh status | up | down   # 127.0.0.1:8189
launchctl bootstrap gui/$(id -u) eva/stream/com.bekh.eva-olmo.plist                  # olmo's tunnel, 127.0.0.1:8084
```

Ports on the box, loopback only: olmo 8081, nemo 8082, llama 8083 (no tunnel to the mac yet),
painter 8189. Tunnels are launchd jobs loaded from the repo; they never start a server.
**Nothing on the box starts by itself**, on purpose: bekh would rather get an error than a
surprise that takes the card.

**Dosed pages need the card too.** `llama-server` takes a control vector only at startup, so
`box_pages.sh` writes each page with a one-shot `llama-completion` and the model's server must
be down for the run. Take it down, run, bring it back up.

**Disk is the tight thing: 12 GB free.** `df -h /` before any pull. Biggest of ours: olmo's
full weights 61 GB (`olmo-hf`, only needed to learn a new olmo bank, back in three minutes —
the first thing to delete, with his word), llama 40, the painter's models 27, olmo's gguf 19,
nemo 8. Pull with the box's own cli at ~400 MB/s, never curl:
`HF_HOME=~/eva-olmo/hf-home HF_XET_HIGH_PERFORMANCE=1 /opt/llama/tools/hf/bin/hf download <repo> <file> --local-dir <dir>`.
No token is on the box and none goes there; ggufs and mirrors have been ungated so far.

**The traps, every one paid for:**

- **The VPN eats quiet connections and a held ssh hangs forever.** Anything over ~40 s runs
  detached (`nohup … > log 2>&1 < /dev/null & echo $! > pidfile`) and is polled with short
  calls. Always pass `-o BatchMode=yes -o ConnectTimeout=8` and `</dev/null`.
- **An ssh that launches a background job often does not return**; the harness then moves the
  call to the background. Wrap the launch as `(nohup … &)` or just poll in a fresh call.
- **A tool call the user rejects may already have run on the box.** One did: a rejected
  command had launched its remote script, and I printed that script's pages as if they were
  the new run's. After any rejection or interruption, look at what is running there
  (`ps -C python -o pid,etime,args`, `ps -C llama-completion`) before saying nothing happened.
- **Never `pkill -f` / `pgrep -f` over ssh** — the remote shell matches itself. Pid files, or
  `ps -C <name>`.
- **Never write python or a heredoc with its own quotes inside a single-quoted ssh command.**
  The quotes vanish (`tm['x']` arrived as `tm[x]`). Write the script locally, `scp` it, run it.
- **zsh does not split a variable into words**: `S='ssh -o …'; $S cmd` fails. Use a function.
- **The local Bash tool blocks `sleep N && …`.** Wait with `until <check>; do sleep 15; done`
  and a long timeout, or `run_in_background`.
- **Two jobs on the card or the cpu at once ruin both.** A stray cpu run made the server
  process a prompt at one token a second.
- **Check `status.sh` says IDLE, then the card (`nvidia-smi`), then act.** `box_serve.sh up`
  refuses a busy card; that refusal is correct, don't work round it.
- **Surface stats lie about her pages.** `distinct-2` catches loops, not salad. Read the text.

**Also down sometimes: the sheets site.** It is a bare process on the mini and does not
survive a reboot (502 at the name). Restart, the mini is fair game:
`ssh bek@100.69.218.90 'cd ~/sheets && (nohup python3 sheets-serve.py 100.69.218.90 8091 > /tmp/sheets-serve.log 2>&1 < /dev/null &)'`.
bekh had the landing cleared on 2026-10-03; the older articles are in `~/sheets/.trash/2026-10-03/`.

## 3. olmo, briefly

She has two direction banks and a pharmacy of sixteen compounds with known doses that
reproduce on seeds they never saw (`docs/mescalito.md` night 3; the pharmacopoeia's three olmo
sections). **Sober she never gave bekh a dream** — she reads level and holds a frame, "nemo's
weird in a sober tone" — and every weird page of hers is a dosed one. What the drugs do to her
is mostly swap the document (a lyric poem, a russian how-to, pulp noir, the joke-post
internet); the three real subjects — the tribe, the listening machine, the war — are the deep
bank's. So we did not get dreams out of her without drugs, and with them we got weird pages,
which is what bekh said a trip was for. She is off the card now; her weights, banks and pages
are on the box and in `docs/mescalito/night3/`.

## 4. llama, and where bekh's head was when we stopped

`docs/llama.md` has it whole; read its last two sections before you say anything about her.
In short: ten sober pages, and she is the most with-it model we have run — she imitates
beautifully, recites Scott's real diary, ends any seed that stops on a finished sentence, and
adds no strangeness of her own. bekh read the storm girl page and said *reads like an
imitation.*

**The mood of the last hour, which matters more than the facts.** He is tired of the drug
road for her: *"before going that drugging again, let's reconsider… it's always better to
play to her nature than trying to change her against it."* I offered six ways (a nemo-to-llama
handoff, drugged pages as her seeds, long pages, bent classics, her as the sleeper, heat) and
**none of it vibed** — that is fine and part of how he works, don't re-pitch them. He asked to
start from scratch, no solutions: *what can make a sane model go insane?* I thought out loud
(a model has no world but the page; a sane mind goes strange when it forgets how it got here,
when it must explain what it did not choose, when it is left alone too long) and asked which
insanity he meant. **His answer is the most important sentence of the night and is now in
`BRIEF.md`'s criterion:** a dream, to him, is nemo *not completely comprehending what the text
is about* — going by feel, by associations and words — *like some black hole that can look
back at you and throw up the particular circumstances of your death.* Then he asked how long a
bank for her would take, got the answer (about an hour; costed in her doc), and said *"I don't
know, brother"* — **not a go.** Nothing is running toward a bank.

What I think, for what it's worth to you: his definition and my "forgets how it got here"
point the same way. Her trouble is not that she is sober, it is that she always comprehends.
The honest next move is a talk about what takes comprehension away from a mind that has it,
not a build. He ended unsure; meet that, don't sell him a plan.

After the wrap he asked what I made of his answer and how we would get there. What I told
him, as a thought and not a plan: his two wishes pull against each other — a dream is not
comprehending, and comprehending is her nature — unless the not-comprehending is put in what
she can *see* instead of in what she *is*. Every mechanic so far touched her writing; none
touched her reading (the open question at the foot of `docs/mescalito.md`). So: let her read
her own page badly — the last line whole, everything before it as its words without their
order — and she has to go by association because association is all the page gives her. No
drug, no damage, any model size. The other route, answering from a middle layer or skipping
late ones, is closer to what nemo literally is and is exactly "making another nemo". He has
not answered this.

## 5. how this session went wrong and right, so you skip the wrong

- He said it twice: **stop overthinking.** *"A trip is to make her write weird shit; that's
  all."* Plain answers, then the thing.
- **Don't protect things he told you to spend.** When he says go with the cost on the table,
  pay the cost.
- **Don't build the convenience he didn't ask for** — a tunnel that auto-started the server,
  nemo and olmo sharing a port. Both got ripped out.
- He liked: pictures and pages put in front of him without asking, a short **narrative**
  instead of a table when he says "gimme a narrative", and **odd lines quoted verbatim** from
  every read. Check an agent's quotes against the page files by script before relaying them;
  every batch here was checked that way.
- Opus writes the code and does the bulk reading (`model: 'opus'` on every spawn); you
  orchestrate, review, judge. I wrote too much code inline early on.
- He dictates. This week: Almo/Ohmo = olmo, long cat = LongCat, dragging/dragon = drugging,
  trash = stash, hit = heat, lauded = loaded, APA = API.

## 6. loose ends, small

- The night-3 reads (`docs/mescalito/night3/opus-*.md`) are past their day and belong in
  `docs/attic/`; the docs that cite them by path would need the paths fixed in the same commit.
- `docs/mescalito/night1/status.json` and five empty `.log` files were dirty before this
  session and still are; nobody has decided about them.
- `eva/stream/go.sh` now starts the mac's nemo only when nothing answers on 8080. Never run in
  a real ration since.
- transurfers got a private remote (`bloodhorse/transurfers`) and the painter's whole recipe
  in `gpu-test-drawing-pipeline/`; another session works in that repo and keeps uncommitted
  changes — commit only what is yours there.
- The pharmacy in the stream is designed in two sentences and not built (`BRIEF.md`, item 5).
