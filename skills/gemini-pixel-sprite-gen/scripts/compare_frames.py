#!/usr/bin/env python3
"""Consistency check — compare a NEW frame against the locked idle, side by side.

The qc gate only catches MECHANICAL failures (clip / transparency / size). It does
NOT check whether the new frame is the SAME CHARACTER as the idle. That's a human
(Claude) judgment call, and skipping it leads to praising frames whose hair length,
proportions, face, or palette have drifted.

This scales both images to the same figure height and overlays quarter guide lines,
so you can directly eyeball:
  - hair length & style
  - head-to-body ratio (chibi-ness)
  - face / eyes
  - palette

Run it for EVERY non-idle frame before showing the user, and state any drift plainly.

Usage:
  compare_frames.py <idle.png> <frame.png> [--out PATH] [--height 600]
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw


def bbox_crop(path):
    im = Image.open(path).convert("RGBA")
    ys, xs = np.where(np.asarray(im)[..., 3] > 180)
    if len(ys) == 0:
        return im
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("idle")
    ap.add_argument("frame")
    ap.add_argument("--out", default="/tmp/frame_vs_idle.png")
    ap.add_argument("--height", type=int, default=600)
    a = ap.parse_args()

    H = a.height
    sh = lambda im: im.resize((max(1, int(im.width * H / im.height)), H), Image.LANCZOS)
    I, F = sh(bbox_crop(a.idle)), sh(bbox_crop(a.frame))

    gap, lh = 40, 22
    cv = Image.new("RGBA", (I.width + F.width + gap * 3, H + lh + 8), (245, 245, 245, 255))
    d = ImageDraw.Draw(cv)
    cv.paste(I, (gap, lh), I)
    cv.paste(F, (gap * 2 + I.width, lh), F)
    d.text((gap, 4), "IDLE (locked)", fill=(0, 0, 0, 255))
    d.text((gap * 2 + I.width, 4), "NEW FRAME", fill=(0, 0, 0, 255))
    for f in (0, .25, .5, .75, 1.0):                       # quarter guide lines
        y = lh + int(H * (1 - 1e-9) * f) if f == 1.0 else lh + int(H * f)
        d.line((0, y, cv.width, y), fill=(205, 180, 180, 255))
    cv.save(a.out)
    print(f"saved {a.out}  (idle figW {I.width}, frame figW {F.width})")
    print("CHECK: hair length/style · head-to-body ratio (chibi) · face/eyes · palette")


if __name__ == "__main__":
    main()
