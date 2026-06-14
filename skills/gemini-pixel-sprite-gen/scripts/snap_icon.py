#!/usr/bin/env python3
"""Snap a Gemini-generated icon source to a clean square pixel-art icon.

Icons differ from character sprites:
- CENTERED in a SQUARE cell (not bottom-aligned like a standing character).
- The LONGER side is fit to the target size (aspect kept) — a tall sword and a
  wide shield both end up inside the same square.
- ALL parts are kept by default (an icon is often multiple disjoint shapes — a
  flame plus a spark, a coin plus a glint). Pass --largest for single-blob icons.

Reuses the same outline-preserving mode-downsample as character sprites
(snap_single.depixelize) so icons read as the SAME chunky pixel-art family.

Output: <out-dir>/<name>.png  (size x size, transparent bg, drop into the game)

Usage:
  snap_icon.py <src_png> <name> [--out-dir DIR] [--size N] [--pad N] [--largest]

Notes:
- Generate the source WITHOUT --opaque (icons need a transparent subject), so
  sprite_gen.py chromakeys the green bg out before this snap.
- Default --size 32 reads well for element/status/skill icons at the chunky
  scale. Use 48/64 for larger item icons.
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
from snap_single import depixelize


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("name")
    ap.add_argument("--out-dir", default="./sprites/icons",
                    help="Output directory (default: ./sprites/icons)")
    ap.add_argument("--size", type=int, default=32,
                    help="Square cell size in px (default 32). The icon art is "
                         "fit inside size-2*pad on its longer side, then centered.")
    ap.add_argument("--pad", type=int, default=1,
                    help="Transparent margin inside the square (default 1).")
    ap.add_argument("--largest", action="store_true",
                    help="Keep ONLY the largest component. Default keeps all "
                         "parts (icons are often multi-piece).")
    a = ap.parse_args()

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fit = max(1, a.size - 2 * a.pad)

    src = np.array(Image.open(a.src).convert("RGBA"))
    A = src[..., 3]
    ys, xs = np.where(A > 10)
    if not len(ys):
        raise SystemExit("snap_icon: source is fully transparent")
    sh = ys.max() - ys.min() + 1
    sw = xs.max() - xs.min() + 1
    # Fit the LONGER side to `fit` (depixelize fits HEIGHT -> target_h).
    target_h = fit if sh >= sw else max(1, int(round(fit * sh / sw)))

    native = depixelize(src, target_h, keep_all=not a.largest)
    A = native[..., 3]
    ys, xs = np.where(A > 0)
    native = native[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    nh, nw = native.shape[:2]
    # Safety: never exceed the cell (rounding can push 1px over).
    if nh > a.size or nw > a.size:
        cy, cx = nh // 2, nw // 2
        h = min(nh, a.size); w = min(nw, a.size)
        native = native[cy - h // 2: cy - h // 2 + h, cx - w // 2: cx - w // 2 + w]
        nh, nw = native.shape[:2]

    canvas = np.zeros((a.size, a.size, 4), dtype=np.uint8)
    y0 = (a.size - nh) // 2
    x0 = (a.size - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = native

    out = out_dir / f"{a.name}.png"
    Image.fromarray(canvas).save(out)
    print(f"icon {a.name}: {a.size}x{a.size} art={nw}x{nh} -> {out.name}")


if __name__ == "__main__":
    main()
