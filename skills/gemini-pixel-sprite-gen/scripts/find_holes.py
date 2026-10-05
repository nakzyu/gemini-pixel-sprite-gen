# find_holes.py a.png [b.png ...] — list transparent pixels not connected to the outside (interior holes)
import sys
from PIL import Image
from collections import deque
def holes(im):
    W,H=im.size; out=set(); q=deque()
    for x in range(W):
        for y in (0,H-1): q.append((x,y))
    for y in range(H):
        for x in (0,W-1): q.append((x,y))
    while q:
        p=q.popleft()
        if p in out or im.getpixel(p)[3]>127: continue
        out.add(p); x,y=p
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            n=(x+dx,y+dy)
            if 0<=n[0]<W and 0<=n[1]<H and n not in out: q.append(n)
    return [(x,y) for y in range(H) for x in range(W) if im.getpixel((x,y))[3]<128 and (x,y) not in out]
if __name__=='__main__':
    for f in sys.argv[1:]: print(f, holes(Image.open(f).convert('RGBA')))
