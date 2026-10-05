#!/usr/bin/env python3
"""Grid 1:1 downscale of a raw Gemini character/monster image, picking the grid by target height.

Gemini draws on a fixed block grid, but the period finder can lock onto a half or double
grid. This tries the candidate periods (small, large, small x2) and keeps the one whose
downscaled content height is closest to --target-h blocks, then runs native_snap with the
search window pinned around that period. If the x/y periods disagree slightly it forces
their average. Use the project's sprite_spec.yaml values for --target-h / --cell-h.

usage: snap_char.py RAW OUT [--monster] [--idle] [--target-h N] [--cell-h N]
  --idle     keep green-ish real colors (no despill; despill is for attack swing trails)
  --monster  defaults target-h 64 / cell-h 72 instead of 32 / 48
"""
import argparse
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import native_snap as ns  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw")
    ap.add_argument("out")
    ap.add_argument("--monster", action="store_true", help="monster defaults (target 64 blocks, cell 72)")
    ap.add_argument("--idle", action="store_true", help="idle pose: skip green despill")
    ap.add_argument("--target-h", type=int, help="expected content height in blocks (default 32, monster 64)")
    ap.add_argument("--cell-h", type=int, help="output cell height in px (default 48, monster 72)")
    a = ap.parse_args()
    target = a.target_h or (64 if a.monster else 32)
    cell_h = a.cell_h or (72 if a.monster else 48)

    arr = np.array(Image.open(a.raw).convert("RGBA"))
    rgb = arr[..., :3].astype(int)
    op = arr[..., 3] > 200
    ys = np.where(op.any(axis=1))[0]
    content_h = ys[-1] - ys[0] + 1
    ex = np.abs(np.diff(rgb, axis=1)).sum(axis=2).sum(axis=0)
    ey = np.abs(np.diff(rgb, axis=0)).sum(axis=2).sum(axis=1)
    orig = ns.grid
    small = (orig(ex, 12, 24)[1] + orig(ey, 12, 24)[1]) / 2
    large = (orig(ex, 24, 45)[1] + orig(ey, 24, 45)[1]) / 2
    cands = sorted({float(round(small, 2)), float(round(large, 2)), float(round(small * 2, 2))},
                   key=lambda p: abs(content_h / p - target))
    P = cands[0]
    ns.grid = lambda sig, lo=20, hi=45: orig(sig, P - 1.2, P + 1.2)
    print(f"grid {P} (raw height {content_h}px -> ~{content_h / P:.0f} blocks, candidates {cands})", end=" · ")
    try:
        ns.snap(a.raw, a.out, cell_h=cell_h, despill=not a.idle)
    except SystemExit as e:  # x/y periods slightly off -> force the averaged period
        m = re.findall(r"[0-9.]+", str(e))
        Pf = round((float(m[0]) + float(m[1])) / 2, 2) if len(m) >= 2 else P
        ns.grid = lambda sig, lo=20, hi=45: orig(sig, Pf, Pf + 0.04)
        print(f"(period mismatch {e} -> pinned {Pf})", end=" · ")
        ns.snap(a.raw, a.out, cell_h=cell_h, despill=not a.idle)


if __name__ == "__main__":
    main()
