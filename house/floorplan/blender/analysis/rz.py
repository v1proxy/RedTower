exec(open('load.py').read())
rooms={
 0:{'guest_room':(-41.8,-35.5,0.5,8.2),'studio':(-42.0,-31.9,8.8,19.3),'bath_l1':(-31.5,-26.7,7.8,14.3),'entry':(-26.4,-19.9,0.5,9.8),'garage':(-19.3,0.3,0.5,19.5)},
 9:{'kitchen':(-42.0,-26.7,0.5,19.3),'living_room':(-19.4,0.0,0.5,19.3),'hall_l2':(-26.4,-19.6,4.4,19.3)},
 18:{'bedroom':(-41.8,-27.2,0.5,13.8),'bath_l3':(-41.8,-36.1,14.4,19.3),'closet_l3':(-35.4,-29.0,14.2,17.8),'office':(-26.4,-19.9,0.5,5.5),'terrace':(-19.3,0.4,0.3,19.5)}}
up=N[:,2]>0.9; dn=N[:,2]<-0.9
out={}
for L,rs in rooms.items():
    for nm,(x0,x1,y0,y1) in rs.items():
        inr=(C[:,0]>x0)&(C[:,0]<x1)&(C[:,1]>y0)&(C[:,1]<y1)
        f=inr&up&(C[:,2]>L-1.2)&(C[:,2]<L+0.6)
        # area-weighted mode of z
        zs=C[f,2]; ws=A[f]
        h={}; 
        for z,w in zip(np.round(zs,2),ws): h[z]=h.get(z,0)+w
        fz=max(h,key=h.get) if h else None
        c=inr&dn&(C[:,2]>(fz or L)+5)&(C[:,2]<(fz or L)+12)
        h2={}
        for z,w in zip(np.round(C[c,2],2),A[c]): h2[z]=h2.get(z,0)+w
        cz=max(h2,key=h2.get) if h2 else None
        out[nm]=(fz,cz)
        print(f'{nm:12s} floor {fz}  ceiling {cz}   top3floor {sorted(h.items(),key=lambda t:-t[1])[:3]}')
