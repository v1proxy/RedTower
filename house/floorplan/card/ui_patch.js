// Red Tower UI patch for floor3dpro-axo-card (applied after axo_patch.js; regex-based so it survives rebuilds of the card).
// - labels drawn at 4x resolution, semibold, rounded background; the box width follows the text so it is never squashed
// - label textures use anisotropic filtering, are not tone mapped (true white text), old textures are disposed on update
// - floor buttons as tiles in the dashboard's own style (levelsPatch below): square dark tiles, icon over an
//   uppercase caption, red border and icon while the floor is shown, on a transparent strip
function uiPatch(src) {
  const n0 = src.length;
  const reT = /_updateTextCanvas\(([\w$]+),([\w$]+),([\w$]+)\)\{const ([\w$]+)=\2\.getContext\("2d"\);[\s\S]*?\}(?=_applyTextCanvas\()/;
  const m = src.match(reT);
  if (!m) throw new Error('_updateTextCanvas not found');
  const [, t, e, i, n] = m;
  const body = `_updateTextCanvas(${t},${e},${i}){const ${n}=${e}.getContext("2d"),q=4,fs=48*q,pad=20*q,fnt=(${t}.font_weight||"600")+" "+fs+"px "+(${t}.font?${t}.font:"sans-serif");${n}.font=fnt;const w=Math.ceil(${n}.measureText(${i}).width)+2*pad,h=Math.round(fs*1.55),rr=h*0.3;${e}.width=w;${e}.height=h;${n}.font=fnt;${n}.textAlign="center";${n}.textBaseline="middle";${n}.clearRect(0,0,w,h);${n}.fillStyle=${t}.textbgcolor?${t}.textbgcolor:"transparent";${n}.beginPath();${n}.moveTo(rr,0);${n}.arcTo(w,0,w,h,rr);${n}.arcTo(w,h,0,h,rr);${n}.arcTo(0,h,0,0,rr);${n}.arcTo(0,0,w,0,rr);${n}.closePath();${n}.fill();${n}.fillStyle=${t}.textfgcolor?${t}.textfgcolor:"white";${n}.fillText(${i},w/2,h/2+fs*0.05)}`;
  src = src.replace(reT, () => body);
  const reS = /(_applyTextCanvasSprite\(([\w$]+),([\w$]+)\)\{const ([\w$]+)=new [\w$]+\(\2\);)/;
  const s = src.match(reS);
  if (!s) throw new Error('_applyTextCanvasSprite not found');
  src = src.replace(reS, () => `${s[1]}${s[4]}.anisotropy=8;${s[3]}.scale.x=${s[3]}.scale.y*${s[2]}.width/${s[2]}.height;${s[3]}.material&&${s[3]}.material.map&&${s[3]}.material.map.dispose&&${s[3]}.material.map.dispose();`);
  const fa = src.search(/_applyTextCanvasSprite\([\w$]+,[\w$]+\)\{/), fb = src.indexOf('}}', fa) + 2;
  const fn = src.slice(fa, fb), fn2 = fn.replace(/new ([\w$]+)\(\{map:([\w$]+),transparent:!0\}\)/, (x, c, mp) => `new ${c}({map:${mp},transparent:!0,toneMapped:!1})`);
  if (fn2 === fn) throw new Error('sprite material not found');
  src = src.slice(0, fa) + fn2 + src.slice(fb);
  src = levelsPatch(src).src;
  return { src, grew: src.length - n0 };
}

// Floor buttons as dashboard tiles. Runs on a fresh HACS card (from uiPatch) or on an already patched card.
// Options: level_names (array by level), level_icons (mdi icons by level), level_all_name, level_all_icon.
const RT_LEVEL_ICONS = ({
_getLevelIcons(){const H=__RT_HTML__;const c=this._config||{},names=c.level_names||[],icons=c.level_icons||[];const ch=this._content&&this._content.clientHeight||600,cw=this._content&&this._content.clientWidth||1000,compact=ch<380||cw<480;const lv=this._levels||[],dl=this._displaylevels||[];const all=lv.every((e,i)=>!e||dl[i]);const tile=(idx,label,icon,on)=>H`<div class=${"rt-floor"+(on?" on":"")+(compact?" compact":"")} title=${label} @click=${ev=>{ev.stopPropagation();this._handleLevelClick({stopPropagation(){},target:{index:idx}})}}><ha-icon .icon=${icon}></ha-icon>${compact?"":H`<span>${label}</span>`}</div>`;const t=[];lv.forEach((e,i)=>{e&&t.push(tile(i,names[i]||"Level "+i,icons[i]||"mdi:numeric-"+i+"-box-outline",!!dl[i]))});return[H`<style>.rt-floor{pointer-events:auto;box-sizing:border-box;width:84px;min-height:52px;padding:8px 10px 7px;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;gap:4px;background-color:rgba(28,28,28,0.92);border:1px solid #232327;border-radius:var(--ha-card-border-radius,0px);cursor:pointer;user-select:none;-webkit-user-select:none;-webkit-tap-highlight-color:transparent;transition:border-color 160ms ease,background-color 160ms ease}.rt-floor ha-icon{--mdc-icon-size:22px;width:22px;height:22px;display:flex;color:#5e5e63;transition:color 160ms ease}.rt-floor span{font-family:var(--ha-font-family-body,Roboto,Noto,sans-serif);font-size:11px;font-weight:500;letter-spacing:0.5px;text-transform:uppercase;line-height:1.2;color:#6e6e73;white-space:nowrap}.rt-floor.on{border-color:#E81123}.rt-floor.on ha-icon{color:#E81123}.rt-floor.on span{color:var(--secondary-text-color,#9b9b9b)}.rt-floor:hover{background-color:rgba(40,40,42,0.96)}.rt-floor.compact{width:44px;min-height:44px;padding:0;align-items:center}</style>`,...t.reverse(),tile(-1,c.level_all_name||"All",c.level_all_icon||"mdi:layers-triple-outline",all)]}
})._getLevelIcons.toString();
function levelsPatch(src) {
  const n0 = src.length;
  const reBar = /<div class="(?:category|rt-floors)" style="[^"]*position: absolute[^"]*">\$\{this\._getLevelIcons\(\)\}<\/div>/;
  if (!reBar.test(src)) throw new Error('level bar not found');
  src = src.replace(reBar, () => '<div class="rt-floors" style="position: absolute; top: 12px; left: 12px; z-index: 2; display: flex; flex-direction: column; gap: 6px; pointer-events: none;">${this._getLevelIcons()}</div>');
  const a = src.indexOf('_getLevelIcons(){'), b = src.indexOf('_getSelectionBar(){', a);
  if (a < 0 || b < 0) throw new Error('_getLevelIcons not found');
  const old = src.slice(a, b);
  const m = old.match(/^_getLevelIcons\(\)\{(?:const [\w$]+=\[\];return [\w$]+\.push\(([\w$]+)`|const H=([\w$]+);)/);
  if (!m) throw new Error('html tag not found in _getLevelIcons');
  const tag = m[1] || m[2];
  src = src.slice(0, a) + RT_LEVEL_ICONS.replace('__RT_HTML__', tag) + src.slice(b);
  return { src, grew: src.length - n0 };
}
if (typeof module !== 'undefined') { module.exports = uiPatch; module.exports.levelsPatch = levelsPatch; }
