// HC1 generated standalone view; new headless contexts, no personal browser session.
const {chromium}=require('C:/Users/Aki Chan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');

(async()=>{
  const [batch,output]=process.argv.slice(2);
  fs.mkdirSync(output,{recursive:false});
  const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const checks=[];
  try{
    for(const label of ['a','b'])for(const width of [390,1280])for(const colorScheme of ['light','dark']){
      const folder=path.join(batch,label,'accepted');
      const view=JSON.parse(fs.readFileSync(path.join(folder,'view.json'),'utf8'));
      const dashboard=path.join(folder,'dashboard.html');
      const context=await browser.newContext({viewport:{width,height:900},colorScheme});
      const page=await context.newPage(),errors=[],requests=[];
      page.on('pageerror',error=>errors.push(error.message));
      await page.route(/^https?:/,route=>{requests.push(route.request().url());return route.abort();});
      await page.goto(pathToFileURL(path.resolve(dashboard)).href);
      const root=page.locator('#vf1-report');
      await root.locator('.detail h2').waitFor();
      assert.equal(await root.locator('[data-run]').count(),1);
      assert((await root.locator('[data-run="0"]').textContent()).includes(view.runId));
      await root.locator('[data-run="0"]').focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.run),'0');
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.criterion),'AC-01');
      for(const row of view.criteria){
        await root.locator(`[data-criterion="${row.criterionId}"]`).focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.evaluate(()=>document.activeElement.dataset.criterion),row.criterionId);
        const expected={verified:'Đã kiểm chứng',failed:'Vi phạm',unverified:'Chưa kiểm chứng'}[row.status];
        assert((await root.locator('.detail h2').textContent()).includes(expected));
        assert.equal(await root.evaluate(el=>el.scrollWidth>el.clientWidth+1),false);
        if(label==='b'&&['AC-03','AC-04'].includes(row.criterionId))
          assert((await root.locator('.detail').textContent()).includes('Còn gap coverage bắt buộc'));
      }
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(()=>document.activeElement.tagName),'SUMMARY');
      await page.keyboard.press('Space');
      assert(await root.locator('.detail pre').first().isVisible());
      await root.locator('.meta summary').click();
      const provenance=await root.locator('.provenance').textContent();
      assert(provenance.includes(view.runId));
      assert(!provenance.includes(label==='a'?'hc1-b-':'hc1-a-'));
      assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
      const screenshot=`${label}-${width}-${colorScheme}.png`;
      await page.screenshot({path:path.join(output,screenshot),fullPage:true});
      checks.push({label,width,colorScheme,status:'PASS',dashboardSha256:hash(dashboard),
                   viewSha256:hash(path.join(folder,'view.json')),screenshot,screenshotSha256:hash(path.join(output,screenshot)),
                   keyboardSourceJourney:true,ownRunProvenance:true,overflow:false,pageErrors:errors,network:requests});
      await context.close();
    }
    fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify({status:'PASS',checkerSha256:hash(__filename),checks},null,2),{flag:'wx'});
    process.stdout.write(JSON.stringify({status:'PASS',checks:checks.length}));
  }finally{await browser.close();}
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
