const CACHE='wrestlestream-shell-v1';
const SHELL=['./','./index.html','./style.css','./app.js','./manifest.webmanifest','./assets/icon.svg','./assets/icon-maskable.svg','./assets/icon-192.png','./assets/icon-512.png','./assets/icon-maskable-512.png','./data/catalogue.json','./data/sources.json'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
 const req=event.request;if(req.method!=='GET'||new URL(req.url).origin!==location.origin)return;
 if(/\/data\/(catalogue|sources)\.json$/.test(new URL(req.url).pathname)){
  event.respondWith(fetch(req).then(resp=>{if(resp.ok){const copy=resp.clone();caches.open(CACHE).then(c=>c.put(req,copy));}return resp;}).catch(()=>caches.match(req)));return;
 }
 event.respondWith(caches.match(req).then(cached=>cached||fetch(req)));
});
