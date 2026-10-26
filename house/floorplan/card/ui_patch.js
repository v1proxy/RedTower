// Red Tower UI patch for floor3dpro-axo-card (applied after axo_patch.js; regex-based so it survives rebuilds of the card).
// - labels drawn at 4x resolution, semibold, rounded background; the box width follows the text so it is never squashed
// - label textures use anisotropic filtering, are not tone mapped (true white text), old textures are disposed on update
// - floor buttons 40 px, brighter, hidden floors clearly dimmed
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
  const bar = '<div class="category" style="opacity: 0.5; position: absolute">';
  if (src.split(bar).length !== 2) throw new Error('level bar not found');
  src = src.replace(bar, '<div class="category" style="opacity: 0.92; position: absolute; top: 6px; left: 6px; --mdc-icon-size: 40px; z-index: 2;">');
  const a = src.indexOf('_getLevelIcons(){'), b = src.indexOf('_getSelectionBar(){', a);
  if (a < 0 || b < 0) throw new Error('_getLevelIcons not found');
  let li = src.slice(a, b);
  li = li.split('<div class="row" style="background-color:black;">').join('<div class="row" style="background-color:black; padding: 2px 2px 4px 2px; cursor: pointer;">');
  li = li.split('"opacity: 60%;"').join('"opacity: 30%;"');
  src = src.slice(0, a) + li + src.slice(b);
  return { src, grew: src.length - n0 };
}
if (typeof module !== 'undefined') module.exports = uiPatch;
