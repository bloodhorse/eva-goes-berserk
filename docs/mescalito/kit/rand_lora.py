# write a random LoRA adapter for an olmo2-arch gguf: stochastic low-rank weight noise that
# stock llama-server can switch per request ("lora":[{"id":k,"scale":s}]) or globally
# between chunks (POST /lora-adapters, KV cache kept). delta W = B @ A on the chosen tensor.
#   --mode noise : A, B gaussian -> a random rank-r perturbation, input-gated
#   --mode wire  : A = one-hot rows on r random MLP neurons, B = random directions ->
#                  "when neuron j fires, it also writes u_j" (needs --target ffn_down)
import argparse, numpy as np, gguf

p = argparse.ArgumentParser()
p.add_argument("out")
p.add_argument("--target", default="ffn_down")          # ffn_down | attn_output | ffn_up ...
p.add_argument("--n-in", type=int, default=27648)       # ffn_down input = MLP hidden
p.add_argument("--n-out", type=int, default=5120)
p.add_argument("--n-layer", type=int, default=64)
p.add_argument("--layers", default="0-63")
p.add_argument("--rank", type=int, default=8)
p.add_argument("--mode", default="noise", choices=["noise", "wire"])
p.add_argument("--seed", type=int, default=0)
a = p.parse_args()

rng = np.random.default_rng(a.seed)
lo, hi = map(int, a.layers.split("-"))
w = gguf.GGUFWriter(a.out, "olmo2")                     # must equal the model's arch string
w.add_string("general.type", "adapter")
w.add_string("adapter.type", "lora")
w.add_float32("adapter.lora.alpha", float(a.rank))      # alpha/rank = 1 -> request scale is the dial
for L in range(lo, hi + 1):
    if a.mode == "noise":
        A = (rng.standard_normal((a.rank, a.n_in)) / np.sqrt(a.n_in)).astype(np.float32)
    else:
        A = np.zeros((a.rank, a.n_in), dtype=np.float32)
        A[np.arange(a.rank), rng.choice(a.n_in, a.rank, replace=False)] = 1.0
    B = (rng.standard_normal((a.n_out, a.rank)) / np.sqrt(a.n_out)).astype(np.float32)
    # numpy (r, n_in) -> ggml ne [n_in, r]; numpy (n_out, r) -> ne [r, n_out]: what the loader checks
    w.add_tensor(f"blk.{L}.{a.target}.weight.lora_a", A)
    w.add_tensor(f"blk.{L}.{a.target}.weight.lora_b", B)
w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
