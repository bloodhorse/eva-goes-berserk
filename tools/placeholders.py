"""Procedural stand-in images for the sketch, so we never borrow anyone's art while real images don't exist yet.

Writes grayscale RGBA sources into sketch/src/; crush.py turns them into palette images.
Delete this once real images arrive.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = 'sketch/src'
rng = np.random.default_rng(7)


def moon(size=520):
    y, x = np.mgrid[:size, :size] / size - 0.5
    r = np.hypot(x, y)
    disc = np.clip((0.36 - r) * 60, 0, 1)
    # light from the upper left, mottled surface so the dither has something to chew on
    shade = np.clip(0.55 - (x + y) * 0.9, 0.08, 1) * (0.85 + 0.15 * rng.standard_normal((size, size)).clip(-1, 1))
    halo = np.clip(1 - (r - 0.36) / 0.14, 0, 1) ** 2 * 0.35
    lum = np.where(disc > 0, shade, 0.35)
    alpha = np.maximum(disc, halo)
    return np.dstack([lum, alpha])


def water(w=960, h=380):
    y, x = np.mgrid[:h, :w].astype(float)
    t = y / h
    ripple = 0.5 + 0.5 * np.sin(x / 9 + np.sin(y / 5) * 3 + y * 0.9)
    lum = 0.1 + 0.35 * t + 0.25 * ripple * t
    # a broken moon-path straight down the middle
    path = np.exp(-((x - w / 2) / (40 + 90 * t)) ** 2) * (ripple > 0.55)
    lum = np.clip(lum + path * 0.6, 0, 1)
    alpha = np.clip(t * 3, 0, 1)
    return np.dstack([lum, alpha])


def pylon(w=320, h=860):
    img = Image.new('LA', (w, h), (0, 0))
    d = ImageDraw.Draw(img)
    cx, top, base = w // 2, 40, h - 10
    half = lambda yy: 14 + (yy - top) / (base - top) * (w * 0.38)
    legs = [(cx - half(yy), yy) for yy in range(top, base, 4)], [(cx + half(yy), yy) for yy in range(top, base, 4)]
    d.line(legs[0], fill=(200, 255), width=5)
    d.line(legs[1], fill=(120, 255), width=5)
    yy, flip = top, 0
    while yy < base - 50:
        ny = yy + 30 + (yy - top) * 0.06
        a, b = (cx - half(yy), yy), (cx + half(ny), ny)
        if flip:
            a, b = (cx + half(yy), yy), (cx - half(ny), ny)
        d.line([a, b], fill=(160, 255), width=2)
        flip ^= 1
        yy = ny
    for arm_y, span in ((130, 1.9), (250, 1.5)):
        hw = half(arm_y) * span
        d.line([(cx - hw, arm_y), (cx + hw, arm_y)], fill=(230, 255), width=6)
        for s in (-1, 1):
            d.line([(cx + s * hw, arm_y), (cx + s * hw, arm_y + 40)], fill=(90, 255), width=2)
    a = np.asarray(img).astype(float) / 255
    return np.dstack([a[..., 0], a[..., 1]])


for name, arr in (('moon', moon()), ('water', water()), ('pylon', pylon())):
    lum, alpha = (arr[..., 0] * 255).astype(np.uint8), (arr[..., 1] * 255).astype(np.uint8)
    Image.fromarray(np.dstack([lum, lum, lum, alpha]), 'RGBA').save(f'{OUT}/{name}.png')
    print('wrote', name)
