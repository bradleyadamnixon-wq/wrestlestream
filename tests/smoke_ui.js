// Headless application smoke test without browser-only dependencies.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ROOT=path.join(__dirname,'..');
const elements = new Map();
const element = selector => {
 if(!elements.has(selector)) elements.set(selector, {
   innerHTML:'',textContent:'', hidden:false, checked:false,
   classList:{toggle(){},add(){},remove(){}},
   addEventListener(){}, setAttribute(){},removeAttribute(){},
   showModal(){},close(){},replaceChildren(){},focus(){},setSelectionRange(){}
 });
 return elements.get(selector);
};
const catalog = JSON.parse(fs.readFileSync(path.join(ROOT,'data/catalogue.json'),'utf8'));
const sources = JSON.parse(fs.readFileSync(path.join(ROOT,'data/sources.json'),'utf8'));
const mem = new Map();
const ctx={
 document:{querySelector:element,querySelectorAll:()=>[],body:{addEventListener(){}}},
 window:{addEventListener(){},scrollTo(){}},
 location:{protocol:'https:',hash:''},
 navigator:{onLine:true},
 localStorage:{getItem:k=>mem.get(k)??null,setItem:(k,v)=>mem.set(k,v)},
 fetch:async url=>({ok:true,json:async()=> url.includes('catalogue')?catalog:sources}),
 URL,Date,Intl,console,clearTimeout,setTimeout,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(ROOT,'app.js'),'utf8'),ctx);
(async()=>{
 await new Promise(resolve=>setTimeout(resolve,50));
 assert.ok(element('#content').innerHTML.includes('MLW Fusion'),'Starter video displayed');
 vm.runInContext("navigate('browse')",ctx);
 assert.ok(element('#content').innerHTML.includes('Browse all wrestling'));
 assert.ok(element('#content').innerHTML.includes('TNA Xplosion'));
 vm.runInContext("toggleSaved('yt-E0PvsiNpoz4')",ctx);
 assert.ok(JSON.parse(mem.get('ws-saved')).includes('yt-E0PvsiNpoz4'));
 vm.runInContext("state.prefs.spoilers=true;render()",ctx);
 assert.ok(element('#content').innerHTML.includes('TAP TO REVEAL'));
 vm.runInContext("navigate('live')",ctx);
 assert.ok(element('#content').innerHTML.includes('No free live streams verified'));
 vm.runInContext("navigate('watchlist')",ctx);
 assert.ok(element('#content').innerHTML.includes('MLW Fusion')===false,'Spoiler title concealed');
 console.log('PASS: real catalogue, browse, save, spoilers, empty live guide, watchlist');
})().catch(e=>{console.error(e);process.exitCode=1;});
