import { launch } from "/Users/bilalsbaiby/work/company/bin/qa-lib.mjs";
const [url, tag] = process.argv.slice(2);
const b = await launch();
for (const [n,w,h,m] of [["1440",1440,900,false],["390",390,844,true]]) {
  const c = await b.newContext({viewport:{width:w,height:h},isMobile:m,deviceScaleFactor:1}); const p = await c.newPage();
  await p.goto(url,{waitUntil:"networkidle"}); await p.evaluate(()=>document.fonts.ready);
  await p.screenshot({path:`${tag}-${n}.png`,fullPage:true});
  console.log(tag,n,"overflow",await p.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth),"fonts",await p.evaluate(()=>[...document.fonts].filter(x=>x.status=="loaded").map(x=>x.family+x.weight).join(",")));
}
await b.close();
