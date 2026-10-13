(()=>{
 let pending=null,busy=false;
 const installed=()=>matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 // Installation is requested by the authenticated Flutter profile card only.
 window.grcPwaInstalled=installed;
 window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();pending=e;});
 window.addEventListener('appinstalled',()=>{pending=null;});
 function guide(){
  if(document.querySelector('.grc-install-guide'))return;
  const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  const d=document.createElement('dialog');d.className='grc-install-guide';d.setAttribute('aria-label','Uygulamayı yükleme rehberi');
  const title=document.createElement('h2');title.textContent=ios?'iPhone’a yükle':'Ana ekranına ekle';
  const intro=document.createElement('p');intro.textContent=ios?'iPhone’da son onay Safari menüsünden verilir.':'Tarayıcının yükleme menüsünü kullanabilirsin.';
  const steps=document.createElement('ol');
  for(const text of ios?[
   'Bu adresi Safari’de aç: app.grcustasi.com',
   'Safari’nin menüsünü (•••) açıp Paylaş’ı seç; doğrudan Paylaş simgesi görünüyorsa ona dokun.',
   'Ana Ekrana Ekle’yi seç. “Web Uygulaması Olarak Aç” görünüyorsa açık bırak ve Ekle’ye dokun.',
  ]:[
   'Chrome veya Edge menüsünü aç.',
   'Uygulamayı yükle veya Ana ekrana ekle seçeneğini seç.',
   'Yüklemeyi onayla; ana ekranındaki GRC Ustası simgesinden aç.',
  ]){const li=document.createElement('li');li.textContent=text;steps.append(li);}
  const help=document.createElement('p');help.className='grc-install-note';help.textContent=ios?'Paylaş menüsü Safari’ye aittir; uygulamanın içinden otomatik açılamaz. Önce bu rehberi kapat, sonra Safari menüsünü aç.':'Yükleme seçeneği görünmüyorsa bu adresi güncel Chrome veya Edge ile aç.';
  const actions=document.createElement('div');actions.className='grc-install-actions';
  const copy=document.createElement('button');copy.type='button';copy.className='grc-install-copy';copy.textContent='Adresi kopyala';copy.onclick=async()=>{try{await navigator.clipboard.writeText('https://app.grcustasi.com/');copy.textContent='Adres kopyalandı';}catch{copy.textContent='app.grcustasi.com';}};
  const close=document.createElement('button');close.type='button';close.className='grc-install-done';close.textContent=ios?'Rehberi kapat, Safari’den devam et':'Tamam';close.onclick=()=>d.close();
  const focus=document.activeElement;d.addEventListener('close',()=>{d.remove();focus?.focus();});actions.append(copy,close);d.append(title,intro,steps,help,actions);document.body.append(d);d.showModal();close.focus();
 }
 const style=document.createElement('style');style.textContent='.grc-install-guide{box-sizing:border-box;max-width:min(480px,calc(100vw - 32px));max-height:calc(100dvh - 32px);border:1px solid #294657;border-radius:24px;padding:28px;background:#0e2030;color:#e8f1f7;font:16px/1.65 system-ui;box-shadow:0 20px 80px #0008}.grc-install-guide::backdrop{background:#020b15bb;backdrop-filter:blur(5px)}.grc-install-guide h2{font-size:24px;margin:0 0 12px}.grc-install-guide ol{padding-left:24px}.grc-install-guide li{padding:6px 0}.grc-install-note{font-size:14px;color:#abc4d2}.grc-install-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.grc-install-guide button{font:600 14px/1.5 system-ui;min-height:44px;border-radius:12px;padding:12px 16px;cursor:pointer}.grc-install-copy{border:1px solid #46606f;background:transparent;color:#d9e7ef}.grc-install-done{border:0;background:#84d8bd;color:#06271e;flex:1}.grc-install-guide button:focus-visible{outline:3px solid #d6ba77;outline-offset:3px}';document.head.append(style);
 window.grcPwaInstall=async()=>{
  if(installed()||busy)return;
  if(!pending){guide();return;}
  const event=pending;pending=null;busy=true;
  try{await event.prompt();await event.userChoice;}catch{guide();}finally{busy=false;}
 };
 if('serviceWorker' in navigator)navigator.serviceWorker.register('/grc-pwa-sw.js',{scope:'/',updateViaCache:'none'}).then(r=>r.update()).catch(()=>{});
})();
