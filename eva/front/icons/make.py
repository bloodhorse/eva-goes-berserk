#!/usr/bin/env -S uv run --python 3.12
"""make.py — the three home-screen icons, written by hand.

    uv run --python 3.12 eva/front/icons/make.py

Stdlib only, like everything else in this tree: `zlib` and `struct` are the whole of a PNG
writer, and ImageMagick is on this mac but not on the next one — an icon that needs a brew
package to regenerate is an icon nobody regenerates. Run once; the three PNGs it writes are
committed, so this script exists to say what the mark IS, not because a build step needs it.

The mark: one stem and three strokes fanning off it — a fan, which is the whole instrument.
Drawn as capsules (a segment plus a radius) and rasterised by distance, so the edges are
antialiased analytically and there is no supersampling loop to wait on. Full-bleed square on
the page's charcoal ground, in the lilac accent, no transparency and no rounded corners: iOS
masks the square itself, and an icon that arrives pre-rounded gets rounded twice.
"""

from __future__ import annotations

import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))

# Straight off loom.html's :root — the dark room's ground and its one accent.
BG = (0x23, 0x23, 0x23)
FG = (0xF5, 0xC8, 0xFE)

# Everything below is in fractions of the icon's side, so one geometry serves 180 and 512.
FORK = (0.50, 0.545)                  # where the stem opens into the fan
STROKES = [
    ((0.50, 0.815), FORK),            # the stem, from the foot up to the fork
    (FORK, (0.255, 0.225)),           # and three branches off it, fanning left to right
    (FORK, (0.50, 0.185)),
    (FORK, (0.745, 0.225)),
]
WIDTH = 0.076                         # stroke width; at 60px this is ~4.5px and still reads


def _dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Distance from a point to a segment — the capsule's whole definition."""
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


def raster(size: int) -> bytes:
    """One PNG's worth of RGB rows, each prefixed with filter byte 0 (none)."""
    r = WIDTH * size / 2.0
    segs = [(a[0] * size, a[1] * size, b[0] * size, b[1] * size) for a, b in STROKES]
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        py = y + 0.5
        for x in range(size):
            px = x + 0.5
            d = min(_dist(px, py, *s) for s in segs)
            # one pixel of ramp across the edge: coverage 1 inside, 0 outside, linear between
            a = r + 0.5 - d
            a = 0.0 if a < 0.0 else (1.0 if a > 1.0 else a)
            for c in range(3):
                rows.append(int(BG[c] + (FG[c] - BG[c]) * a + 0.5))
    return bytes(rows)


def png(size: int) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)   # 8-bit, colour type 2 = RGB
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raster(size), 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    for n in (180, 192, 512):
        path = os.path.join(HERE, f"icon-{n}.png")
        with open(path, "wb") as f:
            f.write(png(n))
        print(f"{path}  {os.path.getsize(path)} bytes")
