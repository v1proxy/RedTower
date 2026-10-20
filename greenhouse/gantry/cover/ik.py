import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, math, arm280 as A, collide as C
from scipy.optimize import least_squares
FACE=1.7
def tool_T(q):
    T=A.frames(q)['joint6_flange'].copy(); T[:3,3]*=1000
    Tz=np.eye(4); Tz[2,3]=FACE
    return T@Tz
def fk_point(q,p_t):
    T=tool_T(q); return T[:3,:3]@np.asarray(p_t)+T[:3,3], T[:3,:3]
LO=np.array([l[0] for l in A.LIMITS]); HI=np.array([l[1] for l in A.LIMITS])
def solve(target, p_t, zdir=(0,-1,0), xdir=None, seeds=40, rng=0, w=200.0):
    r=np.random.default_rng(rng); best=[]
    zdir=None if zdir is None else np.asarray(zdir,float)
    def res(q):
        p,R=fk_point(q,p_t)
        e=list(p-target)+([0,0,0] if zdir is None else list(w*(R[:,2]-zdir)))
        if xdir is not None: e+=list(w*(R[:,1]-np.asarray(xdir)))
        return e
    for s in range(seeds):
        q0=r.uniform(LO*0.8,HI*0.8)
        try: sol=least_squares(res,q0,bounds=(LO,HI),xtol=1e-6,ftol=1e-6,max_nfev=400)
        except Exception: continue
        p,R=fk_point(sol.x,p_t)
        err=np.linalg.norm(p-target)
        ang=0.0 if zdir is None else math.degrees(math.acos(np.clip(R[:,2]@zdir,-1,1)))
        if xdir is not None: ang=max(ang,math.degrees(math.acos(np.clip(R[:,1]@np.asarray(xdir),-1,1))))
        if err<1.0 and ang<2: best.append((sol.x,err,ang))
    return best
