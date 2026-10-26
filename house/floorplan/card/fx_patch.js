// Red Tower FX patch for floor3dpro-axo-card (applied after axo_patch.js and ui_patch.js).
// - floor filter: cards in the same grid tagged `variables: { rt_floor: N }` hide while level N is hidden in the 3D view
// - weather: the weather entity animated over the 3D view (rain, downpour, snow, hail, storm with lightning, clouds,
//   fog, wind, stars by night, and sunlight: the sun itself stays out of frame and only its light comes in, from the
//   side it is on (sun.sun azimuth and elevation relative to the camera), bluish at dawn, yellow at midday, red at
//   sunset; no lens flares). Card options: `weather_entity` (default weather.forecast_home),
//   `weather: "no"` to turn it off. Drawn on a 2D canvas above the model, 30 fps, sized to the card.
const FX_METHODS = String.raw`_rtFloorFilter(){try{const lv=this._displaylevels;if(!lv||!lv.length)return;const hc=this.parentNode,grid=hc&&hc.parentNode;if(!grid||!grid.children)return;const root=grid.getRootNode&&grid.getRootNode();if(root&&root.appendChild&&root!==document&&!(root.getElementById&&root.getElementById("rt-floor-filter"))){const s=document.createElement("style");s.id="rt-floor-filter";s.textContent=".rt-floor-hidden{display:none !important}";root.appendChild(s)}for(const k of grid.children){const cf=k.config||k._config;const v=cf&&cf.variables&&cf.variables.rt_floor;if(v===undefined||v===null||v==="")continue;k.classList.toggle("rt-floor-hidden",lv[Number(v)]===false)}}catch(e){}}
_rtWeatherEnsure(){try{
  if(!this._content||!this._config||this._config.weather==="no")return;
  let W=this._rtW;
  if(!W||!W.cv||!W.cv.isConnected){
    const cv=document.createElement("canvas");cv.className="rt-weather";
    cv.style.cssText="position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:1";
    this._content.appendChild(cv);
    W=this._rtW={cv,ctx:cv.getContext("2d"),p:[],clouds:[],fog:[],stars:[],streaks:[],key:"",last:0,flash:0,bolt:null,next:0,running:false};
  }
  if(!W.running&&this._isConnected!==false){W.running=true;const loop=(ts)=>{if(!this._rtW||this._rtW!==W||!W.cv.isConnected||this._isConnected===false){W.running=false;return}requestAnimationFrame(loop);if(document.hidden||ts-W.last<33)return;const dt=Math.min(0.1,(ts-(W.last||ts))/1000);W.last=ts;this._rtWeatherFrame(W,dt,ts)};requestAnimationFrame(loop)}
}catch(e){}}
_rtSun(ctx,cw,ch,t,cond,sun,W){
  const sa=sun&&sun.attributes||{};const az=parseFloat(sa.azimuth),el=parseFloat(sa.elevation);if(isNaN(el)||el<-6)return;
  const rising=sa.rising===true||(sa.rising===undefined&&new Date().getHours()<12);
  let vaz=315;try{const cp=this._camera.position,tg=this._controls&&this._controls.target;if(cp&&tg){const dx=tg.x-cp.x,dn=-(tg.z-cp.z);if(Math.abs(dx)+Math.abs(dn)>1e-6)vaz=Math.atan2(dx,dn)*180/Math.PI}}catch(e){}
  let d=isNaN(az)?40:az-vaz;d=((d+540)%360)-180;
  const er=Math.max(0,el)*Math.PI/180;let hx=Math.sin(d*Math.PI/180),vy=0.35+0.65*Math.sin(er);const nn=Math.hypot(hx,vy)||1;hx/=nn;vy/=nn;
  const L=Math.hypot(cw,ch),R=0.5*L+0.12*Math.max(cw,ch);const sx=cw/2+hx*R,sy=ch*0.45-vy*R;
  const mix=(p,q,k)=>{k=Math.max(0,Math.min(1,k));return p.map((v,i)=>Math.round(v+(q[i]-v)*k))};
  const DAWN=[130,170,255],MORN=[255,238,200],NOON=[255,220,110],EVE=[255,150,65],SET=[255,62,45];
  const col=rising?(el<2?mix(DAWN,DAWN,0):(el<14?mix(DAWN,MORN,(el-2)/12):mix(MORN,NOON,(el-14)/20))):(el<2?SET:(el<14?mix(SET,EVE,(el-2)/12):mix(EVE,NOON,(el-14)/22)));
  const C=col.join(",");
  let I=el<0?0.45*(1+el/6):Math.min(1,0.6+el/25);I*={sunny:1,"clear-night":0.85,partlycloudy:0.7,windy:0.9,"windy-variant":0.85}[cond]||0.6;
  let occ=0;for(const c of W.clouds){const q=Math.max(0,1-Math.hypot(c.x-(cw/2+hx*cw*0.45),c.y-(ch*0.45-vy*ch*0.45))/(c.w*0.7));occ=Math.max(occ,q)}I*=1-0.5*occ;
  if(I<=0.01)return;
  ctx.save();ctx.globalCompositeOperation="lighter";
  let g=ctx.createRadialGradient(sx,sy,0,sx,sy,R+L*0.55);g.addColorStop(0,"rgba("+C+","+(0.50*I).toFixed(3)+")");g.addColorStop(0.32,"rgba("+C+","+(0.24*I).toFixed(3)+")");g.addColorStop(0.62,"rgba("+C+","+(0.07*I).toFixed(3)+")");g.addColorStop(1,"rgba("+C+",0)");ctx.fillStyle=g;ctx.fillRect(0,0,cw,ch);
  const base=Math.atan2(ch*0.5-sy,cw*0.5-sx),len=R+L*0.75;
  for(let i=0;i<6;i++){const off=(i-2.5)*0.085+0.02*Math.sin(t*0.13+i*2.1),half=0.018+0.012*((i*7)%3),A=(0.045+0.02*Math.sin(t*0.4+i*1.3))*I;
    const a1=base+off-half,a2=base+off+half;g=ctx.createRadialGradient(sx,sy,R*0.6,sx,sy,len);g.addColorStop(0,"rgba("+C+","+A.toFixed(3)+")");g.addColorStop(1,"rgba("+C+",0)");
    ctx.fillStyle=g;ctx.beginPath();ctx.moveTo(sx,sy);ctx.lineTo(sx+Math.cos(a1)*len,sy+Math.sin(a1)*len);ctx.lineTo(sx+Math.cos(a2)*len,sy+Math.sin(a2)*len);ctx.closePath();ctx.fill()}
  ctx.restore()}
_rtWeatherFrame(W,dt,ts){
  const cv=W.cv,ctx=W.ctx,box=this._content;const cw=box.clientWidth,ch=box.clientHeight;if(!cw||!ch)return;
  const dpr=Math.min(window.devicePixelRatio||1,1.5);if(cv.width!==Math.round(cw*dpr)||cv.height!==Math.round(ch*dpr)){cv.width=Math.round(cw*dpr);cv.height=Math.round(ch*dpr);W.key=""}
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,cw,ch);
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
  if(W.stars.length){for(const s of W.stars){const al=0.35+0.45*(0.5+0.5*Math.sin(t*s.f+s.ph));ctx.fillStyle="rgba(235,240,255,"+al.toFixed(3)+")";ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,6.283);ctx.fill()}}
  if(cond==="sunny"||cond==="partlycloudy"||cond==="windy"||cond==="windy-variant"||cond==="clear-night")this._rtSun(ctx,cw,ch,t,cond,sun,W);
  for(const c of W.clouds){c.x+=c.v*dt;if(c.v>0&&c.x-c.w>cw)c.x=-c.w;if(c.v<0&&c.x+c.w<0)c.x=cw+c.w;
    for(let j=0;j<5;j++){const bx=c.x+(j-2)*c.w*0.22,by=c.y+((j%2)?-0.06:0.04)*c.w,br=c.w*(j===2?0.36:0.26);const g=ctx.createRadialGradient(bx,by,0,bx,by,br);g.addColorStop(0,"rgba("+cloudCol+","+cloudA+")");g.addColorStop(1,"rgba("+cloudCol+",0)");ctx.fillStyle=g;ctx.beginPath();ctx.arc(bx,by,br,0,6.283);ctx.fill()}}
  for(const f of W.fog){f.x+=f.v*dt;if(f.x>cw)f.x-=cw;if(f.x<0)f.x+=cw;for(const off of [f.x-cw,f.x]){const g=ctx.createLinearGradient(0,f.y-ch*0.12,0,f.y+ch*0.12);g.addColorStop(0,"rgba(210,215,220,0)");g.addColorStop(0.5,"rgba(210,215,220,0.16)");g.addColorStop(1,"rgba(210,215,220,0)");ctx.fillStyle=g;ctx.fillRect(off,f.y-ch*0.12,cw,ch*0.24)}}
  if(W.streaks.length){ctx.strokeStyle="rgba(220,225,235,0.22)";ctx.lineWidth=1;ctx.beginPath();for(const s of W.streaks){s.x+=s.v*dt;if(s.v>0&&s.x>cw+s.l){s.x=-s.l;s.y=Math.random()*ch}if(s.v<0&&s.x<-s.l){s.x=cw+s.l;s.y=Math.random()*ch}ctx.moveTo(s.x,s.y);ctx.lineTo(s.x+s.l*(s.v>0?-1:1),s.y+2)}ctx.stroke()}
  if(W.p.length){ctx.lineCap="round";ctx.strokeStyle="rgba(175,195,225,0.55)";ctx.lineWidth=1.2;ctx.beginPath();
    for(const q of W.p){if(q.k!=="r")continue;q.y+=q.v*dt;q.x+=q.v*dt*slant*0.35;if(q.y>ch+20){q.y=-20-Math.random()*40;q.x=Math.random()*cw*1.3-cw*0.15}ctx.moveTo(q.x,q.y);ctx.lineTo(q.x-q.l*slant*0.35,q.y-q.l)}ctx.stroke();
    ctx.fillStyle="rgba(255,255,255,0.85)";for(const q of W.p){if(q.k==="s"){q.y+=q.v*dt;q.x+=Math.sin(t*1.3+q.ph)*14*dt+slant*20*dt;if(q.y>ch+5){q.y=-5;q.x=Math.random()*cw}ctx.beginPath();ctx.arc(q.x,q.y,q.r,0,6.283);ctx.fill()}else if(q.k==="h"){q.y+=q.v*dt;q.x+=q.v*dt*slant*0.2;if(q.y>ch+5){q.y=-5;q.x=Math.random()*cw*1.2-cw*0.1}ctx.beginPath();ctx.arc(q.x,q.y,q.r,0,6.283);ctx.fill()}}}
  if(storm){if(!W.next)W.next=t+2+Math.random()*5;if(t>W.next){W.flash=1;W.next=t+3+Math.random()*7;const x0=cw*(0.15+Math.random()*0.7);const pts=[[x0,0]];let x=x0,y=0;while(y<ch*0.55){y+=ch*(0.05+Math.random()*0.07);x+=(Math.random()-0.5)*cw*0.06;pts.push([x,y])}W.bolt={pts,t:t}}
    if(W.flash>0){ctx.fillStyle="rgba(235,240,255,"+(0.42*W.flash).toFixed(3)+")";ctx.fillRect(0,0,cw,ch);W.flash=Math.max(0,W.flash-dt*3.5)}
    if(W.bolt&&t-W.bolt.t<0.18){ctx.strokeStyle="rgba(255,255,255,0.95)";ctx.lineWidth=2.2;ctx.shadowColor="rgba(170,200,255,0.9)";ctx.shadowBlur=12;ctx.beginPath();W.bolt.pts.forEach(([px,py],i)=>i?ctx.lineTo(px,py):ctx.moveTo(px,py));ctx.stroke();ctx.shadowBlur=0}}
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
