exec(open('load.py').read())
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
def section(z):
    d=P[:,:,2]-z; s=np.sign(d); s[s==0]=1
    cross=~((s[:,0]==s[:,1])&(s[:,1]==s[:,2]))
    idx=np.where(cross)[0]; segs=[]; mm=[]
    for i in idx:
        p=P[i]; dd=d[i]; pts=[]
        for a,b in ((0,1),(1,2),(2,0)):
            if (dd[a]>=0)!=(dd[b]>=0):
                t=dd[a]/(dd[a]-dd[b]); pts.append(p[a]+t*(p[b]-p[a]))
        if len(pts)>=2: segs.append([pts[0][:2],pts[1][:2]]); mm.append(M[i])
    return np.array(segs), np.array(mm)
cmap=plt.get_cmap('tab20')
levels={'L1 (z=0)':0.0,'L2 (z=9)':9.0,'L3 (z=18)':18.0,'Roof (z=26)':26.0}
fig,axs=plt.subplots(2,2,figsize=(22,15))
for ax,(nm,z) in zip(axs.flat,levels.items()):
    # floors
    sel=(N[:,2]>0.9)&(np.abs(C[:,2]-z)<0.6)
    polys=P[sel][:,:,:2]
    ax.add_collection(PolyCollection(polys,facecolor='#e8e0d0',edgecolor='none'))
    segs,mm=section(z+4.0)
    cols=[cmap(m%20) for m in mm]
    ax.add_collection(LineCollection(segs,colors=cols,linewidths=0.6))
    ax.set_xlim(-58,3); ax.set_ylim(-12,25); ax.set_aspect('equal'); ax.set_title(nm+' section @+4ft'); ax.grid(alpha=.3)
    ax.set_xticks(range(-56,4,4)); ax.set_yticks(range(-12,26,4))
plt.tight_layout(); plt.savefig('plans.png',dpi=70)
print('ok')
