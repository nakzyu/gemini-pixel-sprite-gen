#!/usr/bin/env python3
"""Snap a Gemini-generated OPAQUE scene to a game-ready background.

Backgrounds differ from sprites:
- NO transparency. Generate the source with `sprite_gen.py ... --opaque` so the
  green-bg instruction is skipped and the scene is kept whole.
- They fill a FIXED viewport: cover-fit + center-crop to the target aspect
  (Gemini won't return an exact 9:16 image; this fixes the framing).
- They get CHUNKED to coarse pixels so the look matches the chunky low-res
  sprites: downscale to W/block x H/block then NEAREST-upscale back, so every
  "pixel" is a block x block square.

Output: <out-dir>/<name>.png  (W x H, opaque, drop straight into the engine)

Usage:
  snap_bg.py <src_png> <name> [--out-dir DIR] [--size WxH] [--block N] [--no-chunk]

Notes:
- Default --size 360x640 = this project's portrait viewport (project.godot).
- --block 2 (default) gives a clearly chunky-but-readable background; 1 = smooth
  downscale, 3-4 = very coarse. Match it to how chunky the sprites read.
"""
import argparse
from pathlib import Path
from PIL import Image


def parse_size(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("name")
    ap.add_argument("--out-dir", default="./sprites/backgrounds",
                    help="Output directory (default: ./sprites/backgrounds)")
    ap.add_argument("--size", default="360x640",
                    help="Target WxH (default 360x640 = the game viewport).")
    ap.add_argument("--block", type=int, default=2,
                    help="Pixel-chunk factor: downscale to W/block x H/block then "
                         "NEAREST-upscale back, so each pixel is block x block "
                         "(default 2). 1 = no chunk.")
    ap.add_argument("--no-chunk", action="store_true",
                    help="Disable chunking (smooth cover-fit only).")
    a = ap.parse_args()

    W, H = parse_size(a.size)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    im = Image.open(a.src).convert("RGB")
    sw, sh = im.size
    # cover-fit: scale so the source fully covers WxH, then center-crop.
    scale = max(W / sw, H / sh)
    rw, rh = max(W, int(round(sw * scale))), max(H, int(round(sh * scale)))
    im = im.resize((rw, rh), Image.LANCZOS)
    left = (rw - W) // 2
    top = (rh - H) // 2
    im = im.crop((left, top, left + W, top + H))

    block = 1 if a.no_chunk else max(1, a.block)
    if block > 1:
        nw, nh = max(1, W // block), max(1, H // block)
        im = im.resize((nw, nh), Image.LANCZOS).resize((W, H), Image.NEAREST)

    out = out_dir / f"{a.name}.png"
    im.save(out)
    print(f"bg {a.name}: {W}x{H} block={block} -> {out.name}")


if __name__ == "__main__":
    main()
