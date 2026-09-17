// Optional browser QA. Run make_demo.py first; requires a Playwright installation.
const {chromium} = require(process.env.UI_SKIN_PLAYWRIGHT_PATH || 'playwright');
const {pathToFileURL} = require('url');
const path = require('path');
const fs = require('fs');

(async () => {
  const options = {headless: true};
  if (process.env.UI_SKIN_CHROME_PATH) options.executablePath = process.env.UI_SKIN_CHROME_PATH;
  const browser = await chromium.launch(options);
  try {
    const page = await browser.newPage({viewport: {width: 1200, height: 900}});
    const errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => {if (/^https?:/.test(r.url())) requests.push(r.url());});
    const base = path.resolve(process.argv[2] || '.ui-skin-check');
    await page.goto(pathToFileURL(path.join(base, 'asset-preview.html')).href);
    await page.locator('.tile').first().click();
    await page.locator('#mode').selectOption('pixels');
    const dimensions = await page.locator('#large img').evaluate(n => ({w: n.getBoundingClientRect().width, h: n.getBoundingClientRect().height}));
    if (dimensions.w !== 240 || dimensions.h !== 80) throw Error('actual pixel mode mismatch');
    await page.locator('#close').click();
    for (const color of ['#ffffff', '#152025', '#808080', 'custom']) await page.locator('#bg').selectOption(color);
    await page.screenshot({path: path.join(base, 'asset-preview.png')});
    await page.goto(pathToFileURL(path.join(base, 'prototype.html')).href);
    await page.locator('#demo-action').click();
    if (!(await page.locator('#demo-result').textContent()).includes('计数 1')) throw Error('click action failed');
    await page.locator('#demo-toggle').focus(); await page.keyboard.press('Space');
    if (!(await page.locator('#demo-result').textContent()).includes('开启')) throw Error('keyboard failed');
    const button = page.locator('#demo-action');
    async function press() {
      const b = await button.boundingBox();
      await page.mouse.move(b.x+b.width/2, b.y+b.height/2); await page.mouse.down();
      if (!(await button.evaluate(n => n.classList.contains('pressed')))) throw Error('press missing');
    }
    async function restored() {
      if (await button.evaluate(n => n.classList.contains('pressed'))) throw Error('press restoration failed');
    }
    await press(); await page.mouse.move(2, 2); await restored(); await page.mouse.up();
    await press(); await page.dispatchEvent('#demo-action', 'pointercancel'); await restored(); await page.mouse.up();
    await press(); await page.evaluate(() => window.dispatchEvent(new Event('blur'))); await restored(); await page.mouse.up();
    for (const ratio of ['16/9', '21/9', '4/3', '9/16']) {
      await page.locator('#ratio').selectOption(ratio);
      const g = await page.evaluate(() => ({sceneW: parseFloat(document.querySelector('#scene').style.width), view: document.querySelector('#viewport').getBoundingClientRect().toJSON()}));
      const [a,b] = ratio.split('/').map(Number);
      if (Math.abs(g.sceneW-600*a/b) > .1 || Math.abs(g.view.width/g.view.height-a/b) > .01) throw Error('ratio mismatch '+ratio);
    }
    await page.locator('#state').selectOption('long');
    if (!(await page.locator('#demo-body').textContent()).includes('较长')) throw Error('state failed');
    await page.locator('#reset').click();
    if (await page.locator('#ratio').inputValue() !== 'design') throw Error('reset failed');
    await page.screenshot({path: path.join(base, 'prototype.png')});
    if (errors.length || requests.length) throw Error(JSON.stringify({errors, unexpectedNetworkRequests: requests}));
    const report = {status: 'passed', checks: ['file:// offline load', 'embedded PNG', 'pixel zoom', 'four backgrounds', 'click and keyboard', 'press/leave/cancel/blur restoration', 'four aspect ratios', 'state and reset'], pageErrors: errors, networkRequests: requests};
    fs.writeFileSync(path.join(base, 'browser-check.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
