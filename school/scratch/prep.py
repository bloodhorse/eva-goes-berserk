import argparse
import json
import os
from multiprocessing import Pool

import numpy as np
from transformers import AutoTokenizer

TOK = None


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("--out", required=True)
    p.add_argument("--tokenizer", default="openai-community/gpt2")
    p.add_argument("--val-frac", type=float, default=0.01)
    p.add_argument("--chunk-mb", type=float, default=4)
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    return p.parse_args()


def init(name):
    global TOK
    TOK = AutoTokenizer.from_pretrained(name)


def encode(job):
    text, eos = job
    ids = TOK(text, add_special_tokens=False)["input_ids"]
    if eos:
        ids.append(TOK.eos_token_id)
    return ids


def chunks_of_file(path, size):
    with open(path, encoding="utf-8", errors="replace") as f:
        buf = []
        n = 0
        for line in f:
            buf.append(line)
            n += len(line)
            if n >= size and line.strip() == "":
                yield "".join(buf), False
                buf, n = [], 0
        yield "".join(buf), True


def jobs(path, size):
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            fp = os.path.join(path, name)
            if os.path.isfile(fp):
                yield from chunks_of_file(fp, size)
    else:
        yield from chunks_of_file(path, size)


def main():
    args = parse_args()
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    vocab = len(tok)
    dtype = np.uint16 if vocab <= 65535 else np.uint32
    base = args.out[:-4] if args.out.endswith(".bin") else args.out
    os.makedirs(os.path.dirname(os.path.abspath(base)), exist_ok=True)
    tok_dir = base + ".tokenizer"
    tok.save_pretrained(tok_dir)
    every = max(2, round(1 / args.val_frac)) if args.val_frac > 0 else 0
    n_train = n_val = 0
    with open(base + ".bin", "wb") as ft, open(base + ".val.bin", "wb") as fv, Pool(args.workers, initializer=init, initargs=(args.tokenizer,)) as pool:
        for i, ids in enumerate(pool.imap(encode, jobs(args.input, int(args.chunk_mb * 2**20)), chunksize=1)):
            a = np.array(ids, dtype=dtype)
            if every and i % every == every - 1:
                a.tofile(fv)
                n_val += len(a)
            else:
                a.tofile(ft)
                n_train += len(a)
    if n_val == 0 and every:
        whole = np.fromfile(base + ".bin", dtype=dtype)
        cut = max(1, int(len(whole) * args.val_frac))
        whole[-cut:].tofile(base + ".val.bin")
        whole[:-cut].tofile(base + ".bin")
        n_train, n_val = len(whole) - cut, cut
    meta = {"tokenizer": os.path.abspath(tok_dir), "dtype": np.dtype(dtype).name, "vocab": vocab, "eos": tok.eos_token_id, "bos": tok.bos_token_id, "train_tokens": n_train, "val_tokens": n_val, "input": os.path.abspath(args.input)}
    with open(base + ".json", "w") as f:
        json.dump(meta, f, indent=1)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
