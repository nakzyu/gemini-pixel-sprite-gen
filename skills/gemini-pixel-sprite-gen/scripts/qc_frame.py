#!/usr/bin/env python3
"""Acceptance gate for raw Gemini sprite output — run BEFORE snapping/showing the user.

Catches the mechanical failures that used to cost re-roll after re-roll:
  - subject CLIPPED at the canvas edge (a weapon/limb/hair running off-frame)
  - chromakey background not removed (no transparency)
  - empty / tiny / failed generation

Design:
  - a subject jammed against a side edge (>10% of that border opaque) FAILS as
    clipped; a clean frame that keeps margin PASSES.
  - ASPECT IS NOT a hard gate — approved attacks range from portrait casters to
    wide melee swings, so a narrow pose only WARNS, and only for `swing` kind.

HARD fails -> exit 1 (pipeline should auto-regenerate, appending the reason).
Soft warns -> exit 0 but printed (human eyeballs them).

Usage:
  qc_frame.py <png> [--kind idle|action|swing] [--json]

  idle   : portrait expected. clip + transparency + size only.
  action : default. + warns if subject spans full width (margin gone).
  swing  : melee swing (sword/spear). + warns if not a wide horizontal pose.
"""
import argparse
import json
import sys

from PIL import Image

OPAQUE = 200          # alpha > this counts as solid subject
HARD_CLIP = 0.10      # border opaque-fraction above this = clipped (hard fail)
SOFT_CLIP = 0.02      # border opaque-fraction above this = minor contact (warn)
MIN_SIZE = 0.25       # subject height must be >= this fraction of canvas height
SWING_ASPECT = 1.1    # a swing attack narrower than this is probably not swinging


def analyze(path, kind):
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    alpha = im.getchannel("A")
    amin, amax = alpha.getextrema()

    hard, warn = [], []

    # 1. transparency present? (chromakey actually removed)
    if amin > 10:
        hard.append("no transparent background — chromakey removal failed "
                    "(subject likely on a solid/green block)")

    mask = alpha.point(lambda v: 255 if v > OPAQUE else 0)
    bbox = mask.getbbox()
    if not bbox:
        hard.append("empty frame — no opaque subject found")
        return _result(path, W, H, None, None, hard, warn)

    l, t, r, b = bbox
    cw, ch = r - l, b - t

    # 2. subject big enough?
    if ch < MIN_SIZE * H:
        hard.append(f"subject too small — {ch}px tall in {H}px canvas "
                    f"({ch / H:.0%}, need >={MIN_SIZE:.0%})")

    # 3. edge clip — opaque fraction along each border (2px-deep strip)
    px = mask.load()
    edges = {
        "left":   sum(1 for y in range(H) for x in (0, 1) if px[x, y]) / (2 * H),
        "right":  sum(1 for y in range(H) for x in (W - 1, W - 2) if px[x, y]) / (2 * H),
        "top":    sum(1 for x in range(W) for y in (0, 1) if px[x, y]) / (2 * W),
        "bottom": sum(1 for x in range(W) for y in (H - 1, H - 2) if px[x, y]) / (2 * W),
    }
    clipped = [f"{s}({f:.0%})" for s, f in edges.items() if f > HARD_CLIP]
    touched = [f"{s}({f:.0%})" for s, f in edges.items()
               if SOFT_CLIP < f <= HARD_CLIP]
    if clipped:
        hard.append("subject CLIPPED at canvas edge: " + ", ".join(clipped)
                    + " — weapon/hair/cape jammed against border, regenerate "
                      "with a wider canvas + margin")
    if touched:
        warn.append("minor edge contact: " + ", ".join(touched))

    # 4. composition warnings (never hard)
    aspect = cw / ch
    if kind in ("action", "swing") and cw >= W - 4:
        warn.append(f"subject spans full canvas width ({cw}/{W}px, no margin) "
                    "— double-check nothing is clipped")
    if kind == "swing" and aspect < SWING_ASPECT:
        warn.append(f"content aspect {aspect:.2f} is portrait — a swing should "
                    f"read WIDE/horizontal (want >= {SWING_ASPECT}); pose may be "
                    "static or wrong-facing")

    return _result(path, W, H, (cw, ch), round(aspect, 2), hard, warn, edges)


def _result(path, W, H, content, aspect, hard, warn, edges=None):
    return {
        "path": path,
        "canvas": [W, H],
        "content": list(content) if content else None,
        "aspect": aspect,
        "edges": {k: round(v, 3) for k, v in edges.items()} if edges else None,
        "hard": hard,
        "warn": warn,
        "verdict": "FAIL" if hard else "PASS",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("png")
    ap.add_argument("--kind", choices=["idle", "action", "swing"], default="action")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    res = analyze(args.png, args.kind)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        c = res["content"]
        print(f"{res['verdict']}  {args.png}")
        print(f"  canvas {res['canvas'][0]}x{res['canvas'][1]}  "
              f"content {c[0]}x{c[1] if c else '-'} aspect {res['aspect']}  "
              f"kind={args.kind}" if c else f"  canvas {res['canvas'][0]}x{res['canvas'][1]}")
        for h in res["hard"]:
            print(f"  ✗ {h}")
        for w in res["warn"]:
            print(f"  ! {w}")

    sys.exit(1 if res["hard"] else 0)


if __name__ == "__main__":
    main()
