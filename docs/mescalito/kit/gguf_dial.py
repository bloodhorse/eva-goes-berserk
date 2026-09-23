#!/usr/bin/env python3
"""Multiply F32 norm vectors of an olmo2-arch gguf IN PLACE. Work on a copy (cp -c on apfs is free).

  gguf_dial.py model.gguf attn_q_norm   0.7  "all"          # attention temperature 1/0.7 everywhere
  gguf_dial.py model.gguf attn_q_norm   1.3  "16-47"        # sharper attention, middle layers
  gguf_dial.py model.gguf attn_q_norm   0.5  "all" "0-9"    # only heads 0..9 of every layer
  gguf_dial.py model.gguf post_attention_norm 0 "30-33"     # exact skip of the attention sublayer
  gguf_dial.py model.gguf post_ffw_norm 1.5 "20-40"          # louder mlp writes

Why this is a free dial on olmo2 (OLMo 2 / OLMo 3):
- q is RMS-normed over the whole 5120-wide vector *before* rope, and the norm weight is a
  plain f32 vector in the gguf (llama-quantize never quantizes 1-d tensors). q.k is linear in q,
  rope is a rotation, so weight*a => every attention logit in that layer *a. That is attention
  temperature 1/a with no code patch. Slicing the vector by head (128 dims each) gives per-head
  temperature.
- olmo2 normalizes each sublayer's OUTPUT (post_attention_norm / post_ffw_norm) before adding
  it to the residual. weight*b => that sublayer writes b times as loud; b=0 is an exact skip of
  that sublayer (both at 0 = the whole block is an identity), keeping the gguf's block count.
"""
import sys
import numpy as np
import gguf


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
    heads = sys.argv[5] if len(sys.argv) > 5 else None
    # optional rope frequency band (0 = fastest-rotating pair .. hd/2-1 = slowest); olmo2 uses
    # neox rope, so band index i owns dims i and i+hd/2 of each head
    band = sys.argv[6] if len(sys.argv) > 6 else None
    factor = float(factor)
    r = gguf.GGUFReader(path, 'r+')
    arch = r.get_field('general.architecture').contents()
    n = r.get_field(f'{arch}.block_count').contents()
    hd = r.get_field(f'{arch}.embedding_length').contents() // r.get_field(f'{arch}.attention.head_count').contents()
    names = {t.name: t for t in r.tensors}
    for il in rng(layers, n):
        t = names[f'blk.{il}.{family}.weight']
        assert t.tensor_type == gguf.GGMLQuantizationType.F32, t.tensor_type
        v = t.data  # memmap view, writes go straight to the file
        if heads is None or heads == 'all':
            hs = rng('all', v.shape[0] // hd)
        else:
            hs = rng(heads, v.shape[0] // hd)
        for h in hs:
            if band is None:
                v[h * hd:(h + 1) * hd] *= np.float32(factor)
            else:
                for i in rng(band, hd // 2):
                    v[h * hd + i] *= np.float32(factor)
                    v[h * hd + i + hd // 2] *= np.float32(factor)
    r.data.flush()
    print(f'{family} x{factor} on layers {layers}' + (f' heads {heads}' if heads else ''))


if __name__ == '__main__':
    main()
