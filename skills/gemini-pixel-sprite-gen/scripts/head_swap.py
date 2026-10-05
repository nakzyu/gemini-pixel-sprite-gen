#!/usr/bin/env python3
# 대기 머리 → 공격 후보에 그대로. 지금 게임 공격 그림이 하는 방식(대기 머리 위 12줄이 공격 안에 92~100% 같은 색).
# usage: head_swap.py <idle.png> <cand.png> <out.png> [--atk 지금공격.png] [--box|--crown] [--imax X] [--dx N --dy N]
# 머리 = 맨 위 ~ 턱 외곽선 줄. 줄마다 얼굴 가운데 열을 품은 이어진 칸 덩어리(눈 줄 폭으로 자름).
# 후보 머리 자리를 비우고 대기 머리를 얼굴 가운데·턱 줄을 맞춰 얹는다. 후보 몸의 피부색은 대기 피부색으로 바꾼다.
import sys
from PIL import Image

def skin(c):
    # 우리 그림 피부 두 톤(실측 10-05): 밝은 피부 r≥238·g/r .78~.87·b/r .60~.74, 그늘 r 215~235·g/r .64~.76·b/r .48~.62
    # 금발(244,215,113)·크림 머리(209,179,141)는 안 걸리게 범위를 좁혔다
    r, g, b, a = c
    if a <= 200 or r == 0: return False
    gr, br = g / r, b / r
    return (r >= 235 and .76 <= gr <= .88 and .58 <= br <= .76) or (210 <= r < 238 and .62 <= gr <= .77 and .46 <= br <= .63)

