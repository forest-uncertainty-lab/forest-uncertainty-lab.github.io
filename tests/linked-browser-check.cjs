/* Optional integration checks for linked place selection and the illustrative method states. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const puppeteer=require(process.env.PUPPETEER_MODULE||'puppeteer'),site=process.env.HAZE_SITE;
if(!site)throw Error('Set HAZE_SITE to the built directory');
(async()=>{
  const browser=await puppeteer.launch({executablePath:process.env.CHROME_BIN,headless:true,pipe:true,args:['--no-sandbox','--single-process','--no-zygote','--disable-gpu'],userDataDir:fs.mkdtempSync(path.join(os.tmpdir(),'linked-fire-'))});
  try {
    const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setRequestInterception(true);
    page.on('request',r=>{const u=new URL(r.url());if(u.hostname!=='haze.local')return r.abort();const file=path.join(site,u.pathname==='/'?'index.html':u.pathname.slice(1));const exists=fs.existsSync(file);r.respond({status:exists?200:404,contentType:({'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json'})[path.extname(file)]||'text/plain',body:exists?fs.readFileSync(file):'Missing'});});
    await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);
    await page.goto('http://haze.local/#tab=fires&theme=dark',{waitUntil:'load'});
    await page.waitForFunction(()=>document.querySelector('#fcChart svg'));
    assert.match(await page.$eval('#fcCaption',e=>e.textContent),/Central Sulawesi/);
    await page.click('#fc-region-papua');
    assert.equal(await page.$eval('#fcPlace',e=>e.value),'prov:Papua');assert.match(await page.$eval('#fh-detail',e=>e.textContent),/Papua/);
    await page.select('#fcPlace','prov:Papua Barat');
    assert.match(await page.$eval('#fcCaption',e=>e.textContent),/West Papua/);assert.equal(await page.$eval('#fRowSelect',e=>e.value),'prov:Papua Barat');
    await page.click('#fc-mode-raw');assert.match(await page.$eval('#fcUnit',e=>e.textContent),/Detections/);
    await page.select('#fYearSelect','2015');assert.match(await page.$eval('#fcCaption',e=>e.textContent),/2015/);assert.doesNotMatch(await page.$eval('#fcUncertainty',e=>e.textContent),/gives an 80%/);
    await page.click('#fMeasure-frp');assert.match(await page.$eval('#fcUnit',e=>e.textContent),/MW/);await page.click('#fMeasure-count');
    await page.click('#fm-jump-2');assert.equal(await page.$eval('#fmTotal',e=>e.textContent),'93.6');
    assert.match(await page.$eval('#fmIllustration',e=>e.textContent),/not observations/);assert.match(await page.evaluate(()=>location.hash),/explain=2/);
    await page.setViewport({width:390,height:844,deviceScaleFactor:1});
    await page.click('[data-lang="id"]');assert.equal(await page.$eval('#fmTotal',e=>e.textContent),'93,6');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await page.focus('#fm-jump-1');await page.keyboard.press('Enter');assert.equal(await page.$eval('#fmTotal',e=>e.textContent),'73,6');
    await page.screenshot({path:path.join(os.tmpdir(),'linked-fire-mobile.png'),fullPage:true});
    const hash=await page.evaluate(()=>location.hash);await page.reload({waitUntil:'load'});await page.waitForFunction(()=>document.querySelector('#fcChart svg'));
    assert.equal(await page.$eval('#fcPlace',e=>e.value),'prov:Papua Barat');assert.equal(await page.$eval('#fmTotal',e=>e.textContent),'73,6');
    assert.match(hash,/comparison=raw/);assert.equal(errors.length,0,errors.join('; '));
    await page.setViewport({width:1280,height:1000});
    await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'no-preference'}]);
    await page.click('#fc-mode-relative');
    await page.$eval('#fm-step-2',e=>e.scrollIntoView({block:'center'}));
    await page.waitForFunction(()=>document.querySelector('#fmTotal').textContent==='93,6');
    await page.click('#fm-jump-0');
    await page.waitForFunction(()=>document.querySelector('#fmTotal').textContent==='54');
    await page.screenshot({path:path.join(os.tmpdir(),'linked-fire-desktop.png'),fullPage:true});
    console.log('PASS Linked region, province, year, measure controls, illustration arithmetic, language, URL restore, keyboard and mobile layout');
  }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
