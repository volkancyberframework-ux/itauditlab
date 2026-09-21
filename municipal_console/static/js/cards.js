(() => {
  let cards=JSON.parse(document.querySelector('#cards-data').textContent), selected=null, deferredOnly=false, busy=false;
  const initialCount=cards.length;
  const panel=document.querySelector('#active-card'), form=document.querySelector('#card-form'), feedback=document.querySelector('#card-feedback');
  const text=(id,value)=>document.getElementById(id).textContent=value;
  function render(preferred) {
    const visible=cards.filter(c=>!deferredOnly||c.deferred);
    selected=visible.find(c=>c.id===preferred)||visible.find(c=>!c.deferred)||visible[0];
    text('remaining-count',`${cards.length} kontrol kaldı`);
    text('deferred-count',` · ${cards.filter(c=>c.deferred).length} açıklama bekliyor`);
    const progress=document.querySelector('#card-progress');progress.max=Math.max(initialCount,1);progress.value=Math.max(0,initialCount-cards.length);
    panel.hidden=!selected;document.querySelector('#card-empty').hidden=!!selected;
    text('empty-title',cards.length?'Bu bölüm tamam!':'Bitti!');
    text('empty-text',cards.length?'Açıklama bekleyen kart yok. Diğer kontrol sorularına devam edebilirsiniz.':'Tüm kontrol yanıtları ve açıklamaları kaydedildi. Teşekkürler!');
    const queue=document.querySelector('#card-queue');queue.replaceChildren();
    visible.forEach(c=>{const button=document.createElement('button');button.type='button';button.className='queue-item'+(c.deferred?' needs-explanation':'');button.textContent=`${c.code}${c.deferred?' · Açıklama bekliyor':''}`;button.setAttribute('aria-current',String(c===selected));button.addEventListener('click',()=>navigate(c.id));queue.append(button);});
    if (!selected)return;
    form.reset();form.elements.control.value=selected.id;
    text('control-code',selected.code);text('control-title',selected.title);text('control-question',selected.question);text('control-guidance',selected.guidance);
    const radio=Array.from(form.elements.status).find(e=>e.value===selected.status);if(radio)radio.checked=true;
    form.elements.explanation.value=selected.explanation;
    panel.classList.toggle('needs-explanation',selected.deferred);
  }
  const dirty=()=>selected&&(form.elements.status.value!==selected.status||form.elements.explanation.value!==selected.explanation);
  function navigate(id){if(busy)return;if(dirty()&&!confirm('Kaydedilmemiş değişiklikleriniz var. Kart değiştirmek istiyor musunuz?'))return;render(id);document.querySelector('#control-title').focus();}
  async function save(defer) {
    if(busy||!selected)return;
    feedback.textContent='';
    if(!form.elements.status.value){feedback.textContent='Önce bir yanıt seçin.';return;}
    if(!defer&&(!form.elements.explanation.value.trim()||!form.elements.declaration.checked)){feedback.textContent='Açıklamayı yazın ve doğruluk onayını işaretleyin.';return;}
    const index=cards.findIndex(c=>c.id===selected.id), next=cards[index+1]?.id||cards[0]?.id;
    const data=new FormData(form);data.set('defer',defer?'1':'0');busy=true;
    form.querySelectorAll('button').forEach(b=>b.disabled=true);
    try {
      const response=await fetch(panel.dataset.saveUrl,{method:'POST',body:data,credentials:'same-origin',headers:{'Accept':'application/json'}});
      if(response.redirected || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Oturum doğrulanamadı. Sayfayı yenileyip yeniden deneyin; gerekirse denetçinizden yeni kod isteyin.');
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Kaydedilemedi.');
      cards=result.cards;render(next);feedback.textContent=result.message;
      if(selected)document.querySelector('#control-title').focus();
    } catch(error){feedback.textContent=error.message||'Bağlantı kurulamadı. Yanıtınız ekranda korunuyor; tekrar deneyin.';}
    finally{busy=false;form.querySelectorAll('button').forEach(b=>b.disabled=false);}
  }
  form.addEventListener('submit',e=>{e.preventDefault();save(false);});
  document.querySelector('#defer-card').addEventListener('click',()=>save(true));
  [['show-all',false],['show-deferred',true]].forEach(([id,value])=>document.getElementById(id).addEventListener('click',()=>{if(busy)return;if(dirty()&&!confirm('Kaydedilmemiş değişiklikler var. Devam edilsin mi?'))return;deferredOnly=value;document.getElementById('show-all').setAttribute('aria-pressed',String(!value));document.getElementById('show-deferred').setAttribute('aria-pressed',String(value));render();}));
  window.addEventListener('beforeunload',e=>{if(dirty()||busy){e.preventDefault();e.returnValue='';}});
  render();
})();
