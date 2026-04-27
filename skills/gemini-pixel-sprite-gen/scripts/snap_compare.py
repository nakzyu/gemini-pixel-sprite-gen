#!/usr/bin/env python3
"""Generate a side-by-side compare grid of snap variations for one source.

Use when a single snap looks off and you want to eyeball which target_h or
top_crop produces the best result. Shows tiles labeled with each setting,
saves to <out-dir>/<name>_compare.png, and prints the path.

Usage:
  snap_compare.py <src_png> [--out-dir DIR] [--name NAME] [--cell-h N]
                  [--target-h-range START STOP STEP]
                  [--top-crop-range START STOP STEP]

Examples:
  # Sweep h from 20 to 36 in steps of 2 (no top crop):
  snap_compare.py src.png --target-h-range 20 36 2

  # Sweep top-crop from 0 to 200 in steps of 20 at fixed h32:
  snap_compare.py src.png --top-crop-range 0 200 20

  # 2D sweep: h x top-crop grid:
  snap_compare.py src.png --target-h-range 28 36 2 --top-crop-range 0 100 20
"""
import argparse
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

PAD, UPSCALE = 4, 8


def depixelize(tight, target_h):
    sh, sw = tight.shape[:2]
    tw = max(1, int(round(sw * target_h / sh)))
    out = np.zeros((target_h, tw, 4), dtype=np.uint8)
    dark = np.zeros((target_h, tw, 3), dtype=np.uint8)
    for i in range(target_h):
        y0 = int(i * sh / target_h)
        y1 = max(y0 + 1, int((i + 1) * sh / target_h))
        for j in range(tw):
            x0 = int(j * sw / tw)
            x1 = max(x0 + 1, int((j + 1) * sw / tw))
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


def feet_x(arr):
    A = arr[..., 3]
    H = A.shape[0]
    xs = np.where(A[int(H * 0.9):, :] > 10)[1]
    return arr.shape[1] / 2 if not len(xs) else (xs.min() + xs.max()) / 2


def round_up_16(n):
    return n if n % 16 == 0 else n + 16 - (n % 16)


def render_one(tight_full, top_crop, target_h, cell_h):
    tight = tight_full[top_crop:] if top_crop else tight_full
    if tight.shape[0] < 20:
        return None
    native = depixelize(tight, target_h)
    A = native[..., 3]
    ys, xs = np.where(A > 0)
    if not len(ys):
        return None
    native = native[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    nh, nw = native.shape[:2]
    if nh > cell_h - PAD:
        return None  # won't fit
    fx = feet_x(native)
    half = max(fx, nw - fx)
    cw = round_up_16(int(np.ceil(half * 2)) + PAD * 2)
    canvas = np.zeros((cell_h, cw, 4), dtype=np.uint8)
    x0 = int(round(cw / 2 - fx))
    y0 = cell_h - nh - PAD
    canvas[y0:y0 + nh, x0:x0 + nw] = native
    return (nw, nh, canvas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out-dir", default="/tmp")
    ap.add_argument("--name", default=None,
                    help="Output filename stem (default: derived from src)")
    ap.add_argument("--cell-h", type=int, default=48)
    ap.add_argument("--target-h-range", nargs=3, type=int, metavar=("START", "STOP", "STEP"),
                    default=None,
                    help="Range of target_h to sweep, e.g. 20 36 2 -> [20, 22, 24, ..., 34]")
    ap.add_argument("--top-crop-range", nargs=3, type=int, metavar=("START", "STOP", "STEP"),
                    default=None,
                    help="Range of top_crop to sweep")
    a = ap.parse_args()

    if not a.target_h_range and not a.top_crop_range:
        a.target_h_range = [24, 38, 2]  # sensible default sweep

    th_values = list(range(*a.target_h_range)) if a.target_h_range else [32]
    tc_values = list(range(*a.top_crop_range)) if a.top_crop_range else [0]

    src = np.array(Image.open(a.src).convert("RGBA"))
    A = src[..., 3]
    ys, xs = np.where(A > 10)
    tight_full = src[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    print(f"src tight: {tight_full.shape[1]}x{tight_full.shape[0]}")

    # Render grid: rows = top_crop values, cols = target_h values
    rendered = []
    max_cw = 0
    for tc in tc_values:
        row = []
        for th in th_values:
            r = render_one(tight_full, tc, th, a.cell_h)
            if r is not None:
                max_cw = max(max_cw, r[2].shape[1])
            row.append((th, tc, r))
        rendered.append(row)

    label_h = 32
    gap = 16 * UPSCALE
    tile_w = max_cw * UPSCALE
    tile_h = a.cell_h * UPSCALE + label_h
    cols = len(th_values)
    rows = len(tc_values)
    total_w = tile_w * cols + gap * (cols - 1)
    total_h = tile_h * rows + gap * max(0, rows - 1)
    out = Image.new("RGBA", (total_w, total_h), (40, 40, 40, 255))
    draw = ImageDraw.Draw(out)
    for ri, row in enumerate(rendered):
        for ci, (th, tc, r) in enumerate(row):
            x = ci * (tile_w + gap)
            y = ri * (tile_h + gap)
            label = f"h{th} crop={tc}" if rows > 1 or len(tc_values) > 1 else f"h{th}"
            if r is None:
                draw.text((x + 4, y + 4), f"{label} [no fit]", fill=(180, 80, 80, 255))
                continue
            nw, nh, canvas = r
            cw_t = canvas.shape[1]
            img = Image.fromarray(canvas).resize(
                (cw_t * UPSCALE, a.cell_h * UPSCALE), Image.NEAREST
            )
            offx = (tile_w - img.size[0]) // 2
            draw.text((x + 4, y + 4), f"{label}  {nw}x{nh}", fill=(255, 255, 255, 255))
            out.paste(img, (x + offx, y + label_h), img)

    name = a.name or Path(a.src).stem + "_compare"
    out_path = Path(a.out_dir) / f"{name}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    print(f"saved {out_path} ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()
