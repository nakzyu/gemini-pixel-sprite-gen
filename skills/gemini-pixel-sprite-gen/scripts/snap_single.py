#!/usr/bin/env python3
"""Snap a Gemini-generated sprite source to a chunky low-res game-ready frame.

Output: <out-dir>/<char>_<action>.png  (only artifact — drop straight into game)

Usage:
  snap_single.py <src_png> <char> <action> [--out-dir DIR] [--target-h N] [--cell-h N] [--top-crop N]

Notes:
- DEFAULT target_h=32 — chunky low-res look that matches the locked-in style
  for upright poses (idle, walk).
- For BENT/CROUCHED poses (forward-stab attack, dive), the source character is
  shorter so h32 makes pixels too fine. Try target-h 28-30 and pick visually.
- Pipeline: tight bbox -> mode-downsample (per-block majority opaque color) ->
  binary alpha -> keep largest connected component -> outline pass (alpha-edge
  pixels recolored with darkest-in-block) -> bottom-center align with feet-x
  centering -> cell_w = round_up_16(feet_extent*2 + pad*2), cell_h = 48.
- After snapping new actions, run normalize_sheets.py to per-character pad all
  action sheets to a common cell.
"""
import argparse
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from scipy import ndimage

cell_h, PAD, UPSCALE = 48, 4, 8


def depixelize(src_arr, target_h):
    A = src_arr[..., 3]
    ys, xs = np.where(A > 10)
    tight = src_arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    src_h, src_w = tight.shape[:2]
    target_w = max(1, int(round(src_w * target_h / src_h)))
    out = np.zeros((target_h, target_w, 4), dtype=np.uint8)
    dark = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    for i in range(target_h):
        y0 = int(i * src_h / target_h)
        y1 = max(y0 + 1, int((i + 1) * src_h / target_h))
        for j in range(target_w):
            x0 = int(j * src_w / target_w)
            x1 = max(x0 + 1, int((j + 1) * src_w / target_w))
            block = tight[y0:y1, x0:x1]
            opq = block[block[..., 3] > 200]
            if len(opq) > block.shape[0] * block.shape[1] * 0.4:
                pixels = [tuple(p[:3]) for p in opq]
                r, g, b = Counter(pixels).most_common(1)[0][0]
                out[i, j] = (r, g, b, 255)
                lum = 0.299 * opq[:, 0] + 0.587 * opq[:, 1] + 0.114 * opq[:, 2]
                dark[i, j] = opq[np.argmin(lum)][:3]
    mask = out[..., 3] > 0
    labels, n = ndimage.label(mask)
    if n > 1:
        sizes = ndimage.sum(mask, labels, range(1, n + 1))
        keep = 1 + int(np.argmax(sizes))
        out[~(labels == keep)] = 0
        mask = out[..., 3] > 0
    pad = np.pad(mask, 1, constant_values=False)
    edge = mask & (
        ~pad[:-2, 1:-1] | ~pad[2:, 1:-1] | ~pad[1:-1, :-2] | ~pad[1:-1, 2:]
    )
    out[edge, :3] = dark[edge]
    out[edge, 3] = 255
    return out


def feet_center_x(arr):
    A = arr[..., 3]
    H = A.shape[0]
    xs = np.where(A[int(H * 0.9):, :] > 10)[1]
    return arr.shape[1] / 2 if not len(xs) else (xs.min() + xs.max()) / 2


def round_up_16(n):
    return n if n % 16 == 0 else n + 16 - (n % 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("char")
    ap.add_argument("action")
    ap.add_argument("--out-dir", default="./sprites/sheets",
                    help="Output directory (default: ./sprites/sheets relative to cwd)")
    ap.add_argument("--target-h", type=int, default=32,
                    help="Native character height in pixels (default 32; "
                         "lower for bent poses)")
    ap.add_argument("--top-crop", type=int, default=0,
                    help="Trim N rows off the TOP of the source tight-bbox "
                         "before snapping. Use to drop overlong hair/halo so "
                         "the face gets more dest pixels (eyes survive at h32)")
    ap.add_argument("--cell-h", type=int, default=48,
                    help="Cell height (default 48 for characters; use higher "
                         "like 64 for tall monsters / large creatures)")
    a = ap.parse_args()

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cell_h = a.cell_h

    src_arr = np.array(Image.open(a.src).convert("RGBA"))
    if a.top_crop:
        A = src_arr[..., 3]
        ys, xs = np.where(A > 10)
        y0, y1 = ys.min(), ys.max() + 1
        x0, x1 = xs.min(), xs.max() + 1
        src_arr = src_arr[y0 + a.top_crop:y1, x0:x1]
    native = depixelize(src_arr, a.target_h)
    A = native[..., 3]
    ys, xs = np.where(A > 0)
    native = native[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    nh, nw = native.shape[:2]
    fx = feet_center_x(native)
    half = max(fx, nw - fx)
    cell_w = round_up_16(int(np.ceil(half * 2)) + PAD * 2)
    canvas = np.zeros((cell_h, cell_w, 4), dtype=np.uint8)
    x0 = int(round(cell_w / 2 - fx))
    y0 = cell_h - nh - PAD
    canvas[y0:y0 + nh, x0:x0 + nw] = native

    out_n = out_dir / f"{a.char}_{a.action}.png"
    Image.fromarray(canvas).save(out_n)
    print(f"{a.action}: cell={cell_w}x{cell_h} char={nw}x{nh} feet_x={fx:.1f} "
          f"-> {out_n.name}")


if __name__ == "__main__":
    main()
