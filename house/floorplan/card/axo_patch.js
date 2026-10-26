// Patches floor3dpro-card (levonisyas, MIT) for Red Tower.
// - swaps the 45deg PerspectiveCamera for an OrthographicCamera (card option `ortho_half_height`, cm)
// - level buttons stacked like the building: highest level on top, ground at the bottom, "all" last
// - renames every floor3dpro-* custom element to floor3dpro-axo-* so it runs beside the HACS card
// - model cache clones also copy mesh geometry; the original shares it, and the room-label code shifts room
//   geometry in place, so every rebuild after the first (switching dashboard tabs) collapsed labels into one corner
function axoPatch(src) {
  const m = src.match(/class ([\w$]+) extends [\w$]+\{constructor\(t=-1,e=1,i=1,n=-1,r=\.1,o=2e3\)\{super\(\),this\.type="OrthographicCamera"/);
  if (!m) throw new Error('OrthographicCamera class not found');
  const O = m[1];
  const re = /this\._camera=new ([\w$]+)\(45,1,\.1,1e4\)/;
  if (!re.test(src)) throw new Error('camera constructor not found');
  src = src.replace(re, 'this._camera=((h)=>{const c=new ' + O + '(-1,1,1,-1,-1e5,1e5);Object.defineProperty(c,"aspect",{configurable:!0,get(){return this.__a||1},set(v){this.__a=v;this.left=-h*v;this.right=h*v;this.top=h;this.bottom=-h}});c.aspect=1;c.updateProjectionMatrix();return c})(Number(this._config&&this._config.ortho_half_height)||900)');
  const lv = src.match(/_getLevelIcons\(\)\{const ([\w$]+)=\[\];return/);
  if (!lv) throw new Error('_getLevelIcons not found');
  const v = lv[1];
  const end = '}),' + v + '}_getSelectionBar(){';
  if (src.split(end).length !== 2) throw new Error('_getLevelIcons end not unique');
  src = src.replace(end, '}),[...' + v + '.slice(1).reverse(),' + v + '[0]]}_getSelectionBar(){');
  const cl = 'e.traverse(t=>{t.isMesh&&t.material&&(Array.isArray(t.material)';
  if (src.split(cl).length !== 2) throw new Error('asset cache clone not found');
  src = src.replace(cl, 'e.traverse(t=>{t.isMesh&&t.geometry&&(t.geometry=t.geometry.clone()),t.isMesh&&t.material&&(Array.isArray(t.material)');
  const n = src.split('floor3dpro-').length - 1;
  src = src.split('floor3dpro-').join('floor3dpro-axo-');
  return { src, O, renamed: n };
}
if (typeof module !== 'undefined') module.exports = axoPatch;
