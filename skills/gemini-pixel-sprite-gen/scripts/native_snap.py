# 픽셀 퍼펙트 축소: Gemini 원본의 격자(주기·위상)를 찾아 칸마다 1:1로 옮긴다(재샘플링 없음).
# usage: native_snap.py <raw.png> <out.png> [--flip] [--main]   --main: 가장 큰 덩어리만 남김 · --despill: 초록 번진 궤적을 흰빛으로(공격 자세 전용)
import sys, numpy as np
from PIL import Image
from collections import Counter

def grid(sig, lo=20, hi=45):
    w = np.clip(sig, 0, None).astype(float); idx = np.arange(len(w)); best = (0, 0, 0)
    for p in np.arange(lo, hi, 0.05):
        ph = (idx % p) / p
        c = (w*np.cos(2*np.pi*ph)).sum(); s = (w*np.sin(2*np.pi*ph)).sum()
        sc = np.hypot(c, s) / w.sum()
        if sc > best[0]: best = (sc, p, (np.arctan2(s, c)/(2*np.pi)) % 1 * p)
    return best  # score, period, phase(경계 위치)

def snap(path, out, flip=False, cell_h=48, pad=4, main_only=False, despill=False):
    a = np.array(Image.open(path).convert('RGBA'))
    rgb = a[..., :3].astype(int); op = a[..., 3] > 200
    ex = np.abs(np.diff(rgb, axis=1)).sum(axis=2).sum(axis=0)
    ey = np.abs(np.diff(rgb, axis=0)).sum(axis=2).sum(axis=1)
    sx, px, fx = grid(ex); sy, py, fy = grid(ey)
    p = (px + py) / 2 if abs(px-py) < 0.6 else None
    if p is None: raise SystemExit(f'x/y 주기 불일치 {px:.2f} {py:.2f}')
    # 경계는 diff 인덱스 기준 → 칸 시작 = phase+1
    ox = (fx + 1) % p; oy = (fy + 1) % p
    H, W = op.shape
    nx = int((W - ox) // p); ny = int((H - oy) // p)
    outa = np.zeros((ny, nx, 4), np.uint8)
    m = 0.3  # 칸 가장자리 30% 는 버리고 가운데만 본다
    for j in range(ny):
        y0 = int(round(oy + j*p + p*m)); y1 = int(round(oy + (j+1)*p - p*m))
        for i in range(nx):
            x0 = int(round(ox + i*p + p*m)); x1 = int(round(ox + (i+1)*p - p*m))
            blk_op = op[y0:y1, x0:x1]
            if blk_op.mean() < 0.5: continue
            cols = rgb[y0:y1, x0:x1][blk_op]
            q = [tuple((c // 8) * 8) for c in cols]  # 압축 잡음 흡수
            key = Counter(q).most_common(1)[0][0]
            sel = cols[[tuple((c//8)*8) == key for c in cols]]
            outa[j, i, :3] = np.median(sel, axis=0).astype(np.uint8); outa[j, i, 3] = 255
    im = Image.fromarray(outa)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    # 떨어진 점(1~2칸짜리) 제거
    arr = np.array(im); al = arr[..., 3] > 0
    from scipy import ndimage
    lab, n = ndimage.label(al, structure=np.ones((3, 3)))
    sizes = ndimage.sum(al, lab, range(1, n+1))
    for k, s in enumerate(sizes, 1):
        if s <= 2 or (main_only and s < sizes.max()): arr[lab == k] = 0
    # 초록 배경에 물든 칸(반투명 휘두름 궤적 등) → 흰빛으로
    g = arr[..., 1].astype(int); r = arr[..., 0].astype(int); b = arr[..., 2].astype(int)
    if despill:  # 공격 자세 궤적 전용 — 민트 머리 같은 실제 색까지 지우므로 대기 자세엔 쓰지 말 것
        spill = (arr[..., 3] > 0) & (g > r + 25) & (g > b + 25)
        arr[spill, :3] = (232, 240, 240)
    im = Image.fromarray(arr); bb = im.getbbox(); im = im.crop(bb)
    ch = im.height
    # 발 x중심: 아래 3줄 불투명 픽셀 평균
    b = np.array(im)[..., 3] > 0; fxs = np.where(b[-3:].any(axis=0))[0]; feet = (fxs.min() + fxs.max()) / 2
    half = max(feet, im.width - feet) + pad
    cw = int(np.ceil(half * 2 / 16) * 16)
    cell = Image.new('RGBA', (cw, cell_h), (0, 0, 0, 0))
    cell.paste(im, (int(round(cw/2 - feet)), cell_h - pad - ch), im)
    cell.save(out)
    print(f'{path.split("/")[-1][:40]} period {p:.2f} (x{px:.2f}/y{py:.2f}, score {sx:.2f}/{sy:.2f}) grid {nx}x{ny} -> char {im.width}x{ch}, cell {cw}x{cell_h}')

if __name__ == '__main__':
    args = sys.argv[1:]; flip = '--flip' in args; main = '--main' in args; ds = '--despill' in args
    args = [x for x in args if not x.startswith('--')]
    snap(args[0], args[1], flip, main_only=main, despill=ds)
