// Expanded pre-push visual matrix; fresh headless contexts, no personal browser state.
const {chromium}=require('C:/Users/Aki Chan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');

(async()=>{
  const [preview,fragment,out]=process.argv.slice(2);
  fs.mkdirSync(out,{recursive:false});
  const expectedScripts=[...fs.readFileSync(fragment,'utf8').matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(match=>match[1]);
  const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const checks=[];
  try{
    for(const colorScheme of ['light','dark'])for(const width of [390,768,1280]){
      const context=await browser.newContext({viewport:{width,height:900},colorScheme,hasTouch:width===390});
      const page=await context.newPage();
      const errors=[],blocked=[];
      page.on('pageerror',error=>errors.push(error.message));
      await page.route(/^https?:/,route=>{blocked.push(route.request().url());return route.abort();});
      await page.goto(pathToFileURL(path.resolve(preview)).href);
      await page.frameLocator('iframe').locator('#vf1-report .detail h2').waitFor();
      const frame=page.frames().find(item=>item!==page.mainFrame());
      const root=frame.locator('#vf1-report');
      assert.deepEqual(await root.locator('script').allTextContents(),expectedScripts);
      for(const run of [0,1]){
        await page.setViewportSize({width,height:900});
        await root.locator(`[data-run="${run}"]`).click();
        assert.equal(await frame.evaluate(()=>document.activeElement.dataset.run),String(run));
        for(const cid of ['AC-01','AC-02','AC-03','AC-04']){
          await root.locator(`[data-criterion="${cid}"]`).click();
          assert.equal(await frame.evaluate(()=>document.activeElement.dataset.criterion),cid);
          const expected=cid==='AC-01'?'Đã kiểm chứng':cid==='AC-04'?(run===0?'Đã kiểm chứng':'Chưa kiểm chứng'):'Vi phạm';
          assert((await root.locator('.detail h2').textContent()).includes(expected));
          if(run===1&&['AC-03','AC-04'].includes(cid))assert((await root.locator('.detail').textContent()).includes('Còn gap coverage bắt buộc'));
          const overflow=await root.evaluate(element=>element.scrollWidth>element.clientWidth+1);
          assert.equal(overflow,false);
        }
        await root.locator('.detail details summary').first().click();
        assert(await root.locator('.detail pre').first().isVisible());
        await root.locator('.meta summary').click();
        const provenance=await root.locator('.provenance').textContent();
        assert(provenance.includes(run===0?'vf1-a-':'vf1-b-'));
        assert(!provenance.includes(run===0?'vf1-b-':'vf1-a-'));
        await root.locator('.meta summary').click();
        // Expand only for the full-content capture after testing the real viewport.
        await page.setViewportSize({width,height:5000});
        const height=await root.evaluate(element=>Math.ceil(element.getBoundingClientRect().height));
        await page.locator('iframe').evaluate((element,h)=>element.style.height=h+'px',height+48);
        const screenshot=`${colorScheme}-${width}-${run===0?'a':'b'}.png`;
        await page.screenshot({path:path.join(out,screenshot),clip:{x:0,y:0,width,height:height+64}});
        checks.push({width,colorScheme,run,criteriaChecked:4,ownProvenance:true,noOverflow:true,screenshot});
      }
      await page.setViewportSize({width,height:900});
      await root.locator('[data-run="0"]').focus();
      for(const key of ['Enter','Tab','Enter','Tab','Enter','Tab','Tab','Tab','Enter'])await page.keyboard.press(key);
      assert.equal(await frame.evaluate(()=>document.activeElement.dataset.criterion),'AC-04');
      await page.keyboard.press('Tab');
      assert.equal(await frame.evaluate(()=>document.activeElement.tagName),'SUMMARY');
      await page.keyboard.press('Space');
      assert(await root.locator('.detail pre').first().isVisible());
      assert.deepEqual(errors,[]);
      assert(blocked.every(url=>url.startsWith('https://unpkg.com/@floating-ui/')||url.startsWith('https://unpkg.com/lucide@')));
      checks.push({width,colorScheme,keyboardJourney:true,pageErrors:errors,blockedPreviewAssets:blocked,appNetworkRequests:0});
      await context.close();
    }
    fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify({status:'PASS',fragmentSha256:hash(fragment),previewSha256:hash(preview),checkerSha256:hash(__filename),checks},null,2),{flag:'wx'});
    process.stdout.write(JSON.stringify({status:'PASS',records:checks.length,screenshots:12}));
  }finally{await browser.close();}
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
