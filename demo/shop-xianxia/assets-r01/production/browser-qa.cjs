const {chromium}=require(process.env.UI_SKIN_PLAYWRIGHT_PATH || 'playwright');
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
(async()=>{
 const base=path.resolve(__dirname,'..'),manifest=JSON.parse(fs.readFileSync(path.join(base,'assets.json'),'utf8'));
 const options={headless:true};
 if(process.env.UI_SKIN_CHROME_PATH) options.executablePath=process.env.UI_SKIN_CHROME_PATH;
 const browser=await chromium.launch(options);
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],network=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
  await page.goto(pathToFileURL(path.join(base,'asset-preview.html')).href);
  await page.locator('img').evaluateAll(imgs=>Promise.all(imgs.map(i=>i.decode())));
  if(await page.locator('.tile').count()!==19)throw Error('Missing asset');
  for(const [name,color] of [['checker','checker'],['white','#ffffff'],['dark','#152025'],['gray','#808080']]){
   await page.locator('#bg').selectOption(color);
   await page.screenshot({path:path.join(__dirname,'review-'+name+'.png'),fullPage:true});
  }
  let views=0;
  for(let i=0;i<manifest.assets.length;i++){
   await page.locator('.tile').nth(i).click();
   for(const [mode,expected] of [['pixels',manifest.assets[i].pixelSize],['design',manifest.assets[i].displaySize]]){
    await page.locator('#mode').selectOption(mode);
    const actual=await page.locator('#large img').evaluate(i=>[i.getBoundingClientRect().width,i.getBoundingClientRect().height]);
    if(actual.some((v,k)=>Math.abs(v-expected[k])>.1))throw Error('Size mismatch '+manifest.assets[i].key);
    views++;
   }
   await page.locator('#close').click();
  }
  await page.locator('#bg').selectOption('custom');await page.locator('#color').fill('#e5d9bb');
  if(errors.length||network.length)throw Error(JSON.stringify({errors,network}));
  fs.writeFileSync(path.join(base,'browser-check.json'),JSON.stringify({technicalStatus:'passed',assets:19,backgrounds:4,sizeViews:views,offline:true,pageErrors:errors,networkRequests:network,visualApproval:'not-inferred'},null,2));
  console.log(JSON.stringify({assets:19,backgrounds:4,sizeViews:views,errors,network}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
