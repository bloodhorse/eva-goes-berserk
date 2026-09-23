#!/usr/bin/env python3
"""Multiply a QUANTIZED gguf tensor by a scalar IN PLACE, by rescaling its block scales only.

  gguf_gain.py model.gguf attn_q 0.8 "all"      # every blk.N.attn_q.weight x0.8
  gguf_gain.py model.gguf ffn_down 1.3 "10-25"

k-quants and q8_0 dequantize as  w = d * (sub-scale * q) - dmin * (sub-min)  (q8_0: w = d*q).
Multiplying the fp16 super-block factors d (and dmin) by a multiplies every dequantized weight by
a, exactly up to fp16 rounding of d -- no requantization, no f16 download. This is the arch-
agnostic twin of gguf_dial.py: on a model with no f32 norm to grab (llama, mistral: pre-norm,
no qk-norm), attn_q x a is attention temperature 1/a, and attn_output / ffn_down x b is the
sublayer gain that mergekit's passthrough `scale` gives at f16.
Work on a copy (cp -c on apfs is free).
"""
import sys
import numpy as np
import gguf

Q = gguf.GGMLQuantizationType
# (block bytes, list of byte offsets of fp16 factors inside a block)
LAYOUT = {
    Q.Q4_K: (144, [0, 2]),   # d, dmin, scales[12], qs[128]
    Q.Q5_K: (176, [0, 2]),   # d, dmin, scales[12], qh[32], qs[128]
    Q.Q6_K: (210, [208]),    # ql[128], qh[64], scales[16], d
    Q.Q8_0: (34, [0]),       # d, qs[32]
    Q.Q4_0: (18, [0]),       # d, qs[16]
}


def rng(spec, n):
    if spec == 'all':
        return list(range(n))
    out = []
    for p in spec.split(','):
        a, _, b = p.partition('-')
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    path, family, factor, layers = sys.argv[1:5]
    factor = float(factor)
    r = gguf.GGUFReader(path, 'r+')
    arch = r.get_field('general.architecture').contents()
    n = r.get_field(f'{arch}.block_count').contents()
    names = {t.name: t for t in r.tensors}
    for il in rng(layers, n):
        t = names[f'blk.{il}.{family}.weight']
        if t.tensor_type == Q.F32 or t.tensor_type == Q.F16:
            t.data[...] *= factor
            continue
        bs, offs = LAYOUT[t.tensor_type]
        raw = t.data.reshape(-1)          # uint8 memmap view
        blocks = raw.reshape(-1, bs)
        for o in offs:
            f = blocks[:, o:o + 2].copy().view(np.float16).reshape(-1)
            f = (f.astype(np.float32) * factor).astype(np.float16)
            blocks[:, o:o + 2] = f.view(np.uint8).reshape(-1, 2)
    r.data.flush()
    print(f'{family} x{factor} on layers {layers}')


if __name__ == '__main__':
    main()
