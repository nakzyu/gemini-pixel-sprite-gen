# rowdrop.py (library) — remove row r and shift everything above it down by one (rowdrop_x: only columns xa..xb)
from PIL import Image
def rowdrop(im, r):
    im=im.copy(); W,H=im.size; src=im.copy()
    for y in range(r,0,-1):
        for x in range(W): im.putpixel((x,y),src.getpixel((x,y-1)))
    for x in range(W): im.putpixel((x,0),(0,0,0,0))
    return im
def rowdrop_x(im, r, xa, xb):
    im=im.copy(); src=im.copy()
    for y in range(r,0,-1):
        for x in range(xa,xb+1): im.putpixel((x,y),src.getpixel((x,y-1)))
    for x in range(xa,xb+1): im.putpixel((x,0),(0,0,0,0))
    return im
