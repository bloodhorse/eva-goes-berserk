"""Write a never-trained LoRA gguf that carries a weight perturbation.

Three kinds:
  gauss    : A, B iid gaussian, rank r. Frobenius norm of B@A set to
             rel * ||W||_F  -- the "random LoRA" of the sandbagging/CPE papers.
  band     : dW = U_k diag(s_k) V_k^T, the band of W itself (scale it at runtime)
  spectral : dW = U_k diag(s_k * (exp(tau*z) - 1)) V_k^T over singular
             components [k0, k1) of W itself -- jitters the GAINS of the
             model's own learned directions, never adds a new direction.
Base weights are read from the quantized gguf (dequantized in numpy), so no
f16 download is needed. llama.cpp applies the adapter at runtime on the Q4
base; per-request `"lora":[{"id":0,"scale":x}]` re-scales it (or turns it off).
Effective delta = scale * alpha/rank * B@A; alpha is set = rank so scale is literal.

usage: noise_lora.py BASE.gguf OUT.gguf --kind spectral --pattern 'blk\\.(\\d+)\\.ffn_up\\.weight'
                     --layers 12-20 --k0 0 --k1 64 --tau 0.3 --seed 1
"""
import argparse, re
import numpy as np
import gguf
from gguf import GGUFReader, GGUFWriter
from gguf.quants import dequantize

p = argparse.ArgumentParser()
p.add_argument("base"); p.add_argument("out")
p.add_argument("--kind", choices=["gauss", "spectral", "band"], required=True)
p.add_argument("--pattern", required=True)
p.add_argument("--layers", default=None)
p.add_argument("--rank", type=int, default=16, help="gauss only")
p.add_argument("--rel", type=float, default=0.05, help="gauss: ||dW||_F / ||W||_F")
p.add_argument("--k0", type=int, default=0); p.add_argument("--k1", type=int, default=64)
p.add_argument("--tau", type=float, default=0.3, help="spectral: std of log-gain per component")
p.add_argument("--seed", type=int, default=0)
a = p.parse_args()

r = GGUFReader(a.base)
arch = bytes(r.fields["general.architecture"].parts[-1]).decode()
rng = np.random.default_rng(a.seed)
lo, hi = (map(int, a.layers.split("-")) if a.layers else (None, None))
pat = re.compile(a.pattern)

w = GGUFWriter(a.out, arch)
w.add_type(gguf.GGUFType.ADAPTER)
w.add_string(gguf.Keys.Adapter.TYPE, "lora")
rank = a.rank if a.kind == "gauss" else a.k1 - a.k0
w.add_float32(gguf.Keys.Adapter.LORA_ALPHA, float(rank))   # alpha/rank = 1

n = 0
for t in r.tensors:
    if not pat.fullmatch(t.name):
        continue
    m = re.match(r"blk\.(\d+)\.", t.name)
    if lo is not None and (not m or not lo <= int(m.group(1)) <= hi):
        continue
    W = dequantize(t.data, t.tensor_type).astype(np.float32)   # numpy shape (out, in)
    W = W.reshape(int(t.shape[1]), int(t.shape[0]))
    if a.kind == "gauss":
        A = rng.standard_normal((rank, W.shape[1])).astype(np.float32)
        B = rng.standard_normal((W.shape[0], rank)).astype(np.float32)
        B *= a.rel * np.linalg.norm(W) / np.linalg.norm(B @ A)
    else:
        U, s, Vt = np.linalg.svd(W, full_matrices=False)
        sl = slice(a.k0, a.k1)
        if a.kind == "band":      # dW = the band itself: scale +c amplifies it, -1 deletes it (LASER-style)
            g = s[sl].copy()
        else:
            g = s[sl] * (np.exp(a.tau * rng.standard_normal(rank)) - 1.0)
        A = Vt[sl].astype(np.float32)                  # (rank, in)
        B = (U[:, sl] * g).astype(np.float32)          # (out, rank)
    w.add_tensor(t.name + ".lora_a", A)
    w.add_tensor(t.name + ".lora_b", B)
    n += 1
w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
print(f"{a.kind} lora over {n} tensors, rank {rank} -> {a.out}")
