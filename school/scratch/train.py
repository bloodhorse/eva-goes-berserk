import argparse
import json
import math
import os
import signal
import time
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn.functional as F
import torch.utils.checkpoint
from transformers import GPT2Config, GPT2LMHeadModel, LlamaConfig, LlamaForCausalLM


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", nargs="+", required=True)
    p.add_argument("--val", nargs="*", default=None)
    p.add_argument("--prompts", default="")
    p.add_argument("--sample-tokens", type=int, default=120)
    p.add_argument("--out", required=True)
    p.add_argument("--arch", default="llama", choices=["llama", "gpt2"])
    p.add_argument("--layers", type=int, default=6)
    p.add_argument("--heads", type=int, default=6)
    p.add_argument("--kv-heads", type=int, default=0)
    p.add_argument("--width", type=int, default=384)
    p.add_argument("--ffn", type=int, default=0)
    p.add_argument("--ctx", type=int, default=1024)
    p.add_argument("--vocab", type=int, default=0)
    p.add_argument("--no-tie", action="store_true")
    p.add_argument("--dropout", type=float, default=0.0)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--accum", type=int, default=1)
    p.add_argument("--lr", type=float, default=6e-4)
    p.add_argument("--min-lr-frac", type=float, default=0.1)
    p.add_argument("--warmup", type=int, default=200)
    p.add_argument("--wd", type=float, default=0.1)
    p.add_argument("--clip", type=float, default=1.0)
    p.add_argument("--hours", type=float, default=0)
    p.add_argument("--steps", type=int, default=0)
    p.add_argument("--seconds", type=float, default=0)
    p.add_argument("--calib", type=int, default=40)
    p.add_argument("--log-every", type=int, default=20)
    p.add_argument("--eval-every", type=int, default=250)
    p.add_argument("--eval-iters", type=int, default=20)
    p.add_argument("--ckpt-minutes", type=float, default=20)
    p.add_argument("--compile", action="store_true")
    p.add_argument("--bench", action="store_true")
    p.add_argument("--fresh", action="store_true")
    p.add_argument("--init", default="")
    p.add_argument("--seed", type=int, default=1234)
    return p.parse_args()


DEV = "cuda" if torch.cuda.is_available() else "cpu"
SHAPE = ["arch", "layers", "heads", "kv_heads", "width", "ffn", "ctx", "vocab", "no_tie"]


def sync():
    if DEV == "cuda":
        torch.cuda.synchronize()


def peak_mem(reserved=False):
    if DEV != "cuda":
        return 0.0
    return (torch.cuda.max_memory_reserved() if reserved else torch.cuda.max_memory_allocated()) / 2**30


def log(msg):
    print(msg, flush=True)


