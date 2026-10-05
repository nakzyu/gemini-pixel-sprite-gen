# 눈썹·눈 블록 옮겨 찍기 — 기준 그림(2차 직업·확정한 대기 자세)의 픽셀을 그대로 복사, 피부색만 대상 팔레트로 치환.
# 눈 규격: 눈썹 1줄(눈 위만 어둡게, 눈 사이 2칸 피부) + 눈 2줄 [연한색 진눈동자 피부 피부 눈동자 / 흰색 밝은눈동자 피부 피부 흰색] + 눈 아래 피부 1줄.
# usage: eye_transplant.py <src.png> <sx,sy,w,h> <dst.png> <dx,dy> <out.png> [src_hex:dst_hex,...]
#   예) eye_transplant.py tactician_idle.png 23,20,7,4 tactician_attack.png 39,19 out.png eeb484:e9ab7d,f5d6aa:f4cfa2
import sys
from PIL import Image

def hx(h): return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

def transplant(src, box, dst_img, xy, skin_map=None):
    s = Image.open(src).convert('RGBA'); x0, y0, w, h = box
    sm = {k.lower(): hx(v) for k, v in (skin_map or {}).items()}
    for j in range(h):
        for i in range(w):
            c = s.getpixel((x0+i, y0+j)); key = '%02x%02x%02x' % c[:3]
            dst_img.putpixel((xy[0]+i, xy[1]+j), sm.get(key, c))
    return dst_img

if __name__ == '__main__':
    if len(sys.argv) < 6:
        print(__doc__ or open(__file__).read().split('\n')[2]); sys.exit(1)
    src, box, dst, xy, out = sys.argv[1:6]
    smap = dict(p.split(':') for p in sys.argv[6].split(',')) if len(sys.argv) > 6 else {}
    im = Image.open(dst).convert('RGBA')
    transplant(src, tuple(map(int, box.split(','))), im, tuple(map(int, xy.split(','))), smap).save(out)
    print('ok', out)
