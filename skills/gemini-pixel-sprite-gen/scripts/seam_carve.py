# 세로 이음매 1줄 빼기(seam carving): 지정한 얼굴 줄은 정한 열을 지나고, 나머지 줄은 옆 칸과 같은 색(빼도 티 안 나는 칸)을 따라간다.
from PIL import Image
def _px(im,x,y):
    if x<0 or x>=im.width: return (0,0,0,0)
    c=im.getpixel((x,y)); return (0,0,0,0) if c[3]<128 else c
def cost(im,x,y):
    c=_px(im,x,y)
    if c==_px(im,x-1,y) or c==_px(im,x+1,y): return 0.0
    return 1.0
def seam(im, forced, xmin=None, xmax=None):
    """forced: {y: x}. 반환: 줄마다 뺄 x"""
    W,H=im.size; xmin=0 if xmin is None else xmin; xmax=W-1 if xmax is None else xmax
    INF=1e9; D=[[INF]*W for _ in range(H)]; P=[[0]*W for _ in range(H)]
    for x in range(xmin,xmax+1):
        if 0 in forced and x!=forced[0]: continue
        D[0][x]=cost(im,x,0)
    for y in range(1,H):
        for x in range(xmin,xmax+1):
            if y in forced and x!=forced[y]: continue
            best=INF; bp=x
            for dx in (0,-1,1):
                px=x+dx
                if xmin<=px<=xmax and D[y-1][px]+0.05*abs(dx)<best: best=D[y-1][px]+0.05*abs(dx); bp=px
            D[y][x]=best+cost(im,x,y); P[y][x]=bp
    x=min(range(xmin,xmax+1),key=lambda x:D[H-1][x]); path=[0]*H
    for y in range(H-1,-1,-1):
        path[y]=x; x=P[y][x]
    return path, D[H-1][path[H-1]]
def remove(im, path):
    W,H=im.size; out=Image.new('RGBA',(W,H),(0,0,0,0))
    for y in range(H):
        xs=path[y]; row=[im.getpixel((x,y)) for x in range(W) if x!=xs]+[(0,0,0,0)]
        for x,c in enumerate(row): out.putpixel((x,y),c)
    return out
def carve(im, forced, xmin=None, xmax=None):
    p,c=seam(im,forced,xmin,xmax); return remove(im,p), p, c