def hms(s):
    s = int(max(s, 0))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def build_model(a, meta):
    vocab = a.vocab or (meta["vocab"] + 63) // 64 * 64
    if a.arch == "gpt2":
        cfg = GPT2Config(vocab_size=vocab, n_embd=a.width, n_layer=a.layers, n_head=a.heads, n_positions=a.ctx, n_inner=a.ffn or None, resid_pdrop=a.dropout, embd_pdrop=a.dropout, attn_pdrop=a.dropout, bos_token_id=meta["bos"], eos_token_id=meta["eos"], use_cache=False)
        return GPT2LMHeadModel(cfg), cfg
    ffn = a.ffn or (8 * a.width // 3 + 63) // 64 * 64
    cfg = LlamaConfig(vocab_size=vocab, hidden_size=a.width, intermediate_size=ffn, num_hidden_layers=a.layers, num_attention_heads=a.heads, num_key_value_heads=a.kv_heads or a.heads, max_position_embeddings=a.ctx, rope_theta=10000.0, rms_norm_eps=1e-5, attention_dropout=a.dropout, tie_word_embeddings=not a.no_tie, bos_token_id=meta["bos"], eos_token_id=meta["eos"], use_cache=False)
    return LlamaForCausalLM(cfg), cfg


def to_cuda(rows):
    t = torch.from_numpy(np.stack(rows))
    if DEV == "cuda":
        t = t.pin_memory().to("cuda", non_blocking=True)
    return t[:, :-1], t[:, 1:]


class Data:
    def __init__(self, path, dtype, ctx):
        self.path, self.dtype, self.ctx = path, dtype, ctx
        self.n = os.path.getsize(path) // np.dtype(dtype).itemsize

    def rows(self, starts):
        m = np.memmap(self.path, dtype=self.dtype, mode="r")
        return [m[s : s + self.ctx + 1].astype(np.int64) for s in starts]

    def get(self, starts):
        return to_cuda(self.rows(starts))

    def random(self, batch, gen):
        return self.get(torch.randint(0, self.n - self.ctx - 1, (batch,), generator=gen).tolist())


class Mix:
    def __init__(self, parts, ctx):
        self.parts = [Data(p, d, ctx) for p, d, _ in parts]
        w = torch.tensor([x for _, _, x in parts], dtype=torch.float)
        self.w = w / w.sum()
        self.ctx = ctx

    def random(self, batch, gen):
        pick = torch.multinomial(self.w, batch, replacement=True, generator=gen).tolist()
        rows = []
        for k, part in enumerate(self.parts):
            n = pick.count(k)
            if n:
                rows += [(part, s) for s in torch.randint(0, part.n - self.ctx - 1, (n,), generator=gen).tolist()]
        return to_cuda([x for part, st in rows for x in part.rows([st])])


def parse_data(specs, vals):
    parts, metas = [], []
    for spec in specs:
        path, _, w = spec.rpartition(":") if spec.rsplit(":", 1)[-1].replace(".", "", 1).isdigit() else (spec, "", "1")
        base = path[:-4] if path.endswith(".bin") else path
        with open(base + ".json") as f:
            meta = json.load(f)
        parts.append((path, meta["dtype"], float(w)))
        metas.append(meta)
    vals = vals or [p[:-4] + ".val.bin" for p, _, _ in parts]
    return parts, vals, metas[0]


def lr_at(step, a, total):
    if step < a.warmup:
        return a.lr * (step + 1) / a.warmup
    if not total:
        return a.lr
    prog = min(1.0, (step - a.warmup) / max(1, total - a.warmup))
    lo = a.lr * a.min_lr_frac
    return lo + 0.5 * (a.lr - lo) * (1 + math.cos(math.pi * prog))


def main():
    cli = parse_args()
    os.makedirs(cli.out, exist_ok=True)
    ckpt_path = os.path.join(cli.out, "ckpt.pt")
    status_path = os.path.join(cli.out, "status.json")
    state = None
    if os.path.exists(ckpt_path) and not cli.fresh and not cli.bench:
        state = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        a = argparse.Namespace(**state["args"])
        log(f"RESUME from {ckpt_path} step={state['step']} total={state['total_steps']}")
    else:
        a = cli
        if not (a.hours or a.steps or a.seconds):
            raise SystemExit("give --hours, --steps or --seconds")
    init_sd = None
    if not state and a.init:
        if not os.path.exists(a.init):
            raise SystemExit(f"--init {a.init}: no such file")
        src = torch.load(a.init, map_location="cpu", weights_only=False)
        src_args = dict(src["args"])
        src_args["vocab"] = src["config"]["vocab_size"]
        ignored = [f"--{k.replace('_', '-')} {getattr(a, k)} (checkpoint {src_args.get(k)})" for k in SHAPE if getattr(a, k) != src_args.get(k) and not (k == "vocab" and getattr(a, k) == 0)]
        for k in SHAPE:
            setattr(a, k, src_args.get(k, getattr(a, k)))
        a.init = os.path.abspath(a.init)
        a.init_step = src["step"]
        a.init_tokens = src.get("tokens")
        init_sd = {k.replace("_orig_mod.", ""): v for k, v in src["model"].items()}
        src_meta = src["meta"]
        log(f"INIT weights from {a.init} source_step={src['step']} source_tokens={src.get('tokens', 0):,} source_eval={src.get('last_eval')}; fresh optimizer and schedule; shape from checkpoint: " + " ".join(f"{k}={getattr(a, k)}" for k in SHAPE))
        if ignored:
            log("INIT ignoring shape flags: " + ", ".join(ignored))
        del src
    parts, val_paths, meta = parse_data(a.data, a.val)
    if init_sd is not None:
        for k in ("vocab", "bos", "eos"):
            if meta[k] != src_meta[k]:
                raise SystemExit(f"--init: data {k}={meta[k]} but checkpoint was trained on {k}={src_meta[k]}; different tokenizer")
    torch.manual_seed(a.seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    model, cfg = build_model(a, meta)
    if state:
        model.load_state_dict(state["model"])
    elif init_sd is not None:
        model.load_state_dict(init_sd)
        log(f"INIT loaded {len(init_sd)} tensors")
        del init_sd
    model.to(DEV)
    n_params = sum(p.numel() for p in model.parameters())
    n_emb = model.get_input_embeddings().weight.numel()
    log(f"MODEL {a.arch} layers={a.layers} width={a.width} heads={a.heads} ctx={a.ctx} vocab={cfg.vocab_size} params={n_params / 1e6:.1f}M non_embedding={(n_params - n_emb) / 1e6:.1f}M")

    decay = [p for p in model.parameters() if p.dim() >= 2]
    no_decay = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": a.wd}, {"params": no_decay, "weight_decay": 0.0}], lr=a.lr, betas=(0.9, 0.95), fused=DEV == "cuda")
    if state:
        opt.load_state_dict(state["opt"])

    body = model.get_decoder() if hasattr(model, "get_decoder") else model.transformer
    head = model.get_output_embeddings()
    fwd = torch.compile(body) if a.compile else body
    train = Mix(parts, a.ctx)
    vals = []
    vg = torch.Generator().manual_seed(0)
    for vp in val_paths:
        if os.path.exists(vp):
            v = Data(vp, meta["dtype"], a.ctx)
            if v.n > a.ctx + 1:
                vals.append((os.path.basename(vp)[: -len(".val.bin")] if vp.endswith(".val.bin") else os.path.basename(vp), v, [torch.randint(0, v.n - a.ctx - 1, (a.batch,), generator=vg).tolist() for _ in range(max(1, a.eval_iters // len(val_paths)))]))
    gen = torch.Generator().manual_seed(a.seed + (state["step"] if state else 0))
    prompts = [l.strip() for l in open(a.prompts, encoding="utf-8") if l.strip()] if a.prompts else []
    tok = None
    if prompts:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(meta["tokenizer"])
    tokens_per_step = a.batch * a.accum * a.ctx
    log("DATA " + ", ".join(f"{p}:{w:g} ({d.n:,} tok)" for (p, _, w), d in zip(parts, train.parts)) + f"; val {', '.join(f'{n} ({v.n:,})' for n, v, _ in vals) or 'none'}; {tokens_per_step:,} tokens per step")

    step = state["step"] if state else 0
    total = state["total_steps"] if state else (a.steps or 0)
    tokens = state["tokens"] if state else 0
    train_seconds = state["train_seconds"] if state else 0.0
    last_eval = state.get("last_eval") if state else None
    last_eval_step = state.get("last_eval_step") if state else None
    ckpt_step = step if state else None
    if state:
        torch.set_rng_state(state["rng"])
    del state

    def chunk_loss(h, y):
        with torch.autocast(DEV, dtype=torch.bfloat16):
            logits = head(h)
        return F.cross_entropy(logits.float(), y, reduction="sum")

    def loss_of(x, y):
        with torch.autocast(DEV, dtype=torch.bfloat16):
            h = fwd(input_ids=x, use_cache=False).last_hidden_state
        h = h.reshape(-1, h.size(-1))
        y = y.reshape(-1)
        tot = 0.0
        for i in range(0, h.size(0), 4096):
            tot = tot + torch.utils.checkpoint.checkpoint(chunk_loss, h[i : i + 4096], y[i : i + 4096], use_reentrant=False)
        return tot / y.numel()

    per_file = {}

    def evaluate():
        if not vals:
            return None
        model.eval()
        per_file.clear()
        with torch.no_grad():
            for name, v, starts in vals:
                per_file[name] = sum(float(loss_of(*v.get(s))) for s in starts) / len(starts)
        model.train()
        return sum(per_file.values()) / len(per_file)

    def sample():
        if not prompts:
            return
        model.eval()
        with torch.no_grad(), open(os.path.join(a.out, "samples.jsonl"), "a", encoding="utf-8") as f:
            for pr in prompts:
                ids = torch.tensor([[meta["bos"]] + tok(pr, add_special_tokens=False)["input_ids"]], device=DEV)
                start = ids.size(1)
                for _ in range(a.sample_tokens):
                    with torch.autocast(DEV, dtype=torch.bfloat16):
                        logits = model(input_ids=ids[:, -a.ctx :], use_cache=False).logits[:, -1].float()
                    nxt = torch.multinomial(torch.softmax(logits, -1), 1)
                    ids = torch.cat([ids, nxt], 1)
                    if int(nxt) == meta["eos"]:
                        break
                text = tok.decode(ids[0, start:].tolist())
                f.write(json.dumps({"step": step, "tokens_seen": tokens, "prompt": pr, "text": text}, ensure_ascii=False) + "\n")
        model.train()
        log(f"SAMPLES step={step} -> samples.jsonl")

    def save_ckpt():
        if a.bench:
            return
        payload = {"model": model.state_dict(), "opt": opt.state_dict(), "step": step, "total_steps": total, "tokens": tokens, "train_seconds": train_seconds, "last_eval": last_eval, "last_eval_step": last_eval_step, "args": vars(a), "arch": a.arch, "config": cfg.to_dict(), "meta": meta, "rng": torch.get_rng_state()}
        tmp = ckpt_path + ".tmp"
        with open(tmp, "wb") as f:
            torch.save(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ckpt_path)
        log(f"CKPT step={step} {ckpt_path}")
        sample()

    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))

    model.train()
    t_start = time.time()
    t_ckpt = time.time()
    t_win, tok_win = time.time(), 0
    calib_t = None
    bench_t0, bench_tok = None, 0
    rate = 0.0
    loss_win, loss_n = 0.0, 0
    phase = "calibrating" if (a.hours and not total) else "training"
    while True:
        if total and step >= total:
            break
        if stop["flag"]:
            log("STOP signal: checkpointing and exiting")
            break
        t_step = time.time()
        lr = lr_at(step, a, total)
        for g in opt.param_groups:
            g["lr"] = lr
        acc = 0.0
        for _ in range(a.accum):
            x, y = train.random(a.batch, gen)
            loss = loss_of(x, y)
            (loss / a.accum).backward()
            acc += loss.detach()
        if a.clip:
            torch.nn.utils.clip_grad_norm_(model.parameters(), a.clip)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        tokens += tokens_per_step
        tok_win += tokens_per_step
        loss_win += float(acc) / a.accum
        loss_n += 1
        train_seconds += time.time() - t_step

        if step == 10:
            sync()
            calib_t = time.time()
            bench_t0, bench_tok = time.time(), 0
        elif step > 10:
            bench_tok += tokens_per_step
        if phase == "calibrating" and step == a.calib:
            sync()
            step_time = (time.time() - calib_t) / (a.calib - 10)
            overhead = 1 + a.eval_iters / (3 * a.eval_every * a.accum)
            left = a.hours * 3600 - train_seconds
            total = step + max(1, int(left * 0.97 / (step_time * overhead)))
            phase = "training"
            log(f"PLAN step_time={step_time:.3f}s budget={a.hours}h total_steps={total} tokens={total * tokens_per_step:,}")
        if a.seconds and bench_t0 and time.time() - bench_t0 >= a.seconds:
            break

        evaled = False
        if step % a.eval_every == 0 or (total and step == total):
            last_eval, last_eval_step, evaled = evaluate(), step, True
        if step % a.log_every == 0 or evaled or step == 1:
            sync()
            now = time.time()
            rate = tok_win / max(now - t_win, 1e-9)
            t_win, tok_win = now, 0
            train_loss = loss_win / max(loss_n, 1)
            loss_win, loss_n = 0.0, 0
            eta = (total - step) * tokens_per_step / rate if total and rate else None
            mem = peak_mem()
            ev = f"{last_eval:.4f}@{last_eval_step}" if last_eval is not None else "-"
            if per_file and len(per_file) > 1:
                ev += " (" + " ".join(f"{k} {v:.3f}" for k, v in per_file.items()) + ")"
            log(f"step {step}/{total or '?'} | loss {train_loss:.4f} | eval {ev} | lr {lr:.2e} | {rate / 1e3:.1f}k tok/s | mem {mem:.1f}G | elapsed {hms(train_seconds)} | eta {hms(eta) if eta is not None else '?'}")
            if not a.bench:
                write_json(status_path, {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "unix": now, "pid": os.getpid(), "phase": phase, "step": step, "total_steps": total, "tokens_seen": tokens, "train_loss": train_loss, "eval_loss": last_eval, "eval_per_file": dict(per_file), "eval_step": last_eval_step, "lr": lr, "tok_per_s": rate, "elapsed_s": train_seconds, "wall_s": now - t_start, "eta_s": eta, "peak_mem_gib": mem, "ckpt_step": ckpt_step, "params": n_params, "init": getattr(a, "init", "") or None, "init_step": getattr(a, "init_step", None)})
        if not a.bench and time.time() - t_ckpt >= a.ckpt_minutes * 60:
            save_ckpt()
            ckpt_step, t_ckpt = step, time.time()

    sync()
    mem = peak_mem()
    res = peak_mem(True)
    if a.bench:
        dt = time.time() - bench_t0 if bench_t0 else 0
        log("BENCH " + json.dumps({"params_m": round(n_params / 1e6, 1), "layers": a.layers, "width": a.width, "ctx": a.ctx, "batch": a.batch, "accum": a.accum, "compile": a.compile, "steps": step, "tok_per_s": round(bench_tok / dt) if dt else None, "peak_alloc_gib": round(mem, 2), "peak_reserved_gib": round(res, 2)}))
        return
    if last_eval_step != step:
        last_eval, last_eval_step = evaluate(), step
    save_ckpt()
    done = total and step >= total
    write_json(status_path, {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "unix": time.time(), "pid": os.getpid(), "phase": "done" if done else "stopped", "step": step, "total_steps": total, "tokens_seen": tokens, "train_loss": None, "eval_loss": last_eval, "eval_per_file": dict(per_file), "eval_step": last_eval_step, "tok_per_s": rate, "elapsed_s": train_seconds, "eta_s": 0 if done else None, "peak_mem_gib": mem, "ckpt_step": step, "params": n_params, "init": getattr(a, "init", "") or None, "init_step": getattr(a, "init_step", None)})
    log(f"{'DONE' if done else 'STOPPED'} step={step} tokens={tokens:,} eval_loss={last_eval} elapsed={hms(train_seconds)} peak_mem={mem:.2f}GiB alloc {res:.2f}GiB reserved")


if __name__ == "__main__":
    main()