def head_info(im):
    W, H = im.size; px = im.load()
    op = lambda x, y: 0 <= x < W and 0 <= y < H and px[x, y][3] > 128
    top = next(y for y in range(H) if any(op(x, y) for x in range(W)))
    sk = [(x, y) for y in range(H) for x in range(W) if skin(px[x, y])]
    # 얼굴 = 위쪽 절반에서 피부 칸이 가장 많이 모인 7줄 창. 턱 = 그 창에서 피부가 이어지는 마지막 줄
    bot = top + (max(y for y in range(H) if any(op(x, y) for x in range(W))) - top) * 2 // 3
    cnt = lambda y0: sum(1 for x, y in sk if y0 <= y < y0 + 7)
    f0 = max(range(top, bot), key=cnt)
    face = [(x, y) for x, y in sk if f0 <= y < f0 + 7]
    # 얼굴 옆 손(활 잡은 손 등)도 피부색이라 얼굴 상자가 넓어져 무기까지 지운다 — 가운데(중앙값)에서 ±5칸만 얼굴로
    mx = sorted(x for x, _ in face)[len(face) // 2]
    face = [(x, y) for x, y in face if abs(x - mx) <= 5]
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
    # imax: 대기 머리 옆에 붙은 소품(지팡이 머리 등)이 머리와 같이 따라오지 않게 대기 머리 열을 이 x 까지로 자른다
    if imax is not None: hi['mask'] = {(x, y) for x, y in hi['mask'] if x <= imax}
    dx = hc['cx'] - hi['cx'] if dx is None else dx
    dy = hc['chin'] - hi['chin'] if dy is None else dy
    out = C.copy(); op = out.load(); ip = I.load(); W, H = out.size
    # 1) 후보 머리 비우기
    #   tight(기본): 얹을 대기 머리 자리 + 후보 얼굴 상자(눈썹 위 3줄~턱 아래 1줄, 얼굴 폭 ±1)만 — 머리 위로 든 무기·날리는 머리칼은 남는다
    #   box: 얼굴 가운데 ±(얼굴 반폭+pad) × 맨 위~턱 줄 전부(머리가 후보보다 많이 클 때)
    fxs = [x for x, y in hc['face']]
    x0, x1 = min(fxs) - pad, max(fxs) + pad
    if tight:
        clear = {(x + dx, y + dy) for x, y in hi['mask']}
        clear |= {(x, y) for y in range(hc['fy0'] - 3, hc['chin'] + 2) for x in range(min(fxs) - 1, max(fxs) + 2)}
    else:
        clear = {(x, y) for y in range(hc['top'], hc['chin'] + 2) for x in range(x0, x1 + 1)}
    for x, y in clear:
        if 0 <= x < W and 0 <= y < H: op[x, y] = (0, 0, 0, 0)
    # 2) 대기 머리 얹기(얼굴 가운데·턱 줄 맞춤)
    for x, y in hi['mask']:
        tx, ty = x + dx, y + dy
        if 0 <= tx < W and 0 <= ty < H and ip[x, y][3] > 128: op[tx, ty] = ip[x, y]
    head = {(x + dx, y + dy) for x, y in hi['mask']}
    # crown: 후보 머리가 대기보다 키가 커서 얹은 머리 위로 후보 정수리가 남을 때 — 얹은 머리 폭 안, 그 위 줄들의
    # 머리색·외곽선 칸만 지운다(대기 머리에 있는 색). 활대·칼날처럼 다른 색은 남는다
    if crown:
        hcols = {ip[x, y][:3] for x, y in hi['mask'] if ip[x, y][3] > 128}
        hx = [x for x, _ in head]; ptop = min(y for _, y in head)
        for y in range(0, ptop):
            for x in range(min(hx), max(hx) + 1):
                c = op[x, y]
                if c[3] > 128 and min(sum(abs(c[i] - h[i]) for i in range(3)) for h in hcols) <= 30: op[x, y] = (0, 0, 0, 0)
    # 3) 나머지 칸 색을 대기(+지금 공격) 팔레트로 — 가까운 색만(효과·궤적처럼 먼 색은 그대로)
    pal = {c[:3] for c in I.getdata() if c[3] > 128}
    if atk_p: pal |= {c[:3] for c in Image.open(atk_p).convert('RGBA').getdata() if c[3] > 128}
    pal = list(pal)
    for y in range(H):
        for x in range(W):
            c = op[x, y]
            if c[3] <= 128 or (x, y) in head: continue
            if max(c[:3]) - min(c[:3]) < 24: continue  # 흰·회색(휘두름 궤적 등)은 그대로 — 머리색으로 물들지 않게
            n = min(pal, key=lambda r: sum(abs(r[i] - c[i]) for i in range(3)))
            if sum(abs(n[i] - c[i]) for i in range(3)) <= tol: op[x, y] = n + (255,)
    # 4) 비우고 남은 떠다니는 조각(6칸 미만, 머리·몸과 안 붙음) 지우기
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
    if len(a) < 3 or a[0] in ('-h', '--help'):
        print('usage: head_swap.py IDLE.png CAND.png OUT.png [--atk CUR_ATTACK.png] [--box|--crown] [--imax X] [--dx N --dy N]\n'
              '  paste the idle head onto an attack candidate (same face as idle).\n'
              '  default tight: clear only the pasted head + candidate face box (raised weapons/hair stay)\n'
              '  --box   clear top..chin around the face (candidate head much bigger than idle)\n'
              '  --crown also erase candidate crown pixels above the pasted head (head/outline colors only)\n'
              '  --imax X  cut idle head mask at column X (drop a staff tip etc. glued to the head)\n'
              '  --atk   add an existing attack sprite\'s palette to the recolor palette')
        sys.exit(0 if a and a[0] in ('-h', '--help') else 2)
    if '--dx' in a: i = a.index('--dx'); kw['dx'] = int(a[i + 1]); del a[i:i + 2]
    if '--dy' in a: i = a.index('--dy'); kw['dy'] = int(a[i + 1]); del a[i:i + 2]
    if '--crown' in a: a.remove('--crown'); kw['crown'] = True
    if '--imax' in a: i = a.index('--imax'); kw['imax'] = int(a[i + 1]); del a[i:i + 2]
    if '--box' in a: a.remove('--box'); kw['tight'] = False
    if '--atk' in a: i = a.index('--atk'); kw['atk_p'] = a[i + 1]; del a[i:i + 2]
    print(swap(*a[:3], **kw))
