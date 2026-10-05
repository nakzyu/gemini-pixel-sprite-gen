#!/usr/bin/env python3
# 얼굴 확대(피부 덩어리 기준, 칸 격자) — 줄마다 그림들(쉼표). head_swap.head_info 로 얼굴 창을 찾는다
# usage: face_zoom.py SCALE OUT.png a.png,b.png [c.png,d.png ...]   (each arg = one row; compare faces block by block)
import sys
from PIL import Image, ImageDraw
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from head_swap import head_info
if len(sys.argv) < 4: print(open(__file__).read().split('\n')[2]); sys.exit(2)
S=int(sys.argv[1]); out=sys.argv[2]; rows=[a.split(',') for a in sys.argv[3:]]
tiles=[]
for r in rows:
    t=[]
    for p in r:
        im=Image.open(p).convert('RGBA')
        try:
            h=head_info(im); xs=[x for x,_ in h['face']]
            box=(max(0,min(xs)-3), max(0,h['fy0']-5), min(im.width,max(xs)+4), min(im.height,h['chin']+3))
        except Exception:
            box=im.getbbox()
        c=im.crop(box); t.append(c.resize((c.width*S,c.height*S),Image.NEAREST))
    tiles.append(t)
W=max(sum(i.width+14 for i in t) for t in tiles)+6; H=sum(max(i.height for i in t)+14 for t in tiles)
o=Image.new('RGBA',(W,H),(205,207,214,255)); d=ImageDraw.Draw(o); y=0
for t in tiles:
    x=6
    for i in t:
        o.alpha_composite(i,(x,y))
        for gx in range(0,i.width+1,S): d.line([(x+gx,y),(x+gx,y+i.height)],fill=(0,0,0,30))
        for gy in range(0,i.height+1,S): d.line([(x,y+gy),(x+i.width,y+gy)],fill=(0,0,0,30))
        x+=i.width+14
    y+=max(i.height for i in t)+14
o.save(out); print(o.size)
