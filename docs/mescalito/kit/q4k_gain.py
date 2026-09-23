"""Block-gain noise on a quantized gguf, in place on a copy.

Every Q4_K super-block (256 weights) decodes as  w = d*sc*q - dmin*m.
Multiplying BOTH fp16 fields d and dmin by the same factor f scales the
whole block exactly: w -> f*w. So the noise is multiplicative and
sign-preserving (the learned pattern inside the block survives, only its
gain wobbles). Q6_K decodes as w = d*scale*(q-32), so scaling d alone does
the same. Nothing is requantized; the file keeps its byte length and
offsets, so llama.cpp loads it like the original.

usage: q4k_gain.py SRC DST --pattern 'blk\\.(\\d+)\\.ffn_(up|gate)\\.weight'
                     --layers 20-50 --sigma 0.05 --seed 1
"""
import argparse, re, shutil
import numpy as np
from gguf import GGUFReader, GGMLQuantizationType as Q

p = argparse.ArgumentParser()
p.add_argument("src"); p.add_argument("dst")
p.add_argument("--pattern", required=True)
p.add_argument("--layers", default=None, help="a-b inclusive, matched on blk.N")
p.add_argument("--sigma", type=float, required=True, help="std of log-gain per block")
p.add_argument("--seed", type=int, default=0)
a = p.parse_args()

shutil.copyfile(a.src, a.dst)           # never edit the source
r = GGUFReader(a.dst, "r+")             # memmap writable: edits land in the file
rng = np.random.default_rng(a.seed)
lo, hi = (map(int, a.layers.split("-")) if a.layers else (None, None))
pat = re.compile(a.pattern)
touched = 0
for t in r.tensors:
    if not pat.fullmatch(t.name):
        continue
    m = re.match(r"blk\.(\d+)\.", t.name)
    if lo is not None and (not m or not lo <= int(m.group(1)) <= hi):
        continue
    raw = t.data.reshape(-1).view(np.uint8)
    if t.tensor_type == Q.Q4_K:
        blk = raw.reshape(-1, 144)                     # 2 d + 2 dmin + 12 scales + 128 quants
        f = np.exp(a.sigma * rng.standard_normal(blk.shape[0])).astype(np.float32)
        for off in (0, 2):                             # d, then dmin: same factor -> exact block scale
            h = blk[:, off:off + 2].copy().view(np.float16).reshape(-1)
            blk[:, off:off + 2] = (h.astype(np.float32) * f).astype(np.float16).view(np.uint8).reshape(-1, 2)
    elif t.tensor_type == Q.Q6_K:
        blk = raw.reshape(-1, 210)                     # 128 ql + 64 qh + 16 int8 scales + 2 d
        f = np.exp(a.sigma * rng.standard_normal(blk.shape[0])).astype(np.float32)
        h = blk[:, 208:210].copy().view(np.float16).reshape(-1)
        blk[:, 208:210] = (h.astype(np.float32) * f).astype(np.float16).view(np.uint8).reshape(-1, 2)
    else:
        print("skip", t.name, t.tensor_type.name); continue
    touched += 1
r.data.flush()
print(f"touched {touched} tensors, sigma={a.sigma}, seed={a.seed}")
