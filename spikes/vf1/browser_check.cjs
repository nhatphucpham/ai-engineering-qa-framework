// Fresh headless Chrome only; never attaches to a personal browser profile.
const { chromium } = require('C:/Users/Aki Chan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');

(async () => {
  const [preview, output, fragment] = process.argv.slice(2);
  const fragmentText=fs.readFileSync(fragment,'utf8');
  const expectedScripts=[...fragmentText.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(match=>match[1]);
  const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  fs.mkdirSync(output, { recursive:false });
  const browser = await chromium.launch({ executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:true });
  const checks=[];
  try {
    for (const width of [1024,320]) {
      const context=await browser.newContext({ viewport:{width,height:1000},hasTouch:width===320 });
      const page=await context.newPage();
      const errors=[], blocked=[];
      page.on('pageerror',error=>errors.push(error.message));
      await page.route(/^https?:/, route=>{blocked.push(route.request().url());return route.abort();});
      await page.goto(pathToFileURL(preview).href);
      await page.frameLocator('iframe').locator('#vf1-report').waitFor();
      const frame=page.frames().find(item=>item!==page.mainFrame());
      const root=frame.locator('#vf1-report');
      await root.locator('.detail h2').waitFor();
      assert.deepEqual(await root.locator('script').allTextContents(),expectedScripts);
      for(const run of [0,1]) {
        await root.locator(`[data-run="${run}"]`).click();
        await root.locator(`[data-run="${run}"][aria-pressed="true"]`).waitFor();
        assert.equal(await frame.evaluate(()=>document.activeElement.dataset.run),String(run));
        for(const cid of ['AC-01','AC-02','AC-03','AC-04']) {
          await root.locator(`[data-criterion="${cid}"]`).click();
          await root.locator('.detail h2').filter({hasText:cid}).waitFor();
          assert.equal(await frame.evaluate(()=>document.activeElement.dataset.criterion),cid);
          const expected=cid==='AC-01'?'Đã kiểm chứng':cid==='AC-04'?(run===0?'Đã kiểm chứng':'Chưa kiểm chứng'):'Vi phạm';
          assert((await root.locator('.detail h2').textContent()).includes(expected));
          if(run===1&&(cid==='AC-03'||cid==='AC-04'))assert((await root.locator('.detail').textContent()).includes('Còn gap coverage bắt buộc'));
          const geometry=await root.evaluate(element=>({width:element.getBoundingClientRect().width,scroll:element.scrollWidth,client:element.clientWidth}));
          assert(geometry.scroll<=geometry.client+1,JSON.stringify(geometry));
          checks.push({width,run,cid,expected,geometry});
        }
        await root.locator('.detail details summary').first().click();
        assert(await root.locator('.detail pre').first().isVisible());
        await root.locator('.meta summary').click();
        const text=await root.locator('.provenance').textContent();
        assert(text.includes(run===0?'vf1-a-':'vf1-b-'));
        assert(!text.includes(run===0?'vf1-b-':'vf1-a-'));
        await root.locator('.meta summary').click();
        if(width===1024) {
          const h=await root.evaluate(element=>Math.ceil(element.getBoundingClientRect().height));
          await page.setViewportSize({width,height:Math.max(1000,h+80)});
          await page.locator('iframe').evaluate((element,height)=>element.style.height=height+'px',h+48);
          await page.screenshot({path:path.join(output,`desktop-${run===0?'a':'b'}.png`),fullPage:true});
        }
      }
      // Native keyboard activation, not a JS click, changes the run.
      await root.locator('[data-run="0"]').focus();
      await page.keyboard.press('Enter');
      await root.locator('[data-run="0"][aria-pressed="true"]').waitFor();
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.run),'0');
      await page.keyboard.press('Tab');
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.run),'1');
      await page.keyboard.press('Enter');
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.run),'1');
      await page.keyboard.press('Tab');
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.criterion),'AC-01');
      await page.keyboard.press('Enter');
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.criterion),'AC-01');
      for(let index=0;index<3;index++)await page.keyboard.press('Tab');
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.criterion),'AC-04');
      await page.keyboard.press('Enter');
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.criterion),'AC-04');
      await page.keyboard.press('Tab');
      assert.equal(await frame.evaluate(()=>document.activeElement.tagName),'SUMMARY');
      await page.keyboard.press('Space');
      assert(await root.locator('.detail pre').first().isVisible());
      if(width===320) {
        await page.setViewportSize({width,height:5000});
        const h=await root.evaluate(element=>Math.ceil(element.getBoundingClientRect().height));
        await page.locator('iframe').evaluate((element,height)=>element.style.height=height+'px',h+48);
        await page.screenshot({path:path.join(output,'mobile.png'),clip:{x:0,y:0,width,height:h+64}});
      }
      assert.deepEqual(errors,[]);
      assert(blocked.every(url=>url.startsWith('https://unpkg.com/@floating-ui/')||url.startsWith('https://unpkg.com/lucide@')),JSON.stringify(blocked));
      checks.push({width,pageErrors:errors,blockedPreviewAssets:blocked,appNetworkRequests:0,keyboardRunCriterionSourceJourney:true,focusRetained:true,openCoverageVisible:true});
      await context.close();
    }
    fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({status:'PASS',fragmentSha256:hash(fragment),previewSha256:hash(preview),checkerSha256:hash(__filename),checks},null,2),{flag:'wx'});
    process.stdout.write(JSON.stringify({status:'PASS',checks:checks.length}));
  } finally {await browser.close();}
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
