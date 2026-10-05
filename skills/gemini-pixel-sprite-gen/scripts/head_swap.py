#!/usr/bin/env python3
# head_swap.py — paste the head of one sprite (e.g. idle) onto another frame of the same character
# (e.g. an attack candidate) so both frames share an identical face.
# usage: head_swap.py <idle.png> <cand.png> <out.png> [--atk existing_attack.png] [--box|--crown] [--imax X]
#                     [--dx N --dy N] [--skin HEX,HEX,..] [--skin-tol N] [--face-rows N] [--face-halfwidth N]
# Head = top row .. chin outline row; per row the connected run containing the face center column
# (clipped to the eye-row width). The candidate's head area is cleared and the source head is pasted,
# aligned on face center + chin row. Remaining near-palette pixels are recolored to the source palette.
# The face is located from skin-colored pixels: pass --skin with your skin colors (sampled from the
# source sprite); without it a built-in light-skin heuristic is used.
import sys
from PIL import Image

# Face-detection settings (CLI flags override). face_rows / face_halfwidth = None -> proportional to the
# figure height (0.2x / 0.15x).
CFG = dict(skin=None, skin_tol=40, face_rows=None, face_halfwidth=None)

def skin(c):
    r, g, b, a = c
    if a <= 200 or r == 0: return False
    if CFG['skin']:
        return any(abs(r - s[0]) + abs(g - s[1]) + abs(b - s[2]) <= CFG['skin_tol'] for s in CFG['skin'])
    # fallback heuristic: two light skin tones (lit + shade), narrow enough to skip blond/cream hair
    gr, br = g / r, b / r
    return (r >= 235 and .76 <= gr <= .88 and .58 <= br <= .76) or (210 <= r < 238 and .62 <= gr <= .77 and .46 <= br <= .63)

