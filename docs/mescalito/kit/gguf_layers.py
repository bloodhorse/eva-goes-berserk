#!/usr/bin/env python3
"""Rewrite a (quantized) gguf with its transformer blocks in a new order.

  gguf_layers.py in.gguf out.gguf "0-29,20-29,30-63"

Blocks are copied byte-for-byte (Q4_K_M stays Q4_K_M, no requantization, no f16 download),
renumbered 0..N-1, and `<arch>.block_count` is set to N. A per-layer array such as
`<arch>.attention.sliding_window_pattern` is re-laid in the same order, so each copied block
keeps the attention type (sliding / full) it was trained with -- a repeated full-attention layer
must stay full, or its rope and mask change underneath it.

Written for olmo2 (OLMo 2 / OLMo 3) but arch-agnostic for any gguf whose only per-layer
metadata is arrays of length block_count.
"""
import sys
import re
import numpy as np
import gguf


def parse_order(spec: str) -> list[int]:
    out = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            a, b = map(int, part.split('-'))
            out += list(range(a, b + 1))
        else:
            out.append(int(part))
    return out


def main():
    src, dst, spec = sys.argv[1:4]
    order = parse_order(spec)
    r = gguf.GGUFReader(src)
    arch = r.get_field('general.architecture').contents()
    n_old = r.get_field(f'{arch}.block_count').contents()
    assert all(0 <= i < n_old for i in order), 'layer index out of range'

    w = gguf.GGUFWriter(dst, arch)
    for f in r.fields.values():
        if f.name == 'general.architecture' or f.name.startswith('GGUF.'):
            continue
        vt = f.types[0]
        sub = f.types[-1] if vt == gguf.GGUFValueType.ARRAY else None
        val = f.contents()
        if f.name == f'{arch}.block_count':
            val = len(order)
        elif vt == gguf.GGUFValueType.ARRAY and isinstance(val, list) and len(val) == n_old \
                and not f.name.startswith('tokenizer.'):
            # per-layer array: follow the blocks
            val = [val[i] for i in order]
        w.add_key_value(f.name, val, vt, sub_type=sub)

    blk = re.compile(r'^blk\.(\d+)\.(.+)$')
    by_layer: dict[int, list] = {}
    rest = []
    for t in r.tensors:
        m = blk.match(t.name)
        if m:
            by_layer.setdefault(int(m.group(1)), []).append((m.group(2), t))
        else:
            rest.append((t.name, t))

    plan = [(name, t) for name, t in rest if not name.startswith('output')]
    for new_i, old_i in enumerate(order):
        plan += [(f'blk.{new_i}.{suffix}', t) for suffix, t in by_layer[old_i]]
    plan += [(name, t) for name, t in rest if name.startswith('output')]

    for name, t in plan:
        w.add_tensor_info(name, t.data.shape, t.data.dtype, t.data.nbytes, t.tensor_type)
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_ti_data_to_file()
    for name, t in plan:
        w.write_tensor_data(t.data, tensor_endianess=r.endianess)
    w.close()
    print(f'{src}: {n_old} blocks -> {dst}: {len(order)} blocks')


if __name__ == '__main__':
    main()
