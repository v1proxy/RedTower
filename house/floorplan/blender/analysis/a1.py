exec(open('load.py').read())
print('V',V.shape,'T',T.shape, 'bbox',V.min(0),V.max(0))
# material areas
import collections
ma=np.bincount(M, weights=A, minlength=len(MN)); mt=np.bincount(M, minlength=len(MN))
for i in np.argsort(-ma): print(f'{MN[i][:45]:45s} area={ma[i]:9.1f} tris={mt[i]:8d} base={[round(x,2) for x in mats[i].get("base",mats[i]["diffuse"])][:4]} a={mats[i].get("alpha")}')
# horizontal up-facing faces z histogram
up=(N[:,2]>0.95)
h,edges=np.histogram(C[up,2],bins=np.arange(-2,36,0.25),weights=A[up])
for i in np.argsort(-h)[:25]: print('z=%.2f area=%.0f'%(edges[i],h[i]))