def head_info(im):
    W, H = im.size; px = im.load()
    op = lambda x, y: 0 <= x < W and 0 <= y < H and px[x, y][3] > 128
    top = next(y for y in range(H) if any(op(x, y) for x in range(W)))
    sk = [(x, y) for y in range(H) for x in range(W) if skin(px[x, y])]
    # face = the face_rows window in the upper 2/3 holding the most skin pixels; chin = last contiguous skin row
    bottom = max(y for y in range(H) if any(op(x, y) for x in range(W)))
    fig_h = bottom - top + 1
    nrow = CFG['face_rows'] or max(3, round(fig_h * 0.2))
    half = CFG['face_halfwidth'] or max(2, round(fig_h * 0.15))
    bot = top + (bottom - top) * 2 // 3
    cnt = lambda y0: sum(1 for x, y in sk if y0 <= y < y0 + nrow)
    f0 = max(range(top, bot), key=cnt)
    face = [(x, y) for x, y in sk if f0 <= y < f0 + nrow]
    # a skin-colored hand next to the face would widen the face box (and erase the weapon) —
    # keep only skin within +-half columns of the median column
    mx = sorted(x for x, _ in face)[len(face) // 2]
    face = [(x, y) for x, y in face if abs(x - mx) <= half]
    rows = sorted({y for _, y in face}); fy0 = rows[0]; chin = rows[0]
    for y in rows:
        if y - chin > 1: break
        chin = y
    xs = sorted(x for x, y in face if y <= chin); cx = xs[len(xs) // 2]
    eye_row = max(range(fy0, chin + 1), key=lambda y: sum(1 for x, yy in face if yy == y))
    def run(y):
        if not op(cx, y):
            near = [x for x in range(W) if op(x, y)]
            if not near: return None
            x0 = min(near, key=lambda x: abs(x - cx))
        else: x0 = cx
        a = x0; b = x0
        while op(a - 1, y): a -= 1
        while op(b + 1, y): b += 1
        return a, b
    ea, eb = run(eye_row)
    mask = set()
    for y in range(top, chin + 2):
        r = run(y)
        if not r: continue
        for x in range(max(r[0], ea - 1), min(r[1], eb + 1) + 1): mask.add((x, y))
    return dict(top=top, chin=chin, cx=cx, eye_row=eye_row, span=(ea, eb), mask=mask, face=face, fy0=fy0,
                skins=sorted({px[x, y][:3] for x, y in face}, key=lambda c: -sum(c)))

def swap(idle_p, cand_p, out_p, dx=None, dy=None, atk_p=None, pad=4, tol=48, tight=True, crown=False, imax=None):
    I = Image.open(idle_p).convert('RGBA'); C = Image.open(cand_p).convert('RGBA')
    hi = head_info(I); hc = head_info(C)
    # imax: cut the source head mask at column x so a prop glued to the head (staff tip etc.) is not copied
    if imax is not None: hi['mask'] = {(x, y) for x, y in hi['mask'] if x <= imax}
    dx = hc['cx'] - hi['cx'] if dx is None else dx
    dy = hc['chin'] - hi['chin'] if dy is None else dy
    out = C.copy(); op = out.load(); ip = I.load(); W, H = out.size
    # 1) clear the candidate head
    #   tight (default): only the pasted-head footprint + candidate face box (3 rows above face .. 1 below chin, face width +-1)
    #   — weapons raised over the head and flying hair survive
    #   box: face center +-(face half width + pad) x top..chin (candidate head much bigger than the source)
    fxs = [x for x, y in hc['face']]
    x0, x1 = min(fxs) - pad, max(fxs) + pad
    if tight:
        clear = {(x + dx, y + dy) for x, y in hi['mask']}
        clear |= {(x, y) for y in range(hc['fy0'] - 3, hc['chin'] + 2) for x in range(min(fxs) - 1, max(fxs) + 2)}
    else:
        clear = {(x, y) for y in range(hc['top'], hc['chin'] + 2) for x in range(x0, x1 + 1)}
    for x, y in clear:
        if 0 <= x < W and 0 <= y < H: op[x, y] = (0, 0, 0, 0)
    # 2) paste the source head (face center + chin row aligned)
    for x, y in hi['mask']:
        tx, ty = x + dx, y + dy
        if 0 <= tx < W and 0 <= ty < H and ip[x, y][3] > 128: op[tx, ty] = ip[x, y]
    head = {(x + dx, y + dy) for x, y in hi['mask']}
    # crown: candidate crown still sticks out above the pasted head — within the pasted head's width, erase pixels
    # above it that match source-head colors (hair/outline); other colors (bow limb, blade) stay
    if crown:
        hcols = {ip[x, y][:3] for x, y in hi['mask'] if ip[x, y][3] > 128}
        hx = [x for x, _ in head]; ptop = min(y for _, y in head)
        for y in range(0, ptop):
            for x in range(min(hx), max(hx) + 1):
                c = op[x, y]
                if c[3] > 128 and min(sum(abs(c[i] - h[i]) for i in range(3)) for h in hcols) <= 30: op[x, y] = (0, 0, 0, 0)
    # 3) recolor remaining pixels to the source (+ --atk) palette — near colors only (effects/trails stay)
    pal = {c[:3] for c in I.getdata() if c[3] > 128}
    if atk_p: pal |= {c[:3] for c in Image.open(atk_p).convert('RGBA').getdata() if c[3] > 128}
    pal = list(pal)
    for y in range(H):
        for x in range(W):
            c = op[x, y]
            if c[3] <= 128 or (x, y) in head: continue
            if max(c[:3]) - min(c[:3]) < 24: continue  # leave whites/greys (swing trails) alone
            n = min(pal, key=lambda r: sum(abs(r[i] - c[i]) for i in range(3)))
            if sum(abs(n[i] - c[i]) for i in range(3)) <= tol: op[x, y] = n + (255,)
    # 4) drop floating leftovers (< 6 px, not attached to head/body)
    seen = set()
    for y in range(H):
        for x in range(W):
            if op[x, y][3] <= 128 or (x, y) in seen: continue
            comp = []; st = [(x, y)]; seen.add((x, y))
            while st:
                a, b = st.pop(); comp.append((a, b))
                for u in (-1, 0, 1):
                    for v in (-1, 0, 1):
                        q = (a + u, b + v)
                        if 0 <= q[0] < W and 0 <= q[1] < H and q not in seen and op[q][3] > 128: seen.add(q); st.append(q)
            if len(comp) < 6:
                for q in comp: op[q] = (0, 0, 0, 0)
    out.save(out_p)
    return dict(dx=dx, dy=dy, idle=(hi['top'], hi['chin'], hi['cx']), cand=(hc['top'], hc['chin'], hc['cx']), tight=tight)

if __name__ == '__main__':
    a = sys.argv[1:]; kw = {}
    def _opt(name, conv):
        if name in a:
            i = a.index(name); v = conv(a[i + 1]); del a[i:i + 2]; return v
    CFG['skin'] = _opt('--skin', lambda v: [tuple(int(h.strip('#')[i:i + 2], 16) for i in (0, 2, 4)) for h in v.split(',')])
    CFG['skin_tol'] = _opt('--skin-tol', int) or CFG['skin_tol']
    CFG['face_rows'] = _opt('--face-rows', int)
    CFG['face_halfwidth'] = _opt('--face-halfwidth', int)
    if len(a) < 3 or a[0] in ('-h', '--help'):
        print('usage: head_swap.py IDLE.png CAND.png OUT.png [--atk CUR_ATTACK.png] [--box|--crown] [--imax X] [--dx N --dy N]\n'
              '  paste the idle head onto an attack candidate (same face as idle).\n'
              '  default tight: clear only the pasted head + candidate face box (raised weapons/hair stay)\n'
              '  --box   clear top..chin around the face (candidate head much bigger than idle)\n'
              '  --crown also erase candidate crown pixels above the pasted head (head/outline colors only)\n'
              '  --imax X  cut idle head mask at column X (drop a staff tip etc. glued to the head)\n'
              '  --atk   add an existing attack sprite\'s palette to the recolor palette\n'
              '  --skin HEX,..  skin colors used to find the face (default: built-in light-skin heuristic)\n'
              '  --skin-tol N   RGB L1 tolerance for --skin (default 40)\n'
              '  --face-rows N / --face-halfwidth N  face window size (default 0.2x / 0.15x figure height)')
        sys.exit(0 if a and a[0] in ('-h', '--help') else 2)
    if '--dx' in a: i = a.index('--dx'); kw['dx'] = int(a[i + 1]); del a[i:i + 2]
    if '--dy' in a: i = a.index('--dy'); kw['dy'] = int(a[i + 1]); del a[i:i + 2]
    if '--crown' in a: a.remove('--crown'); kw['crown'] = True
    if '--imax' in a: i = a.index('--imax'); kw['imax'] = int(a[i + 1]); del a[i:i + 2]
    if '--box' in a: a.remove('--box'); kw['tight'] = False
    if '--atk' in a: i = a.index('--atk'); kw['atk_p'] = a[i + 1]; del a[i:i + 2]
    print(swap(*a[:3], **kw))
