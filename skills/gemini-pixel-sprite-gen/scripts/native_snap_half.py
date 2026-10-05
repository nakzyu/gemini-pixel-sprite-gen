# 반 칸 격자 → 2×2 묶기 축소 (공격 자세처럼 반 칸 어긋남이 있는 넓은 캔버스 원본용)
# usage: native_snap_half.py <raw> <out> [--flip] [--main]   (가로·세로 반 칸 간격이 다르면 "다시 뽑기"로 종료)
import sys, numpy as np
from PIL import Image
from collections import Counter
from scipy import ndimage
sys.path.insert(0, __import__('os').path.dirname(__file__))
from native_snap import grid  # 같은 폴더

def sample(rgb, op, p, ox, oy, m=0.25):
    H, W = op.shape; nx = int((W-ox)//p); ny = int((H-oy)//p)
    out = np.zeros((ny, nx, 4), np.uint8)
    for j in range(ny):
        y0 = int(round(oy+j*p+p*m)); y1 = max(y0+1, int(round(oy+(j+1)*p-p*m)))
        for i in range(nx):
            x0 = int(round(ox+i*p+p*m)); x1 = max(x0+1, int(round(ox+(i+1)*p-p*m)))
            bo = op[y0:y1, x0:x1]
            if bo.size == 0 or bo.mean() < 0.5: continue
            cols = rgb[y0:y1, x0:x1][bo]
            q = [tuple((c//8)*8) for c in cols]; key = Counter(q).most_common(1)[0][0]
            sel = cols[[tuple((c//8)*8) == key for c in cols]]
            out[j, i, :3] = np.median(sel, axis=0).astype(np.uint8); out[j, i, 3] = 255
    return out

def quantize(f, tol=20):
    pal = []; out = f.copy()
    for j in range(f.shape[0]):
        for i in range(f.shape[1]):
            if f[j, i, 3] == 0: continue
            c = f[j, i, :3].astype(int)
            for q in pal:
                if np.abs(q - c).sum() < tol: out[j, i, :3] = q; break
            else:
                pal.append(c); out[j, i, :3] = c
    return out, len(pal)

def down2(f):
    best = None
    for py in (0, 1):
        for px in (0, 1):
            g = f[py:, px:]; h = g.shape[0]//2; w = g.shape[1]//2
            g = g[:h*2, :w*2].reshape(h, 2, w, 2, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, 4, 4)
            same = 0; out = np.zeros((h, w, 4), np.uint8)
            for j in range(h):
                for i in range(w):
                    cells = [tuple(c) for c in g[j, i] if c[3] > 0]
                    if len(cells) < 2: continue
                    cnt = Counter(cells); c, n = cnt.most_common(1)[0]
                    if n == 4: same += 1
                    if n == 2 and len(cnt) > 1:  # 동률이면 어두운 쪽(외곽선 보존)
                        tops = [k for k, v in cnt.items() if v == 2]; c = min(tops, key=lambda k: int(k[0])+int(k[1])+int(k[2]))
                    out[j, i] = c
            if best is None or same > best[0]: best = (same, out, (px, py))
    return best

def run(path, outp, flip, main, lo=8, hi=14, cell_h=48, pad=4, despill=False):
    a = np.array(Image.open(path).convert('RGBA')); rgb = a[..., :3].astype(int); op = a[..., 3] > 200
    sx, px, fx = grid(np.abs(np.diff(rgb, axis=1)).sum(axis=2).sum(axis=0), lo, hi)
    sy, py, fy = grid(np.abs(np.diff(rgb, axis=0)).sum(axis=2).sum(axis=1), lo, hi)
    if abs(px-py) > 0.3: raise SystemExit(f'반 칸 주기 불일치 x{px:.2f} y{py:.2f} (점수 {sx:.2f}/{sy:.2f}) — 격자 없는 원본, 다시 뽑기')
    p = (px+py)/2; fine = sample(rgb, op, p, (fx+1) % p, (fy+1) % p)
    fine, npal = quantize(fine)
    same, arr, ph = down2(fine)
    pass  # 반 칸 중간 결과는 저장 안 함
    al = arr[..., 3] > 0; lab, n = ndimage.label(al, structure=np.ones((3, 3))); sizes = ndimage.sum(al, lab, range(1, n+1))
    for k, s in enumerate(sizes, 1):
        if s <= 2 or (main and s < sizes.max()): arr[lab == k] = 0
    g = arr[..., 1].astype(int); r = arr[..., 0].astype(int); b = arr[..., 2].astype(int)
    if despill:  # 공격 자세 궤적 전용
        arr[(arr[..., 3] > 0) & (g > r+25) & (g > b+25), :3] = (232, 240, 240)
    im = Image.fromarray(arr)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im = im.crop(im.getbbox()); ch = im.height
    bm = np.array(im)[..., 3] > 0; fxs = np.where(bm[-3:].any(axis=0))[0]; feet = (fxs.min()+fxs.max())/2
    half = max(feet, im.width-feet)+pad; cw = int(np.ceil(half*2/16)*16)
    cell = Image.new('RGBA', (cw, cell_h), (0, 0, 0, 0)); cell.paste(im, (int(round(cw/2-feet)), cell_h-pad-ch), im); cell.save(outp)
    total = (arr[..., 3] > 0).sum()
    print(f'{path.split("/")[-1][:40]} 반칸 {p:.2f} (점수 {sx:.2f}/{sy:.2f}) 한칸 {2*p:.2f} 위상 {ph} 2x2일치 {same}/{(arr[...,3]>0).sum()} 팔레트 {npal} -> char {im.width}x{ch}, cell {cw}x{cell_h}')

if __name__ == '__main__':
    args = sys.argv[1:]; flip = '--flip' in args; main = '--main' in args
    lo = float(next((a.split('=')[1] for a in args if a.startswith('--lo=')), 8))
    hi = float(next((a.split('=')[1] for a in args if a.startswith('--hi=')), 14))
    args = [x for x in args if not x.startswith('--')]
    run(args[0], args[1], flip, main, lo, hi, despill=('--despill' in sys.argv))  # --lo=/--hi= : 반 칸 주기 탐색 범위(대기 자세는 14~20)
