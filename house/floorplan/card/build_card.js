// Builds the patched card from the HACS floor3dpro-card file: the axonometric patch, the UI patch, then the FX patch.
//   node build_card.js path/to/floor3dpro-card.js [floor3dpro-axo-card.js]
// Put the output in /config/www/floor3d/ and load it as /local/floor3d/floor3dpro-axo-card.js?v=<n>.
const fs = require('fs');
const axoPatch = require('./axo_patch.js');
const uiPatch = require('./ui_patch.js');
const fxPatch = require('./fx_patch.js');
const [, , input, output = 'floor3dpro-axo-card.js'] = process.argv;
if (!input) { console.error('usage: node build_card.js floor3dpro-card.js [out.js]'); process.exit(2); }
const a = axoPatch(fs.readFileSync(input, 'utf8'));
const b = uiPatch(a.src);
const c = fxPatch(b.src);
fs.writeFileSync(output, c.src);
console.log(`${output}: ${c.src.length} chars, ${a.renamed} element names renamed, UI patch +${b.grew}, FX patch +${c.grew}`);
