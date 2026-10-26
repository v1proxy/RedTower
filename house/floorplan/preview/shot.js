const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [,, cfgFile, stFile, out, hideCsv] = process.argv;
  const b64 = s => Buffer.from(fs.readFileSync(s)).toString('base64');
  const browser = await chromium.launch({ args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 800 } });
  page.on('console', m => { const t = m.text(); if (/error|Error|level|loaded/i.test(t)) console.log('[page]', t.slice(0, 200)); });
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:8765/${process.env.PAGE||'index.html'}?cfg=${encodeURIComponent(b64(cfgFile))}&st=${encodeURIComponent(b64(stFile))}`);
  await page.waitForFunction(() => window.__card && window.__card._levels && window.__card._levels.length > 0, null, { timeout: 90000 });
  await page.waitForTimeout(2500);
  if (hideCsv) { for (const l of hideCsv.split(',').filter(Boolean)) { await page.evaluate(l => window.__toggle(Number(l)), l); } await page.waitForTimeout(1500); }
  await page.screenshot({ path: out });
  await browser.close();
})();
