# from-scratch run — copy-paste

Everything lives in `~/eva-olmo/school/` on the box. Architecture: Llama-style decoder
(`LlamaForCausalLM`, tied embeddings) with GPT-2's tokenizer (`openai-community/gpt2`,
50257 tokens, padded to 50304, uint16 bins). Every ssh call from the mac:

```bash
B=ubuntu@10.4.65.34
bx() { ssh -o BatchMode=yes -o ConnectTimeout=8 $B "$@" </dev/null; }
```

## 0. the card is free

```bash
bx 'nvidia-smi --query-gpu=memory.used,memory.total --format=csv; ~/eva-olmo/kit/box_serve.sh status; bash ~/sq1-r3vi3w/eval/gputest/status.sh | sed -n 3p'
bx '~/eva-olmo/kit/box_serve.sh down'
```

`status.sh` line 3 must say `IDLE`; memory.used should be ~0 MiB.

## 1. prep a corpus (one big file or a dir of files, one document per file)

```bash
bx 'cd ~/eva-olmo/school && HF_HOME=~/eva-olmo/hf-home ~/eva-olmo/.venv-train/bin/python prep.py data/fantasy --out bins/fantasy.bin --workers 12'
bx 'cd ~/eva-olmo/school && HF_HOME=~/eva-olmo/hf-home ~/eva-olmo/.venv-train/bin/python prep.py data/scifi.txt --out bins/scifi.bin --workers 12'
```

Each makes `bins/<name>.bin`, `bins/<name>.val.bin`, `bins/<name>.json` (counts, dtype,
tokenizer path) and `bins/<name>.tokenizer/`. A `.jsonl` is not read by prep — flatten it to
text first.

## 2. start a run, detached

`--hours` plans the cosine schedule to end inside the budget (measured after `--calib` steps).
Pick the shape and batch from the throughput table in the report.

```bash
bx 'cd ~/eva-olmo/school && (nohup ~/eva-olmo/.venv-train/bin/python train.py \
  --data bins/fantasy.bin:1 bins/scifi.bin:1 bins/anime.bin:1 \
  --out runs/r1 --layers 12 --width 768 --heads 12 --ctx 1024 \
  --batch 16 --accum 2 --lr 6e-4 --warmup 500 --hours 12 \
  --log-every 50 --eval-every 500 --ckpt-minutes 20 \
  --prompts prompts.txt --compile > runs/r1.log 2>&1 < /dev/null & echo $! > runs/r1.pid)'
```

`--val` defaults to each `<name>.val.bin`; give `--val a.val.bin b.val.bin` to override.

## 3. watch

```bash
bx 'cat ~/eva-olmo/school/runs/r1/status.json'
bx 'tail -5 ~/eva-olmo/school/runs/r1.log'
bx 'ps -p $(cat ~/eva-olmo/school/runs/r1.pid) -o pid,etime,pcpu || echo DEAD'
bx 'tail -n 3 ~/eva-olmo/school/runs/r1/samples.jsonl'
bx 'nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv'
```

Heartbeat age: `bx 'echo $(( $(date +%s) - $(stat -c %Y ~/eva-olmo/school/runs/r1/status.json) ))s'`
— more than ~2 minutes old with the pid alive means stuck; pid gone means dead.

## 4. resume after a reboot or a stop

Same command as step 2 with the same `--out`: it finds `runs/r1/ckpt.pt`, takes every setting
(shape, schedule, plan) from the checkpoint and goes on from its step. Up to `--ckpt-minutes`
of work since the last checkpoint is lost.

```bash
bx 'cd ~/eva-olmo/school && (nohup ~/eva-olmo/.venv-train/bin/python train.py --data bins/fantasy.bin:1 bins/scifi.bin:1 bins/anime.bin:1 --out runs/r1 >> runs/r1.log 2>&1 < /dev/null & echo $! > runs/r1.pid)'
```

## 4b. warm start: a new run from an old run's weights

`--init <ckpt.pt>` into a new `--out`: loads only the model weights, then trains with a fresh
optimizer and a fresh schedule from this command line (`--data`, weights, `--lr`, `--warmup`,
`--hours`, all of it). The shape (`--layers --width --heads --ctx --vocab ...`) is taken from the
checkpoint and shape flags are ignored; the log says which (`INIT ...` lines). The data must use
the same tokenizer. `status.json` carries `init` and `init_step`. `--init` is read only when the
new `--out` has no `ckpt.pt`, so resuming the new run is the step 4 command with its own `--out`.

```bash
bx 'cd ~/eva-olmo/school && (nohup ~/eva-olmo/.venv-train/bin/python train.py \
  --data bins/fantasy.bin:1 bins/scifi.bin:1 bins/anime.bin:1 bins/picks.bin:1 \
  --out runs/r2 --init runs/night1/ckpt.pt \
  --batch 12 --accum 2 --lr 1e-4 --warmup 200 --hours 2 \
  --log-every 50 --eval-every 500 --ckpt-minutes 20 \
  --prompts prompts.txt --compile > runs/r2.log 2>&1 < /dev/null & echo $! > runs/r2.pid)'
```

## 5. export the latest checkpoint and generate a page

```bash
bx '~/eva-olmo/school/export.sh ~/eva-olmo/school/runs/r1 f16'
bx 'ls ~/eva-olmo/school/runs/r1/*.gguf'
bx 'cd ~/eva-olmo && build/bin/llama-completion -m school/runs/r1/model-STEP-f16.gguf -ngl 99 -c 1024 -p "The house did not answer, and so I knew" -n 150 --temp 1 -no-cnv --no-display-prompt --simple-io 2>/dev/null'
```

Replace `STEP` with the number `ls` printed. `q8_0` instead of `f16` for a smaller file.
Exporting while training runs is fine (it reads `ckpt.pt`, which is replaced atomically).

Serve it (loopback only):

```bash
bx '(nohup /opt/llama/bin/llama-server -m ~/eva-olmo/school/runs/r1/model-STEP-f16.gguf -ngl 99 -c 1024 --host 127.0.0.1 --port 8090 --no-jinja > ~/eva-olmo/school/serve.log 2>&1 < /dev/null & echo $! > ~/eva-olmo/school/serve.pid)'
bx 'curl -s http://127.0.0.1:8090/completion -d "{\"prompt\":\"The house did not answer\",\"n_predict\":150,\"temperature\":1}"'
```

## 6. stop everything

SIGTERM makes the trainer write a checkpoint and exit cleanly:

```bash
bx 'kill -TERM $(cat ~/eva-olmo/school/runs/r1.pid)'
bx 'tail -2 ~/eva-olmo/school/runs/r1.log'
bx 'kill $(cat ~/eva-olmo/school/serve.pid)'
```
