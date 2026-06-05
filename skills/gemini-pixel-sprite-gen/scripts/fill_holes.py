#!/usr/bin/env python3
"""Fill transparent gaps INSIDE a snapped sprite with nearby colors.

Why: Gemini sometimes returns hair/armor with a hollow interior (e.g. twin-tails
tied high leave a see-through crown, or scattered transparent speckle inside a
solid mass). At 32px those gaps survive the snap and read as holes / a half-eaten
head. This closes interior gaps WITHOUT touching the outer silhouette.

Two passes:
  1. Enclosed-hole fill: flood the background inward from the 4 corners over
     transparent pixels; any transparent pixel NOT reached is enclosed -> fill it
     with the mode color of its opaque 8-neighbors (iterative dilation).
  2. Concave fill: any remaining transparent pixel with >= THR opaque 8-neighbors
     gets the mode neighbor color, repeated PASSES times. Closes notches and
     1-wide channels that technically still touch the background.

Outer flat edges keep <THR opaque neighbors, so the silhouette is preserved.

Usage:
  python3 fill_holes.py <src.png> [dst.png] [--thr 5] [--passes 3]
  (dst defaults to src, i.e. in place)
"""
import sys
from PIL import Image
from collections import deque, Counter


def fill(src, dst, thr=5, passes=3):
    im = Image.open(src).convert("RGBA")
    W, H = im.size
    px = im.load()

    def is_op(x, y):
        return 0 <= x < W and 0 <= y < H and px[x, y][3] > 0

    # pass 1: enclosed-hole fill via background flood from corners
    bg = [[False] * W for _ in range(H)]
    dq = deque()
    for cx, cy in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        if not is_op(cx, cy) and not bg[cy][cx]:
            bg[cy][cx] = True
            dq.append((cx, cy))
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not bg[ny][nx] and not is_op(nx, ny):
                bg[ny][nx] = True
                dq.append((nx, ny))
    holes = set((x, y) for y in range(H) for x in range(W)
                if not is_op(x, y) and not bg[y][x])
    enclosed = 0
    while holes:
        op_now = set((x, y) for y in range(H) for x in range(W) if is_op(x, y))
        progressed = []
        for (x, y) in holes:
            cols = [px[x + dx, y + dy]
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if (dx or dy) and (x + dx, y + dy) in op_now]
            if cols:
                progressed.append((x, y, Counter(cols).most_common(1)[0][0]))
        if not progressed:
            break
        for (x, y, c) in progressed:
            px[x, y] = (c[0], c[1], c[2], 255)
            holes.discard((x, y))
            enclosed += 1

    # pass 2: concave fill (>= thr opaque neighbors)
    concave = 0
    for _ in range(passes):
        todo = []
        for y in range(H):
            for x in range(W):
                if is_op(x, y):
                    continue
                cols = [px[x + dx, y + dy]
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if (dx or dy) and is_op(x + dx, y + dy)]
                if len(cols) >= thr:
                    todo.append((x, y, Counter(cols).most_common(1)[0][0]))
        if not todo:
            break
        for (x, y, c) in todo:
            px[x, y] = (c[0], c[1], c[2], 255)
            concave += 1

    im.save(dst)
    print(f"filled enclosed={enclosed} concave={concave} -> {dst}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    src = a[0]
    dst = a[1] if len(a) > 1 and not a[1].startswith("--") else src
    thr = int(a[a.index("--thr") + 1]) if "--thr" in a else 5
    passes = int(a[a.index("--passes") + 1]) if "--passes" in a else 3
    fill(src, dst, thr, passes)
