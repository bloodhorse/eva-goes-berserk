# per-layer residual RMS for olmo2-arch ggufs, read out of a stock llama-imatrix file.
# works only because olmo 2/3 has NO pre-norm: blk.L.attn_q's input is the raw residual
# entering block L, i.e. l_out of block L-1 -- so imatrix's in_sum2 is that residual's
# per-dimension sum of squares. on a pre-norm model (llama, mistral) this reads the
# normed input instead and the numbers are useless for scaling a cvec.
# out: rms.npy [n_layer] (per-element RMS of l_out-k) and diag.npy [n_layer, n_embd]
# (per-dimension RMS: a diagonal "covariance" to shape noise on-manifold-lite).
import sys, numpy as np, gguf

r = gguf.GGUFReader(sys.argv[1])
t = {x.name: x for x in r.tensors}
n_layer = 1 + max(int(n.split(".")[1]) for n in t if n.startswith("blk."))

def sq(name):
    s2 = np.asarray(t[f"{name}.in_sum2"].data, dtype=np.float64).reshape(-1)
    c = float(np.asarray(t[f"{name}.counts"].data).reshape(-1)[0])
    return s2 / c                                   # mean x^2 per input dimension

diag = []
for k in range(n_layer):
    # l_out-k enters block k+1; the last block has no successor -> its mid-layer ffn input
    src = f"blk.{k+1}.attn_q.weight" if k + 1 < n_layer else f"blk.{k}.ffn_up.weight"
    diag.append(np.sqrt(sq(src)))
diag = np.stack(diag).astype(np.float32)
rms = np.sqrt((diag ** 2).mean(axis=1)).astype(np.float32)
np.save("diag.npy", diag); np.save("rms.npy", rms)
for k in range(0, n_layer, 8):
    top = np.sort(diag[k])[-3:][::-1]
    print(f"l_out-{k:2d}  rms {rms[k]:9.3f}  |h| {rms[k]*np.sqrt(diag.shape[1]):10.1f}  top dims {top.round(1)}")
