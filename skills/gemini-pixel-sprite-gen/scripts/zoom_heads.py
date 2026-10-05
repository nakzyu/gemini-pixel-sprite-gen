#!/usr/bin/env python3
# zoom_heads.py — enlarged top N rows of each sprite with a pixel grid; each arg is one row of comma-separated images
import sys
from PIL import Image, ImageDraw
if len(sys.argv) < 5: print('usage: zoom_heads.py SCALE TOP_ROWS OUT.png a.png,b.png [c.png,d.png ...]'); sys.exit(2)
S=int(sys.argv[1]); N=int(sys.argv[2]); out=sys.argv[3]; rows=[a.split(',') for a in sys.argv[4:]]
tiles=[]
for r in rows:
    t=[]
    for p in r:
        im=Image.open(p).convert('RGBA'); b=im.getbbox(); c=im.crop((b[0],b[1],b[2],min(im.height,b[1]+N)))
        t.append(c.resize((c.width*S,c.height*S),Image.NEAREST))
    tiles.append(t)
W=max(sum(i.width+14 for i in t) for t in tiles)+6; H=sum(max(i.height for i in t)+14 for t in tiles)
o=Image.new('RGBA',(W,H),(205,207,214,255)); d=ImageDraw.Draw(o); y=0
for t in tiles:
    x=6
    for i in t:
        o.alpha_composite(i,(x,y))
        for gx in range(0,i.width+1,S): d.line([(x+gx,y),(x+gx,y+i.height)],fill=(0,0,0,28))
        for gy in range(0,i.height+1,S): d.line([(x,y+gy),(x+i.width,y+gy)],fill=(0,0,0,28))
        x+=i.width+14
    y+=max(i.height for i in t)+14
o.save(out); print(o.size)
