(() => {
  const link=document.querySelector('#card-mailto');if(!link)return;
  const feedback=document.querySelector('#mail-feedback');
  document.querySelector('#card-eml').addEventListener('click',()=>{
    const content=JSON.parse(document.querySelector('#card-eml-data').textContent);
    const url=URL.createObjectURL(new Blob([content],{type:'message/rfc822'}));
    const a=document.createElement('a');a.href=url;a.download='bt-kontrol-sorulari.eml';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    feedback.textContent='Tablolu taslak indirildi. Dosyayı e-posta uygulamanızda açabilirsiniz.';
  });
  document.querySelector('#card-copy').addEventListener('click',async()=>{
    const preview=document.querySelector('#card-email-preview');
    try{await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([preview.innerHTML],{type:'text/html'}),'text/plain':new Blob([preview.innerText],{type:'text/plain'})})]);feedback.textContent='Tablo kopyalandı; e-posta metnine yapıştırabilirsiniz.';}
    catch{feedback.textContent='Otomatik kopyalama kullanılamıyor. Tablolu .eml taslağını indirin.';}
  });
  link.click();
})();
