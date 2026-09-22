"""Crush an image into a dream palette: luminance -> ordered (bayer) dither across the palette.

The palette is what makes images from anywhere read as one world, so every image
goes through here before it reaches a dream. Ordered dither (not error diffusion)
on purpose: its regular grid reads as "screen", and it stays stable between
animation frames instead of boiling.

usage: crush.py in.png out.png "#0b0d12 #23384a #6f9fb0 #cdd3c4" [--clear-dark]
  palette: any order, sorted by brightness here
  --clear-dark: the darkest color becomes transparent, so lower layers show through
"""
import sys
import numpy as np
from PIL import Image

BAYER8 = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21],
]) / 64.0


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def crush(src, palette, clear_dark=False):
    pal = sorted((hex2rgb(p) for p in palette), key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])
    rgba = np.asarray(src.convert('RGBA')).astype(float)
    lum = (0.299 * rgba[..., 0] + 0.587 * rgba[..., 1] + 0.114 * rgba[..., 2]) / 255.0
    h, w = lum.shape
    thresh = np.tile(BAYER8, (h // 8 + 1, w // 8 + 1))[:h, :w]
    # position between palette steps; the bayer threshold decides which neighbor each pixel takes
    steps = lum * (len(pal) - 1)
    idx = np.clip(np.floor(steps + thresh).astype(int), 0, len(pal) - 1)
    out = np.zeros((h, w, 4), np.uint8)
    for i, c in enumerate(pal):
        out[idx == i] = (*c, 255)
    # source alpha is dithered too, so soft edges dissolve into dots instead of a hard cut
    alpha = rgba[..., 3] / 255.0
    # <= not <: with <, fully transparent pixels survive wherever the threshold is 0 → a faint box around every image
    out[alpha <= thresh] = 0
    if clear_dark:
        out[idx == 0] = 0
    return Image.fromarray(out, 'RGBA')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    crush(Image.open(sys.argv[1]), sys.argv[3].split(), '--clear-dark' in sys.argv).save(sys.argv[2])
