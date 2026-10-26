exec(open('load.py').read())
from scipy import ndimage
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
R=0.1; X0,X1,Y0,Y1=-44,2,-1,21
W=int((X1-X0)/R); H=int((Y1-Y0)/R)
def section_mask(z):
    d=P[:,:,2]-z; s=np.sign(d); s[s==0]=1
    cross=~((s[:,0]==s[:,1])&(s[:,1]==s[:,2]))
    idx=np.where(cross)[0]
    img=np.zeros((H,W),bool)
    p=P[idx]; dd=d[idx]
    pts=[]
    for a,b in ((0,1),(1,2),(2,0)):
        m=(dd[:,a]>=0)!=(dd[:,b]>=0)
        t=np.where(m, dd[:,a]/np.where(m,dd[:,a]-dd[:,b],1), np.nan)
        q=p[:,a]+t[:,None]*(p[:,b]-p[:,a]); pts.append(q)
    pts=np.stack(pts,1) # n,3,3 with nan where no crossing
    for i in range(len(idx)):
        qq=pts[i][~np.isnan(pts[i][:,0])]
        if len(qq)<2: continue
        a,b=qq[0][:2],qq[1][:2]
        n=int(max(abs(b-a))/R*2)+2
        xs=np.linspace(a[0],b[0],n); ys=np.linspace(a[1],b[1],n)
        ix=((xs-X0)/R).astype(int); iy=((ys-Y0)/R).astype(int)
        ok=(ix>=0)&(ix<W)&(iy>=0)&(iy<H); img[iy[ok],ix[ok]]=True
    return img
import json,sys
seeds=json.loads(sys.argv[1]); z=float(sys.argv[2]); tag=sys.argv[3]
wall=section_mask(z+4.0)|section_mask(z+2.5)
wall=ndimage.binary_dilation(wall,iterations=1)
free=~wall
lab,n=ndimage.label(free)
out={}
fig,ax=plt.subplots(figsize=(18,8.5))
ax.imshow(wall,origin='lower',extent=(X0,X1,Y0,Y1),cmap='Greys')
cols=plt.get_cmap('tab10')
for k,(nm,(sx,sy)) in enumerate(seeds.items()):
    l=lab[int((sy-Y0)/R),int((sx-X0)/R)]
    if l==0: print(nm,'seed on wall'); continue
    m=lab==l; ys,xs=np.where(m)
    x0,x1=X0+xs.min()*R,X0+(xs.max()+1)*R; y0,y1=Y0+ys.min()*R,Y0+(ys.max()+1)*R
    area=m.sum()*R*R
    out[nm]=dict(x0=round(x0,2),x1=round(x1,2),y0=round(y0,2),y1=round(y1,2),area=round(area,1),fill=round(area/((x1-x0)*(y1-y0)),2))
    print(nm,out[nm])
    ov=np.zeros((H,W,4)); ov[m]=cols(k%10); ov[m,3]=0.35
    ax.imshow(ov,origin='lower',extent=(X0,X1,Y0,Y1))
    ax.text(sx,sy,nm,fontsize=9,ha='center')
ax.set_xticks(range(X0,X1+1,1)); ax.set_yticks(range(Y0,Y1+1,1)); ax.tick_params(labelsize=6); ax.grid(alpha=.25)
plt.tight_layout(); plt.savefig(f'rooms_{tag}.png',dpi=72)
json.dump(out,open(f'rooms_{tag}.json','w'),indent=1)
