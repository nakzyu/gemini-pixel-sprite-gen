# 그림 전체 폭에서 한 줄(r)을 빼고 그 위를 통째로 한 칸 내린다
from PIL import Image
def rowdrop(im, r):
    im=im.copy(); W,H=im.size; src=im.copy()
    for y in range(r,0,-1):
        for x in range(W): im.putpixel((x,y),src.getpixel((x,y-1)))
    for x in range(W): im.putpixel((x,0),(0,0,0,0))
    return im
def rowdrop_x(im, r, xa, xb):
    # xa..xb 열에서만 한 줄(r)을 빼고 위를 한 칸 내린다(무기 등 머리 밖은 그대로)
    im=im.copy(); src=im.copy()
    for y in range(r,0,-1):
        for x in range(xa,xb+1): im.putpixel((x,y),src.getpixel((x,y-1)))
    for x in range(xa,xb+1): im.putpixel((x,0),(0,0,0,0))
    return im
