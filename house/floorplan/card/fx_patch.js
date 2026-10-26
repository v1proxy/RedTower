// Red Tower FX patch for floor3dpro-axo-card (applied after axo_patch.js and ui_patch.js).
// - floor filter: cards in the same grid tagged `variables: { rt_floor: N }` hide while level N is hidden in the 3D view
// - windows: after sunset, while someone is home (`presence_entity`, default zone.home = people at home), the glass
//   glows warm as if the lights were on inside; `window_lights: "no"` turns it off
// - weather: the weather entity animated over the 3D view (rain, downpour, snow, hail, storm with lightning, clouds,
//   fog, wind, stars by night, and sunlight: the sun sits just outside the frame and travels around its edge through
//   the day (sun.sun azimuth and elevation relative to the camera); a soft corner glow with faint rays and ghosts,
//   no horizontal streak; colour shifts only slightly, cool at dawn, warm white at midday, soft peach at sunset).
//   Two layers: the sky (background, stars, clouds, lightning bolt) behind the model, whose own background is made
//   transparent; rain, snow, hail, fog, wind, the lightning flash and the sunlight in front of it. Card options: `weather_entity` (default weather.forecast_home),
//   `weather: "no"` to turn it off. Drawn on a 2D canvas above the model, 30 fps, sized to the card.
const FX_METHODS = String.raw`_rtFloorFilter(){try{const lv=this._displaylevels;if(!lv||!lv.length)return;const hc=this.parentNode,grid=hc&&hc.parentNode;if(!grid||!grid.children)return;const root=grid.getRootNode&&grid.getRootNode();if(root&&root.appendChild&&root!==document&&!(root.getElementById&&root.getElementById("rt-floor-filter"))){const s=document.createElement("style");s.id="rt-floor-filter";s.textContent=".rt-floor-hidden{display:none !important}";root.appendChild(s)}for(const k of grid.children){const cf=k.config||k._config;const v=cf&&cf.variables&&cf.variables.rt_floor;if(v===undefined||v===null||v==="")continue;k.classList.toggle("rt-floor-hidden",lv[Number(v)]===false)}}catch(e){}}
_rtWindows(){try{
  const hs=this._hass&&this._hass.states||{};const cfg=this._config||{};const sun=hs["sun.sun"];const night=!!sun&&sun.state==="below_horizon";
  const pe=cfg.presence_entity||"zone.home";const ps=hs[pe];let home=false;if(ps){const v=String(ps.state);home=pe.indexOf("zone.")===0?Number(v)>0:(v==="home"||v==="on"||v==="true")}
  const lit=night&&home&&cfg.window_lights!=="no";if(this._rtLit===lit&&this._rtLitScene===this._scene)return;
  if(!this._scene)return;this._rtLit=lit;this._rtLitScene=this._scene;
  this._scene.traverse(o=>{if(!o.isMesh||!o.material||!/^glass_l\d/.test(o.name))return;const m=o.material;const u=m.userData||(m.userData={});
    if(!u.rtOrig)u.rtOrig={c:m.color?m.color.getHex():null,e:m.emissive?m.emissive.getHex():null,ei:m.emissiveIntensity,op:m.opacity};const r=u.rtOrig;
    if(lit){if(m.color)m.color.setHex(0xffc477);if(m.emissive)m.emissive.setHex(0xff9535);m.emissiveIntensity=1.05;m.opacity=Math.max(r.op,0.9)}
    else{if(m.color&&r.c!==null)m.color.setHex(r.c);if(m.emissive&&r.e!==null)m.emissive.setHex(r.e);m.emissiveIntensity=r.ei;m.opacity=r.op}
    m.needsUpdate=true});
  this._requestRender&&this._requestRender("windows")}catch(e){}}
_rtWeatherEnsure(){try{
  this._rtWindows&&this._rtWindows();
  if(!this._content||!this._config||this._config.weather==="no")return;
  let W=this._rtW;
  if(!W||!W.cv||!W.cv.isConnected||!W.bv||!W.bv.isConnected){
    if(W){try{W.cv.remove();W.bv&&W.bv.remove()}catch(e){}}
    const mk=(z)=>{const c=document.createElement("canvas");c.className="rt-weather";c.style.cssText="position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:"+z;return c};
    const bv=mk(0),cv=mk(1);this._content.insertBefore(bv,this._content.firstChild);this._content.appendChild(cv);
    W=this._rtW={cv,ctx:cv.getContext("2d"),bv,bctx:bv.getContext("2d"),p:[],clouds:[],fog:[],stars:[],streaks:[],key:"",last:0,flash:0,bolt:null,next:0,running:false};
  }
  const rd=this._renderer&&this._renderer.domElement;if(rd&&rd.style.zIndex!=="1"){rd.style.position="relative";rd.style.zIndex="1"}
  if(this._scene&&this._rtBgScene!==this._scene){const bg=this._scene.background;this._rtBgCol=bg&&bg.getHexString?"#"+bg.getHexString():(this._config.backgroundColor&&this._config.backgroundColor!=="transparent"?this._config.backgroundColor:"#000000");this._scene.background=null;try{this._renderer.setClearColor(0,0)}catch(e){}this._rtBgScene=this._scene;this._requestRender&&this._requestRender("sky")}
  if(!W.running&&this._isConnected!==false){W.running=true;const loop=(ts)=>{if(!this._rtW||this._rtW!==W||!W.cv.isConnected||this._isConnected===false){W.running=false;return}requestAnimationFrame(loop);if(document.hidden||ts-W.last<33)return;const dt=Math.min(0.1,(ts-(W.last||ts))/1000);W.last=ts;this._rtWeatherFrame(W,dt,ts)};requestAnimationFrame(loop)}
}catch(e){}}
_rtSun(ctx,cw,ch,t,cond,sun,W){
  const sa=sun&&sun.attributes||{};const az=parseFloat(sa.azimuth),el=parseFloat(sa.elevation);if(isNaN(el)||el<-4)return;
  const rising=sa.rising===true||(sa.rising===undefined&&new Date().getHours()<12);
  let vaz=315;try{const cp=this._camera.position,tg=this._controls&&this._controls.target;if(cp&&tg){const dx=tg.x-cp.x,dn=-(tg.z-cp.z);if(Math.abs(dx)+Math.abs(dn)>1e-6)vaz=Math.atan2(dx,dn)*180/Math.PI}}catch(e){}
  let d=isNaN(az)?40:az-vaz;d=((d+540)%360)-180;
  let hx=Math.sin(d*Math.PI/180),vy=0.1+0.9*Math.sin(Math.max(0,el)*Math.PI/180);const nn=Math.hypot(hx,vy)||1;hx/=nn;vy/=nn;
  const cx=cw/2,cy=ch*0.40,m=0.035*Math.min(cw,ch);const tx=hx>1e-6?(cw+m-cx)/hx:(hx<-1e-6?(-m-cx)/hx:1e9),ty=vy>1e-6?(cy+m)/vy:1e9,tt=Math.min(tx,ty);
  const sx=cx+hx*tt,sy=cy-vy*tt;
  const mix=(p,q,k)=>{k=Math.max(0,Math.min(1,k));return p.map((v,i)=>Math.round(v+(q[i]-v)*k))};
  const NOON=[255,244,226],DAWN=[222,232,255],DUSK=[255,212,190];
  const col=mix(rising?DAWN:DUSK,NOON,el/12);const C=col.join(",");
  let I=0.55*({sunny:1,"clear-night":0.8,partlycloudy:0.75,windy:0.9,"windy-variant":0.85}[cond]||0.6)*(el<0?Math.max(0,1+el/4):1);
  let occ=0;for(const c of W.clouds){const q=Math.max(0,1-Math.hypot(sx-c.x,sy-c.y)/(c.w*0.6));occ=Math.max(occ,q)}I*=1-0.6*occ;
  if(I<=0.01)return;
  const L=Math.max(cw,ch),flick=0.95+0.05*Math.sin(t*5.3)*Math.sin(t*1.7);
  ctx.save();ctx.globalCompositeOperation="lighter";
  let g=ctx.createRadialGradient(sx,sy,0,sx,sy,L*1.15);g.addColorStop(0,"rgba("+C+","+(0.16*I).toFixed(3)+")");g.addColorStop(0.35,"rgba("+C+","+(0.05*I).toFixed(3)+")");g.addColorStop(1,"rgba("+C+",0)");ctx.fillStyle=g;ctx.fillRect(0,0,cw,ch);
  const hr=ch*0.30;g=ctx.createRadialGradient(sx,sy,0,sx,sy,hr);g.addColorStop(0,"rgba("+C+","+(0.55*I).toFixed(3)+")");g.addColorStop(0.25,"rgba("+C+","+(0.22*I).toFixed(3)+")");g.addColorStop(1,"rgba("+C+",0)");ctx.fillStyle=g;ctx.beginPath();ctx.arc(sx,sy,hr,0,6.283);ctx.fill();
  const rr=ch*0.11;g=ctx.createRadialGradient(sx,sy,rr*0.82,sx,sy,rr);g.addColorStop(0,"rgba(255,200,190,0)");g.addColorStop(0.4,"rgba(255,215,190,"+(0.035*I).toFixed(3)+")");g.addColorStop(0.7,"rgba(200,235,215,"+(0.03*I).toFixed(3)+")");g.addColorStop(1,"rgba(190,210,255,0)");ctx.fillStyle=g;ctx.beginPath();ctx.arc(sx,sy,rr,0,6.283);ctx.fill();
  const spikes=[[0,1],[Math.PI/3,0.8],[2*Math.PI/3,0.85],[Math.PI,1],[4*Math.PI/3,0.8],[5*Math.PI/3,0.85],[Math.PI/6,0.45],[Math.PI/2,0.5],[5*Math.PI/6,0.4],[7*Math.PI/6,0.45],[3*Math.PI/2,0.5],[11*Math.PI/6,0.4]];
  for(let i=0;i<spikes.length;i++){const a0=spikes[i][0]+0.12,len=ch*0.42*spikes[i][1]*(0.94+0.06*Math.sin(t*2.3+i*1.7))*flick,w=ch*(i<6?0.006:0.004);
    const ex=sx+Math.cos(a0)*len,ey=sy+Math.sin(a0)*len,nx=-Math.sin(a0)*w,ny=Math.cos(a0)*w;g=ctx.createLinearGradient(sx,sy,ex,ey);g.addColorStop(0,"rgba(255,250,240,"+(0.5*I).toFixed(3)+")");g.addColorStop(0.3,"rgba("+C+","+(0.16*I).toFixed(3)+")");g.addColorStop(1,"rgba("+C+",0)");
    ctx.fillStyle=g;ctx.beginPath();ctx.moveTo(sx+nx,sy+ny);ctx.lineTo(ex,ey);ctx.lineTo(sx-nx,sy-ny);ctx.closePath();ctx.fill()}
  const cor=ch*0.045;g=ctx.createRadialGradient(sx,sy,0,sx,sy,cor);g.addColorStop(0,"rgba(255,255,255,"+Math.min(1,I*1.2).toFixed(3)+")");g.addColorStop(0.45,"rgba(255,252,244,"+(0.9*I).toFixed(3)+")");g.addColorStop(1,"rgba("+C+",0)");ctx.fillStyle=g;ctx.beginPath();ctx.arc(sx,sy,cor,0,6.283);ctx.fill();
  const vx=cx-sx,vy2=ch*0.55-sy;
  const ghosts=[[0.32,0.020,"240,225,195",0.10,0],[0.55,0.060,"160,215,185",0.045,1],[0.78,0.030,"225,180,210",0.07,0],[1.05,0.095,"165,185,230",0.035,1],[1.30,0.042,"235,210,170",0.06,2],[1.62,0.140,"180,165,225",0.028,1],[1.85,0.026,"175,225,220",0.08,0]];
  for(const [k,r0,gc,al,shape] of ghosts){const gx=sx+vx*k,gy=sy+vy2*k,r=ch*r0,A=al*I;if(shape===1){ctx.beginPath();for(let j=0;j<6;j++){const an=j*Math.PI/3+0.2;const px=gx+Math.cos(an)*r,py=gy+Math.sin(an)*r;j?ctx.lineTo(px,py):ctx.moveTo(px,py)}ctx.closePath();g=ctx.createRadialGradient(gx,gy,0,gx,gy,r);g.addColorStop(0,"rgba("+gc+","+(A*0.5).toFixed(3)+")");g.addColorStop(0.85,"rgba("+gc+","+A.toFixed(3)+")");g.addColorStop(1,"rgba("+gc+","+(A*0.3).toFixed(3)+")");ctx.fillStyle=g;ctx.fill()}
    else if(shape===2){ctx.strokeStyle="rgba("+gc+","+(A*1.6).toFixed(3)+")";ctx.lineWidth=Math.max(1,r*0.12);ctx.beginPath();ctx.arc(gx,gy,r,0,6.283);ctx.stroke()}
    else{g=ctx.createRadialGradient(gx,gy,0,gx,gy,r);g.addColorStop(0,"rgba("+gc+","+(A*1.4).toFixed(3)+")");g.addColorStop(1,"rgba("+gc+",0)");ctx.fillStyle=g;ctx.beginPath();ctx.arc(gx,gy,r,0,6.283);ctx.fill()}}
  ctx.restore()}
_rtWeatherFrame(W,dt,ts){
  const cv=W.cv,ctx=W.ctx,bv=W.bv,bx=W.bctx,box=this._content;const cw=box.clientWidth,ch=box.clientHeight;if(!cw||!ch)return;
  const dpr=Math.min(window.devicePixelRatio||1,1.5);if(cv.width!==Math.round(cw*dpr)||cv.height!==Math.round(ch*dpr)){cv.width=bv.width=Math.round(cw*dpr);cv.height=bv.height=Math.round(ch*dpr);W.key=""}
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,cw,ch);bx.setTransform(dpr,0,0,dpr,0,0);bx.fillStyle=this._rtBgCol||"#000000";bx.fillRect(0,0,cw,ch);
  const hs=this._hass&&this._hass.states||{};const ent=this._config.weather_entity||"weather.forecast_home";const ws=hs[ent];if(!ws)return;
  const cond=String(ws.state||"");const sun=hs["sun.sun"];const night=sun?sun.state==="below_horizon":false;
  const a=ws.attributes||{};let wind=parseFloat(a.wind_speed)||0;if(a.wind_speed_unit==="km/h")wind/=1.609;if(a.wind_speed_unit==="m/s")wind*=2.237;
  const brg=parseFloat(a.wind_bearing);const dir=isNaN(brg)?1:(Math.sin((brg+180)*Math.PI/180)>=0?1:-1);
  const slant=Math.max(0,Math.min(1,wind/35))*dir;
  const area=cw*ch/1.12e6;const R=(n)=>n>0?Math.max(8,Math.round(n*area)):0;
  const rain={rainy:150,pouring:340,"lightning-rainy":260,"snowy-rainy":110}[cond]||0;
  const snow={snowy:190,"snowy-rainy":90}[cond]||0;const hail=cond==="hail"?140:0;
  const storm=cond==="lightning"||cond==="lightning-rainy";
  const cloudN={cloudy:7,partlycloudy:4,rainy:7,pouring:8,"lightning-rainy":8,lightning:8,snowy:7,"snowy-rainy":7,hail:7,fog:3}[cond]||0;
  const cloudCol=storm||cond==="pouring"?"70,74,84":(cond==="cloudy"||rain||snow||hail?"125,130,140":"200,205,215");
  const cloudA=cond==="partlycloudy"?0.20:(storm||cond==="pouring"?0.46:0.34);
  const key=cond+"|"+night+"|"+cw+"x"+ch;
  if(W.key!==key){W.key=key;W.p=[];const rnd=Math.random;
    for(let i=0;i<R(rain);i++)W.p.push({k:"r",x:rnd()*cw*1.3-cw*0.15,y:rnd()*ch,l:10+rnd()*14,v:(cond==="pouring"?1350:950)+rnd()*350});
    for(let i=0;i<R(snow);i++)W.p.push({k:"s",x:rnd()*cw,y:rnd()*ch,r:1.1+rnd()*2.1,v:28+rnd()*44,ph:rnd()*6.28});
    for(let i=0;i<R(hail);i++)W.p.push({k:"h",x:rnd()*cw*1.2-cw*0.1,y:rnd()*ch,r:1.3+rnd()*1.3,v:650+rnd()*300});
    W.clouds=[];for(let i=0;i<cloudN;i++)W.clouds.push({x:rnd()*cw*1.2-cw*0.1,y:ch*(0.02+rnd()*0.30),w:cw*(0.16+rnd()*0.16),v:(6+rnd()*14)*(slant<0?-1:1)});
    W.fog=[];if(cond==="fog")for(let i=0;i<4;i++)W.fog.push({y:ch*(0.35+i*0.17),x:rnd()*cw,v:(8+rnd()*10)*(i%2?1:-1)});
    W.stars=[];if(night&&!rain&&!snow&&!hail&&!storm&&cond!=="cloudy"&&cond!=="fog"){const n=cond==="clear-night"||cond==="sunny"?110:45;for(let i=0;i<R(n);i++)W.stars.push({x:rnd()*cw,y:rnd()*ch*0.55,r:0.5+rnd()*1.1,ph:rnd()*6.28,f:0.6+rnd()*1.6})}
    W.streaks=[];if(cond==="windy"||cond==="windy-variant")for(let i=0;i<R(26);i++)W.streaks.push({x:rnd()*cw,y:rnd()*ch,l:40+rnd()*90,v:(380+rnd()*320)*dir})}
  const t=ts/1000;
  if(W.stars.length){for(const s of W.stars){const al=0.35+0.45*(0.5+0.5*Math.sin(t*s.f+s.ph));bx.fillStyle="rgba(235,240,255,"+al.toFixed(3)+")";bx.beginPath();bx.arc(s.x,s.y,s.r,0,6.283);bx.fill()}}
  if(cond==="sunny"||cond==="partlycloudy"||cond==="windy"||cond==="windy-variant"||cond==="clear-night")this._rtSun(ctx,cw,ch,t,cond,sun,W);
  for(const c of W.clouds){c.x+=c.v*dt;if(c.v>0&&c.x-c.w>cw)c.x=-c.w;if(c.v<0&&c.x+c.w<0)c.x=cw+c.w;
    for(let j=0;j<5;j++){const qx=c.x+(j-2)*c.w*0.22,qy=c.y+((j%2)?-0.06:0.04)*c.w,br=c.w*(j===2?0.36:0.26);const g=bx.createRadialGradient(qx,qy,0,qx,qy,br);g.addColorStop(0,"rgba("+cloudCol+","+cloudA+")");g.addColorStop(1,"rgba("+cloudCol+",0)");bx.fillStyle=g;bx.beginPath();bx.arc(qx,qy,br,0,6.283);bx.fill()}}
  for(const f of W.fog){f.x+=f.v*dt;if(f.x>cw)f.x-=cw;if(f.x<0)f.x+=cw;for(const off of [f.x-cw,f.x]){const g=ctx.createLinearGradient(0,f.y-ch*0.12,0,f.y+ch*0.12);g.addColorStop(0,"rgba(210,215,220,0)");g.addColorStop(0.5,"rgba(210,215,220,0.16)");g.addColorStop(1,"rgba(210,215,220,0)");ctx.fillStyle=g;ctx.fillRect(off,f.y-ch*0.12,cw,ch*0.24)}}
  if(W.streaks.length){ctx.strokeStyle="rgba(220,225,235,0.22)";ctx.lineWidth=1;ctx.beginPath();for(const s of W.streaks){s.x+=s.v*dt;if(s.v>0&&s.x>cw+s.l){s.x=-s.l;s.y=Math.random()*ch}if(s.v<0&&s.x<-s.l){s.x=cw+s.l;s.y=Math.random()*ch}ctx.moveTo(s.x,s.y);ctx.lineTo(s.x+s.l*(s.v>0?-1:1),s.y+2)}ctx.stroke()}
  if(W.p.length){ctx.lineCap="round";ctx.strokeStyle="rgba(175,195,225,0.55)";ctx.lineWidth=1.2;ctx.beginPath();
    for(const q of W.p){if(q.k!=="r")continue;q.y+=q.v*dt;q.x+=q.v*dt*slant*0.35;if(q.y>ch+20){q.y=-20-Math.random()*40;q.x=Math.random()*cw*1.3-cw*0.15}ctx.moveTo(q.x,q.y);ctx.lineTo(q.x-q.l*slant*0.35,q.y-q.l)}ctx.stroke();
    ctx.fillStyle="rgba(255,255,255,0.85)";for(const q of W.p){if(q.k==="s"){q.y+=q.v*dt;q.x+=Math.sin(t*1.3+q.ph)*14*dt+slant*20*dt;if(q.y>ch+5){q.y=-5;q.x=Math.random()*cw}ctx.beginPath();ctx.arc(q.x,q.y,q.r,0,6.283);ctx.fill()}else if(q.k==="h"){q.y+=q.v*dt;q.x+=q.v*dt*slant*0.2;if(q.y>ch+5){q.y=-5;q.x=Math.random()*cw*1.2-cw*0.1}ctx.beginPath();ctx.arc(q.x,q.y,q.r,0,6.283);ctx.fill()}}}
  if(storm){if(!W.next)W.next=t+2+Math.random()*5;if(t>W.next){W.flash=1;W.next=t+3+Math.random()*7;const x0=cw*(0.15+Math.random()*0.7);const pts=[[x0,0]];let x=x0,y=0;while(y<ch*0.55){y+=ch*(0.05+Math.random()*0.07);x+=(Math.random()-0.5)*cw*0.06;pts.push([x,y])}W.bolt={pts,t:t}}
    if(W.flash>0){ctx.fillStyle="rgba(235,240,255,"+(0.42*W.flash).toFixed(3)+")";ctx.fillRect(0,0,cw,ch);W.flash=Math.max(0,W.flash-dt*3.5)}
    if(W.bolt&&t-W.bolt.t<0.18){bx.strokeStyle="rgba(255,255,255,0.95)";bx.lineWidth=2.2;bx.shadowColor="rgba(170,200,255,0.9)";bx.shadowBlur=12;bx.beginPath();W.bolt.pts.forEach(([px,py],i)=>i?bx.lineTo(px,py):bx.moveTo(px,py));bx.stroke();bx.shadowBlur=0}}
}
`;
function fxPatch(src) {
  const n0 = src.length;
  const methods = FX_METHODS.replace(/\n\s*/g, '');
  if (src.includes('_rtFloorFilter(){')) {  // already patched: swap in the current methods only
    const a = src.indexOf('_rtFloorFilter(){'), b = src.search(/_toggleVisibleLevel\([\w$]+\)\{setTimeout\(/);
    if (b < a) throw new Error('patched block not found');
    src = src.slice(0, a) + methods + src.slice(b);
    return { src, grew: src.length - n0, upgraded: true };
  }
  const reT = /_toggleVisibleLevel\(([\w$]+)\)\{/;
  const m = src.match(reT);
  if (!m) throw new Error('_toggleVisibleLevel not found');
  src = src.replace(reT, (all, a) => methods + `_toggleVisibleLevel(${a}){setTimeout(()=>this._rtFloorFilter&&this._rtFloorFilter(),0);`);
  const reZ = /_zIndexChecker\(\)\{/;
  if (!reZ.test(src)) throw new Error('_zIndexChecker not found');
  src = src.replace(reZ, '_zIndexChecker(){this._rtFloorFilter&&this._rtFloorFilter();this._rtWeatherEnsure&&this._rtWeatherEnsure();');
  const reV = /_setVisibleLevel\(([\w$]+)\)\{/;
  if (!reV.test(src)) throw new Error('_setVisibleLevel not found');
  src = src.replace(reV, (all, a) => `_setVisibleLevel(${a}){setTimeout(()=>this._rtFloorFilter&&this._rtFloorFilter(),0);`);
  return { src, grew: src.length - n0 };
}
if (typeof module !== 'undefined') module.exports = fxPatch;
