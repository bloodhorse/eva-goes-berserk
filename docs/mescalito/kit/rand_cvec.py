# write a random control vector for llama.cpp: one gaussian direction per layer,
# scaled to a fraction `alpha` of that layer's residual norm.
# llama.cpp adds direction.k to l_out of block k (0-based), for every position,
# prompt included; direction.0 is refused by the loader, so k runs 1..n_layer-1.
import argparse, numpy as np, gguf

p = argparse.ArgumentParser()
p.add_argument("out")
p.add_argument("--n-embd", type=int, default=5120)     # olmo 3 32b
p.add_argument("--n-layer", type=int, default=64)
p.add_argument("--alpha", type=float, default=0.25)    # |v| / |residual| per layer
p.add_argument("--rms", default=None)                  # .npy [n_layer]: per-element RMS of l_out-k
p.add_argument("--layers", default=None)               # "16-40": zero outside (or use --control-vector-layer-range)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--hint", default="olmo2")
a = p.parse_args()

rng = np.random.default_rng(a.seed)
rms = np.load(a.rms) if a.rms else np.ones(a.n_layer, dtype=np.float32)
lo, hi = (map(int, a.layers.split("-")) if a.layers else (1, a.n_layer - 1))

w = gguf.GGUFWriter(a.out, "controlvector")
w.add_string("controlvector.model_hint", a.hint)
w.add_uint32("controlvector.layer_count", a.n_layer - 1)
for k in range(1, a.n_layer):
    d = np.zeros(a.n_embd, dtype=np.float32)
    if lo <= k <= hi:
        d = rng.standard_normal(a.n_embd).astype(np.float32)
        d *= a.alpha * rms[k] * np.sqrt(a.n_embd) / np.linalg.norm(d)
    w.add_tensor(f"direction.{k}", d)
w.write_header_to_file()
w.write_kv_data_to_file()
w.write_tensors_to_file()
w.close()
