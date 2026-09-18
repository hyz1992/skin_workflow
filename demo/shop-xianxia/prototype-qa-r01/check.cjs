const {chromium}=require(process.env.UI_SKIN_PLAYWRIGHT_PATH || 'playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const root=path.resolve(__dirname,'../prototype-r01'),url=pathToFileURL(path.join(root,'prototype.html')).href;
(async()=>{
 const options={headless:true};
 if(process.env.UI_SKIN_CHROME_PATH) options.executablePath=process.env.UI_SKIN_CHROME_PATH;
 const browser=await chromium.launch(options);
 try{
  const page=await browser.newPage({viewport:{width:1600,height:950}}),errors=[],network=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
  await page.goto(url);await page.locator('img').evaluateAll(xs=>Promise.all(xs.map(x=>x.decode())));
  assert.equal(await page.locator('.card').count(),5);assert.equal(await page.locator('.purchase').allTextContents().then(xs=>xs.map(x=>x.trim()).join(',')),'¥1,¥3,¥6,¥18,¥30');
  await page.screenshot({path:path.join(__dirname,'default.png')});checks.push('Five source-defined diamond packs; all assets loaded offline');
  await page.locator('.purchase').first().click();assert(await page.locator('#dialog').evaluate(n=>n.open));assert((await page.locator('#dialog-body').textContent()).includes('¥1'));
  await page.locator('#dialog-cancel').click();assert(!(await page.locator('#dialog').evaluate(n=>n.open)));
  await page.locator('.purchase').first().click();await page.screenshot({path:path.join(__dirname,'purchase.png')});await page.locator('#dialog-confirm').click();assert(!(await page.locator('#toast').evaluate(n=>n.hidden)));checks.push('Purchase dialog: cancel and simulated confirmation');
  await page.locator('#service').click();assert.equal(await page.locator('#dialog-title').textContent(),'联系客服');await page.keyboard.press('Escape');assert(await page.locator('#service').evaluate(n=>n===document.activeElement));
  await page.locator('#privilege').click();assert.equal(await page.locator('#dialog-title').textContent(),'贵族特权');await page.locator('#dialog-confirm').click();checks.push('Service, privileges, Escape, focus restoration');
  await page.locator('#tab-coin').click();assert(!(await page.locator('#empty').evaluate(n=>n.hidden)));assert.equal(await page.locator('#empty-title').textContent(),'暂无金币商品');
  await page.keyboard.press('ArrowRight');assert.equal(await page.locator('#tab-energy').getAttribute('aria-selected'),'true');await page.keyboard.press('Home');assert.equal(await page.locator('#tab-diamond').getAttribute('aria-selected'),'true');checks.push('Tabs, arrow/Home navigation, unknown categories show empty state');
  await page.locator('#close-shop').click();assert(await page.locator('#shop').evaluate(n=>n.hidden));await page.locator('#reopen').click();assert(!(await page.locator('#shop').evaluate(n=>n.hidden)));checks.push('Close and reopen');
  const button=page.locator('#service');
  async function down(){const r=await button.boundingBox();await page.mouse.move(r.x+r.width/2,r.y+r.height/2);await page.mouse.down();assert(await button.evaluate(n=>n.classList.contains('pressed')));return r;}
  async function clear(){assert(!(await button.evaluate(n=>n.classList.contains('pressed'))));}
  const before=await button.boundingBox();await down();assert.deepEqual(await button.boundingBox(),before);await page.mouse.move(3,3);await clear();await page.mouse.up();
  await down();await page.dispatchEvent('#service','pointercancel');await clear();await page.mouse.move(3,3);await page.mouse.up();
  await down();await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await clear();await page.mouse.move(3,3);await page.mouse.up();
  await button.focus();await page.keyboard.down('Space');assert(await button.evaluate(n=>n.classList.contains('pressed')));await page.keyboard.up('Space');await clear();await page.keyboard.press('Escape');checks.push('Stable hit box; press, leave, cancel, blur and Space key restoration');
  await page.locator('#state').selectOption('disabled');assert.equal(await page.locator('.purchase:disabled').count(),5);assert(!(await page.locator('#dialog').evaluate(n=>n.open)));checks.push('Disabled purchase controls');
  await page.locator('#state').selectOption('empty');assert.equal(await page.locator('#products').evaluate(n=>n.hidden),true);checks.push('Empty diamond list');
  await page.locator('#reset').click();
  for(const ratio of ['16/9','21/9','4/3','9/16']){
   await page.locator('#ratio').selectOption(ratio);
   const g=await page.locator('#viewport').boundingBox();const [a,b]=ratio.split('/').map(Number);assert(Math.abs(g.width/g.height-a/b)<.015);
   const inside=await page.evaluate(()=>{const a=document.getElementById('shop').getBoundingClientRect(),b=document.getElementById('viewport').getBoundingClientRect();return a.left>=b.left&&a.right<=b.right+1&&a.top>=b.top&&a.bottom<=b.bottom+1;});assert(inside);
  }
  await page.screenshot({path:path.join(__dirname,'portrait.png')});
  await page.locator('#state').selectOption('long');await page.screenshot({path:path.join(__dirname,'portrait-long.png')});
  const overflow=await page.locator('#products').evaluate(n=>n.scrollWidth>n.clientWidth);assert(overflow);
  await page.locator('#products').hover();await page.mouse.wheel(0,3000);await page.waitForTimeout(250);assert(await page.locator('#products').evaluate(n=>n.scrollLeft>0));
  await page.locator('.purchase').last().click();assert((await page.locator('#dialog-body').textContent()).includes('30,000,000'));await page.keyboard.press('Escape');checks.push('Four ratios; compact layout; horizontal wheel scroll; last long-data pack reachable');
  await page.locator('#ratio').selectOption('4/3');await page.screenshot({path:path.join(__dirname,'tablet-long.png')});
  await page.locator('#reset').click();assert.equal(await page.locator('#ratio').inputValue(),'design');assert.equal(await page.locator('#state').inputValue(),'normal');assert.equal(await page.locator('#badge-level').textContent(),'0');assert.equal(await page.locator('#tab-diamond').getAttribute('aria-selected'),'true');checks.push('Reset restores view, data and selection');
  await page.setViewportSize({width:390,height:844});await page.reload();await page.locator('img').evaluateAll(xs=>Promise.all(xs.map(x=>x.decode())));assert.equal(await page.locator('#ratio').inputValue(),'auto');await page.screenshot({path:path.join(__dirname,'mobile.png')});assert(await page.locator('#shop').evaluate(n=>n.classList.contains('compact')));
  await page.locator('#state').selectOption('long');await page.screenshot({path:path.join(__dirname,'mobile-long.png')});
  const textFit=await page.evaluate(()=>{const n=document.getElementById('vip-upgrade'),p=document.querySelector('.vip');return n.getBoundingClientRect().bottom<=p.getBoundingClientRect().bottom;});assert(textFit);checks.push('390×844 initial auto layout and long VIP copy');
  assert.equal(errors.length,0);assert.equal(network.length,0);
  fs.writeFileSync(path.join(__dirname,'browser-check.json'),JSON.stringify({status:'passed',checks,pageErrors:errors,networkRequests:network},null,2));console.log(JSON.stringify({status:'passed',checks}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
