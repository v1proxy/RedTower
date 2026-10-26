import numpy as np, json
d=np.load('raw.npz'); V=d['V'].astype(np.float64); T=d['T']; M=d['M'].astype(int); O=d['O']
meta=json.load(open('raw.json')); names=meta['objects']; mats=meta['materials']; MN=[m['name'] for m in mats]
P=V[T]; e1=P[:,1]-P[:,0]; e2=P[:,2]-P[:,0]; cr=np.cross(e1,e2); A=0.5*np.linalg.norm(cr,axis=1)
N=cr/np.maximum(2*A[:,None],1e-12); C=P.mean(1)
nobj=len(names)
