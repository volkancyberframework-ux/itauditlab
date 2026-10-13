const CACHE='grc-shell-20261013-v2';
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/web-features/offline.html','/icons/Icon-192.png','/icons/Icon-512.png'])).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('grc-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
 const r=e.request,u=new URL(r.url);
 if(r.method!=='GET'||u.origin!==self.location.origin||r.headers.has('Authorization')||/^\/(api|web-api|media)\//.test(u.pathname))return;
 const allowed=r.mode==='navigate'||/^\/(assets|icons|canvaskit|web-features)\//.test(u.pathname)||['/main.dart.js','/flutter.js','/flutter_bootstrap.js','/manifest.json','/favicon.png','/apple-touch-icon.png'].includes(u.pathname);
 if(!allowed)return;
 e.respondWith(fetch(r).then(response=>{if(response.ok){const copy=response.clone();e.waitUntil(caches.open(CACHE).then(c=>c.put(r,copy)));}return response;}).catch(async()=>{const cache=await caches.open(CACHE);if(r.mode==='navigate')return cache.match('/web-features/offline.html');return await cache.match(r)||Response.error();}));
});
