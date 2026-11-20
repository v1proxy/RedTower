// Red Tower security patch for floor3dpro-axo-card (applied after fx_patch.js).
// The house's sensors in the 3D view, drawn on their own 2D canvas over the model (x-ray, so a room is never hidden
// behind the walls or the roof):
// - smoke, CO, gas and heat alarms: the room as a red volume pulsing at an alarm cadence, a tag over it, and the card
//   edge glowing red; an alarm whose room is unknown, or an alarm panel in `triggered`, lights the whole card edge
// - water leaks: a shallow blue volume on the room floor; CO2 over `security_co2` ppm: an orange volume
// - motion, occupancy and presence: the room floor glows amber with a ripple, then fades out after the sensor clears
// - open doors and windows: the opening as a red pane rising from its status strip, with a tag
// - every active event is listed top right, alarms first
// Sensors are found by device class. Where each one is: `security_objects` (entity -> model objects) first, then the
// entity's or its device's area (area_id -> room_<area_id>, or `security_areas`), then a room word in its name or its
// device's name (`security_keywords`). Motion, leaks and openings on a hidden floor are not drawn; alarms always are.
// Options: security: "no", security_objects, security_areas, security_exclude, security_kinds (entity -> kind),
// security_keywords (word -> room object), security_aggregates (entity -> id prefix of its members: an "any camera"
// sensor is left out while one of its own per-camera sensors is on), security_height (cm, 240),
// security_open_height (cm, 200), security_motion_fade (s, 20), security_co2 (ppm, 1500), security_list: "no".
const SEC_METHODS = String.raw`_rtSecEnsure(){try{
  const cfg=this._config||{};if(cfg.security==="no"||!this._content||!this._scene||!this._camera||!this._renderer)return;
  let S=this._rtS;
  if(!S||!S.cv||!S.cv.isConnected){if(S&&S.cv){try{S.cv.remove()}catch(e){}}
    const c=document.createElement("canvas");c.className="rt-sec";c.style.cssText="position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:1";
    this._content.appendChild(c);S=this._rtS={cv:c,ctx:c.getContext("2d"),items:[],geo:{},running:false,last:0,hass:null,scene:null}}
  else{let n=S.cv.nextSibling;while(n&&n.tagName!=="CANVAS")n=n.nextSibling;if(n)this._content.appendChild(S.cv)}
  if(S.scene!==this._scene){S.scene=this._scene;S.geo={};S.hass=null}
  if(S.hass!==this._hass){S.hass=this._hass;this._rtSecScan(S)}
  if(S.items.length&&!S.running&&this._isConnected!==false){S.running=true;
    const loop=(ts)=>{if(this._rtS!==S||!S.cv.isConnected||this._isConnected===false){S.running=false;return}
      if(!S.items.length){S.running=false;S.ctx.setTransform(1,0,0,1,0,0);S.ctx.clearRect(0,0,S.cv.width,S.cv.height);return}
      requestAnimationFrame(loop);if(document.hidden||ts-S.last<33)return;S.last=ts;try{this._rtSecFrame(S,ts)}catch(e){}};
    requestAnimationFrame(loop)}
}catch(e){}}
_rtSecScan(S){
  const H=this._hass||{},hs=H.states||{},cfg=this._config||{},ents=H.entities||{},devs=H.devices||{},areas=H.areas||{};
  const excl=new Set(cfg.security_exclude||[]),objs=cfg.security_objects||{},amap=cfg.security_areas||{},kinds=cfg.security_kinds||{};
  const DC={smoke:"smoke",carbon_monoxide:"co",gas:"gas",heat:"heat",moisture:"leak",motion:"motion",occupancy:"motion",presence:"motion",door:"open",window:"open",opening:"open",garage_door:"open"};
  const KW=cfg.security_keywords||{guest:"room_guest_room",studio:"room_studio",entry:"room_entry",foyer:"room_entry",garage:"room_garage",kitchen:"room_kitchen",living:"room_living_room",hall:"room_hall_l2",stair:"room_hall_l2",bedroom:"room_bedroom",closet:"room_closet_l3",office:"room_office"};
  const now=Date.now(),fade=1000*(cfg.security_motion_fade!==undefined?Number(cfg.security_motion_fade):20),co2=Number(cfg.security_co2)||1500;
  const has=n=>!!(n&&this._scene.getObjectByName(n));const items=[];
  for(const id in hs){if(excl.has(id))continue;const st=hs[id],a=st.attributes||{},dom=id.split(".")[0];
    let k=kinds[id];
    if(!k){if(dom==="binary_sensor")k=DC[a.device_class];else if(dom==="alarm_control_panel")k="alarm";else if(dom==="sensor"&&a.device_class==="carbon_dioxide")k="co2"}
    if(!k)continue;
    const re=ents[id];if(re&&(re.hidden||re.entity_category)&&!kinds[id])continue;
    const s=st.state,lc=Date.parse(st.last_changed)||now;let until=Infinity,on=false;
    if(k==="alarm")on=s==="triggered";else if(k==="co2"){const v=parseFloat(s);on=!isNaN(v)&&v>=co2}else if(s==="on")on=true;else if(k==="motion"&&s==="off"&&now-lc<fade){on=true;until=lc+fade}
    if(!on)continue;
    const dev=re&&re.device_id?devs[re.device_id]:null,area=(re&&re.area_id)||(dev&&dev.area_id)||null;
    const o=[].concat(objs[id]||[]).filter(has);let rooms=[];
    if(area){const m=[].concat(amap[area]||[]).filter(has);rooms=m.length?m:(has("room_"+area)?["room_"+area]:[])}
    if(!o.length&&!rooms.length){const txt=((a.friendly_name||"")+" "+((dev&&(dev.name_by_user||dev.name))||"")).toLowerCase();const hit=[...new Set(Object.keys(KW).filter(w=>txt.indexOf(w)>=0).map(w=>KW[w]))].filter(has);if(hit.length===1)rooms=hit}
    const nm=String(a.friendly_name||id).replace(/\s+/g," ").trim().replace(/\s+(motion|occupancy|presence|sensor|detector|alarm|smoke|co|carbon monoxide|leak|water leak|opening|contact)$/i,"")||id,an=area&&areas[area]&&areas[area].name;
    const where=o.length?nm:(rooms.length?(an&&rooms.length===1&&rooms[0]==="room_"+area?an:this._rtSecRoomName(rooms[0])):nm);
    items.push({id,k,since:lc,until,o,rooms,where})}
  const agg=cfg.security_aggregates||{};const out=items.filter(it=>{const pre=agg[it.id];return !pre||!items.some(o=>o!==it&&o.id.indexOf(pre)===0)});
  const rank={alarm:0,smoke:0,co:0,gas:0,heat:0,leak:1,co2:2,open:3,motion:4};out.sort((x,y)=>(rank[x.k]-rank[y.k])||(y.since-x.since));
  S.items=out}
_rtSecRoomName(n){const m={room_bath_l1:"Bath, ground",room_bath_l3:"Bath, third",room_hall_l2:"Hall",room_closet_l3:"Closet"};if(m[n])return m[n];const s=String(n||"").replace(/^room_/,"").replace(/_l\d$/,"").replace(/_/g," ");return s.charAt(0).toUpperCase()+s.slice(1)}
_rtSecGeo(S,name){
  if(name in S.geo)return S.geo[name];let g=null;
  try{const o=this._scene.getObjectByName(name);
  if(o&&o.isMesh&&o.geometry&&o.geometry.attributes&&o.geometry.attributes.position){
    o.updateWorldMatrix(true,false);const e=o.matrixWorld.elements,p=o.geometry.attributes.position;const pts=[],mi=[],map={};
    for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i);const w=[e[0]*x+e[4]*y+e[8]*z+e[12],e[1]*x+e[5]*y+e[9]*z+e[13],e[2]*x+e[6]*y+e[10]*z+e[14]];const k=Math.round(w[0])+","+Math.round(w[1])+","+Math.round(w[2]);if(map[k]===undefined){map[k]=pts.length;pts.push(w)}mi[i]=map[k]}
    let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9,z0=1e9,z1=-1e9;for(const q of pts){x0=Math.min(x0,q[0]);x1=Math.max(x1,q[0]);y0=Math.min(y0,q[1]);y1=Math.max(y1,q[1]);z0=Math.min(z0,q[2]);z1=Math.max(z1,q[2])}
    const ix=o.geometry.index?o.geometry.index.array:null,nI=ix?ix.length:p.count,ec={};let A=0,cx=0,cz=0;
    for(let i=0;i+2<nI;i+=3){const a=mi[ix?ix[i]:i],b=mi[ix?ix[i+1]:i+1],c=mi[ix?ix[i+2]:i+2];if(a===b||b===c||a===c)continue;
      for(const [u,w] of [[a,b],[b,c],[c,a]]){const k=u<w?u+"_"+w:w+"_"+u;ec[k]=(ec[k]||0)+1}
      const ar=Math.abs((pts[b][0]-pts[a][0])*(pts[c][2]-pts[a][2])-(pts[c][0]-pts[a][0])*(pts[b][2]-pts[a][2]))/2;A+=ar;cx+=ar*(pts[a][0]+pts[b][0]+pts[c][0])/3;cz+=ar*(pts[a][2]+pts[b][2]+pts[c][2])/3}
    const adj={};for(const k in ec){if(ec[k]!==1)continue;const [u,w]=k.split("_").map(Number);(adj[u]=adj[u]||[]).push(w);(adj[w]=adj[w]||[]).push(u)}
    const keys=Object.keys(adj).map(Number);let loop=[];
    if(keys.length){let prev=-1,cur=keys[0];for(let n=0;n<=keys.length;n++){loop.push(cur);const nx=(adj[cur]||[]).find(v=>v!==prev);if(nx===undefined||nx===keys[0])break;prev=cur;cur=nx}}
    const ym=(y0+y1)/2;
    if(loop.length<3||loop.length!==keys.length){const b=pts.length;pts.push([x0,ym,z0],[x1,ym,z0],[x1,ym,z1],[x0,ym,z1]);loop=[b,b+1,b+2,b+3]}
    g={pts,loop,y:ym,minx:x0,maxx:x1,miny:y0,maxy:y1,minz:z0,maxz:z1,ccx:A?cx/A:(x0+x1)/2,ccz:A?cz/A:(z0+z1)/2,level:(o.userData&&o.userData.level)||0}}
  }catch(e){g=null}
  S.geo[name]=g;return g}
_rtSecFrame(S,ts){
  const cv=S.cv,ctx=S.ctx,box=this._content,cw=box.clientWidth,ch=box.clientHeight;if(!cw||!ch)return;
  const dpr=Math.min(window.devicePixelRatio||1,1.5);if(cv.width!==Math.round(cw*dpr)||cv.height!==Math.round(ch*dpr)){cv.width=Math.round(cw*dpr);cv.height=Math.round(ch*dpr)}
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,cw,ch);
  const now=Date.now();S.items=S.items.filter(i=>i.until>now);const items=S.items;if(!items.length)return;
  const cfg=this._config||{},cam=this._camera,rd=this._renderer.domElement,rb=rd.getBoundingClientRect(),bb=box.getBoundingClientRect();
  const rw=rd.clientWidth||cw,rh=rd.clientHeight||ch,ox=rb.left-bb.left,oy=rb.top-bb.top;
  const V=new cam.position.constructor();const P=(x,y,z)=>{V.set(x,y,z).project(cam);return[ox+(V.x+1)/2*rw,oy+(1-V.y)/2*rh]};
  const t=ts/1000,H=Number(cfg.security_height)||240,OH=Number(cfg.security_open_height)||200,dl=this._displaylevels||[],shown=l=>dl[l]!==false;
  const fadeS=cfg.security_motion_fade!==undefined?Number(cfg.security_motion_fade):20;
  const COL={smoke:"232,17,35",co:"232,17,35",gas:"232,17,35",heat:"232,17,35",alarm:"232,17,35",open:"232,17,35",leak:"0,180,255",co2:"255,122,0",motion:"255,176,0"};
  const LBL={smoke:"Smoke",co:"CO",gas:"Gas",heat:"Heat",alarm:"Alarm",open:"Open",leak:"Leak",co2:"CO₂",motion:"Motion"};
  const ALARM={smoke:1,co:1,gas:1,heat:1,alarm:1};
  const font=S.font||(S.font=(getComputedStyle(this).getPropertyValue("--ha-font-family-body")||"").trim()||"Roboto, Noto, sans-serif");
  const poly=a=>{ctx.beginPath();a.forEach((q,i)=>i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]));ctx.closePath()};
  const rgba=(c,a)=>"rgba("+c+","+Math.max(0,Math.min(1,a)).toFixed(3)+")";
  const pulse=0.5+0.5*Math.sin(t*Math.PI*2*1.2);let edge=0;const tags=[];
  for(const it of items){const c=COL[it.k],isA=!!ALARM[it.k];
    for(const n of (it.k==="open"&&it.o.length?[]:it.rooms)){const g=this._rtSecGeo(S,n);if(!g||(!isA&&!shown(g.level)))continue;
      const F=g.loop.map(i=>P(g.pts[i][0],g.y,g.pts[i][2]));
      if(it.k==="open"){const a=0.55+0.45*(0.5+0.5*Math.sin(t*Math.PI*2*0.8));poly(F);ctx.fillStyle=rgba(c,0.10*a);ctx.fill();ctx.save();ctx.setLineDash([6,4]);ctx.shadowColor=rgba(c,0.9);ctx.shadowBlur=8;ctx.strokeStyle=rgba(c,0.6+0.4*a);ctx.lineWidth=1.6;ctx.stroke();ctx.restore();const tp=P(g.ccx,g.y,g.ccz);tags.push([tp[0],tp[1],LBL[it.k],c]);continue}
      if(it.k==="motion"){
        const fk=it.until===Infinity?1:Math.max(0,(it.until-now)/(Math.max(1,fadeS)*1000));
        poly(F);ctx.fillStyle=rgba(c,0.30*fk);ctx.fill();ctx.strokeStyle=rgba(c,0.85*fk);ctx.lineWidth=1.4;ctx.stroke();
        if(it.until===Infinity){ctx.save();poly(F);ctx.clip();const R=Math.max(g.maxx-g.minx,g.maxz-g.minz)*0.6;
          for(let r=0;r<2;r++){const ph=(t*0.7+r*0.5)%1,rr=R*ph,pts=[];for(let q=0;q<36;q++){const an=q/36*6.2832;pts.push(P(g.ccx+Math.cos(an)*rr,g.y,g.ccz+Math.sin(an)*rr))}poly(pts);ctx.strokeStyle=rgba(c,0.9*(1-ph));ctx.lineWidth=2;ctx.stroke()}
          ctx.restore()}
      }else{
        const h=it.k==="leak"?40:H,C=g.loop.map(i=>P(g.pts[i][0],g.y+h,g.pts[i][2])),a=isA?0.35+0.65*pulse:0.75+0.25*pulse;
        ctx.fillStyle=rgba(c,0.10*a);for(let i=0;i<F.length;i++){const j=(i+1)%F.length;poly([F[i],F[j],C[j],C[i]]);ctx.fill()}
        poly(F);ctx.fillStyle=rgba(c,0.30*a);ctx.fill();poly(C);ctx.fillStyle=rgba(c,0.12*a);ctx.fill();
        ctx.save();ctx.shadowColor=rgba(c,0.9);ctx.shadowBlur=12;ctx.strokeStyle=rgba(c,0.55+0.45*a);ctx.lineWidth=1.6;ctx.beginPath();
        for(let i=0;i<F.length;i++){const j=(i+1)%F.length;ctx.moveTo(F[i][0],F[i][1]);ctx.lineTo(F[j][0],F[j][1]);ctx.moveTo(C[i][0],C[i][1]);ctx.lineTo(C[j][0],C[j][1]);ctx.moveTo(F[i][0],F[i][1]);ctx.lineTo(C[i][0],C[i][1])}
        ctx.stroke();ctx.restore();ctx.strokeStyle=rgba(it.k==="leak"?"190,235,255":"255,190,196",0.35+0.5*a);ctx.lineWidth=0.8;ctx.stroke();
        const tp=P(g.ccx,g.y+h,g.ccz);tags.push([tp[0],tp[1],LBL[it.k],c])}}
    for(const n of it.o){const g=this._rtSecGeo(S,n);if(!g||(!isA&&!shown(g.level)))continue;
      const y1=Math.max(g.maxy,g.miny+OH),pts=[];for(const x of [g.minx,g.maxx])for(const y of [g.miny,y1])for(const z of [g.minz,g.maxz])pts.push(P(x,y,z));
      const hull=this._rtSecHull(pts),a=0.55+0.45*(0.5+0.5*Math.sin(t*Math.PI*2*0.8));
      poly(hull);ctx.fillStyle=rgba(c,0.28*a);ctx.fill();ctx.save();ctx.shadowColor=rgba(c,0.9);ctx.shadowBlur=10;ctx.strokeStyle=rgba(c,0.6+0.4*a);ctx.lineWidth=1.6;ctx.stroke();ctx.restore();ctx.strokeStyle=rgba("255,190,196",0.35+0.5*a);ctx.lineWidth=0.8;ctx.stroke();
      const tp=P((g.minx+g.maxx)/2,y1,(g.minz+g.maxz)/2);tags.push([tp[0],tp[1],LBL[it.k],c])}
    if(isA)edge=Math.max(edge,it.rooms.length||it.o.length?0.55:1)}
  if(edge>0){const gr=ctx.createRadialGradient(cw/2,ch/2,Math.min(cw,ch)*0.3,cw/2,ch/2,Math.hypot(cw,ch)*0.6);gr.addColorStop(0,"rgba(232,17,35,0)");gr.addColorStop(1,rgba("232,17,35",0.42*edge*(0.35+0.65*pulse)));ctx.fillStyle=gr;ctx.fillRect(0,0,cw,ch)}
  try{ctx.letterSpacing="0.5px"}catch(e){}
  ctx.font="600 11px "+font;ctx.textAlign="center";ctx.textBaseline="middle";
  for(const [x,y,txt,c] of tags){const s=txt.toUpperCase(),w=Math.ceil(ctx.measureText(s).width)+14,h=18,bx=x-w/2,by=y-h-8;
    ctx.beginPath();ctx.moveTo(x,by+h);ctx.lineTo(x,y);ctx.strokeStyle=rgba(c,0.95);ctx.lineWidth=1;ctx.stroke();
    this._rtSecRound(ctx,bx,by,w,h,3);ctx.fillStyle=rgba(c,0.95);ctx.fill();ctx.fillStyle="#ffffff";ctx.fillText(s,x,by+h/2+0.5)}
  if(cfg.security_list==="no")return;
  const max=cw<480?3:6;ctx.textAlign="left";ctx.font="500 11px "+font;let y=12;
  for(const it of items.slice(0,max)){const c=COL[it.k],isA=!!ALARM[it.k],s=(LBL[it.k]+"  ·  "+it.where).toUpperCase(),tw=Math.min(Math.ceil(ctx.measureText(s).width),Math.max(60,cw*0.6)),w=tw+36,h=28,bx=cw-12-w;
    ctx.fillStyle="rgba(28,28,28,0.92)";ctx.fillRect(bx,y,w,h);ctx.strokeStyle=isA?rgba(c,0.55+0.45*pulse):"#232327";ctx.lineWidth=1;ctx.strokeRect(bx+0.5,y+0.5,w-1,h-1);
    ctx.beginPath();ctx.arc(bx+14,y+h/2,4,0,6.2832);ctx.fillStyle=rgba(c,isA?0.45+0.55*pulse:1);ctx.fill();
    ctx.save();ctx.beginPath();ctx.rect(bx+24,y,tw+6,h);ctx.clip();ctx.fillStyle="#d6d6d6";ctx.fillText(s,bx+25,y+h/2+0.5);ctx.restore();y+=h+6}
  if(items.length>max){ctx.textAlign="right";ctx.fillStyle="#9b9b9b";ctx.fillText("+"+(items.length-max)+" MORE",cw-14,y+8)}}
_rtSecRound(ctx,x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}
_rtSecHull(p){p=p.slice().sort((a,b)=>a[0]-b[0]||a[1]-b[1]);const cr=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]),lo=[],up=[];
  for(const q of p){while(lo.length>1&&cr(lo[lo.length-2],lo[lo.length-1],q)<=0)lo.pop();lo.push(q)}
  for(let i=p.length-1;i>=0;i--){const q=p[i];while(up.length>1&&cr(up[up.length-2],up[up.length-1],q)<=0)up.pop();up.push(q)}
  up.pop();lo.pop();return lo.concat(up)}
`;
function secPatch(src) {
  const n0 = src.length;
  const methods = SEC_METHODS.replace(/\n\s*/g, '');
  if (src.includes('_rtSecEnsure(){')) {  // already patched: swap in the current methods only
    const a = src.indexOf('_rtSecEnsure(){'), b = src.indexOf('_rtFloorFilter(){');
    if (b < a) throw new Error('patched security block not found');
    src = src.slice(0, a) + methods + src.slice(b);
    return { src, grew: src.length - n0, upgraded: true };
  }
  if (src.split('_rtFloorFilter(){').length !== 2) throw new Error('fx_patch block not found: apply fx_patch.js first');
  src = src.replace('_rtFloorFilter(){', () => methods + '_rtFloorFilter(){');
  if (src.split('_zIndexChecker(){').length !== 2) throw new Error('_zIndexChecker not found');
  src = src.replace('_zIndexChecker(){', '_zIndexChecker(){this._rtSecEnsure&&this._rtSecEnsure();');
  return { src, grew: src.length - n0 };
}
if (typeof module !== 'undefined') module.exports = secPatch;
