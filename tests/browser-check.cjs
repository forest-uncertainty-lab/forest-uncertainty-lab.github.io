/* Optional browser regression checks. Supply an installed Puppeteer module and Chrome binary. */
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const puppeteer = require(process.env.PUPPETEER_MODULE || 'puppeteer');
const site = process.env.HAZE_SITE;
if (!site) throw Error('Set HAZE_SITE to the built site directory');
(async () => {
  const browser = await puppeteer.launch({executablePath: process.env.CHROME_BIN, headless: true, pipe: true,
    args: ['--no-sandbox', '--single-process', '--no-zygote', '--disable-gpu'],
    userDataDir: fs.mkdtempSync(path.join(os.tmpdir(), 'haze-browser-'))});
  const failures = [];
  try {
    for (const variant of ['empty-nea', 'partial-cams', 'missing-wind']) {
      const page = await browser.newPage(), errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const data = JSON.parse(fs.readFileSync(path.join(site, 'data/haze.json'), 'utf8'));
      if (variant === 'empty-nea') data.nea.pm25_hourly = [];
      if (variant === 'partial-cams') {
        const s = data.cams.palu;
        const hour = Math.floor(Date.now() / 3600000) * 3600000;
        const value = s.pm2_5.find(v => v != null) ?? 10;
        s.time = Array.from({length: 24}, (_, i) => new Date(hour - i * 3600000).toISOString().slice(0, 16));
        s.pm2_5 = s.time.map((_, i) => i === 0 ? value : null);
      }
      if (variant === 'missing-wind') {
        for (const city of data.cities) for (const level of ['925', '850', '700']) {
          data.trajectories[city.key][level] = Array.from({length: 9}, () => [[city.lon, city.lat, 0]]);
          data.upwind[city.key][level] = {share: null, median: null, max: null, members: 0};
        }
      }
      await page.setRequestInterception(true);
      page.on('request', request => {
        const url = new URL(request.url());
        if (url.hostname !== 'haze.local') return request.abort();
        const file = path.join(site, url.pathname === '/' ? 'index.html' : url.pathname.slice(1));
        const body = url.pathname === '/data/haze.json' ? JSON.stringify(data) : fs.existsSync(file) ? fs.readFileSync(file) : '';
        request.respond({status: body.length ? 200 : 404, contentType: ({'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json'})[path.extname(file)] || 'text/plain', body});
      });
      try {
        await page.goto('http://haze.local/#tab=haze&city=' + (variant === 'partial-cams' ? 'palu' : 'singapore'), {waitUntil: 'load'});
        await page.waitForFunction(() => document.querySelector('#hzTitle').textContent.length > 0);
        await new Promise(resolve => setTimeout(resolve, 100));
        assert.equal(errors.length, 0, errors.join('; '));
        assert.ok(await page.$eval('#hzMap', e => e.children.length > 0), 'The map still renders');
        if (variant === 'empty-nea') assert.match(await page.$eval('#hzSide', e => e.innerText), /hourly.*unavailable/i);
        if (variant === 'partial-cams') {
          const hero = await page.$eval('#hzHero', e => e.innerText);
          assert.match(hero, /1 of 24/);
          assert.doesNotMatch(hero, /times the WHO|24-hour guideline/);
        }
        if (variant === 'missing-wind') {
          const paths = await page.$eval('#hzPaths', e => e.innerText);
          assert.match(paths, /unavailable/i);
          assert.doesNotMatch(paths, /48 hours ago|None of the nine/);
        }
        console.log('PASS ' + variant);
      } catch (error) { failures.push(variant + ' · ' + error.message); }
      await page.close();
    }
  } finally { await browser.close(); }
  assert.deepEqual(failures, []);
})().catch(error => { console.error(error.message); process.exitCode = 1; });
