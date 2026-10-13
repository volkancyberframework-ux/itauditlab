import {FullscreenImageViewer} from './fullscreen-image-viewer.mjs';
const element=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
export class WebApi {
  constructor(fetcher=window.fetch.bind(window)){this.fetcher=fetcher;this.bearer='';this.refreshing=null;}
  async renew(){
    if(!this.refreshing)this.refreshing=this.fetcher('/web-api/auth/refresh/',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}'}).then(async r=>{const d=await r.json();if(!r.ok)throw Error('Oturum yenilenemedi. Ana sayfaya dönüp hesabını yeniden açabilirsin.');this.bearer=`Bearer ${d.access}`;}).finally(()=>this.refreshing=null);
    return this.refreshing;
  }
  async response(url,options={},retry=true){
    const target=new URL(url,location.origin);
    if(target.origin!==location.origin)throw Error('Görsel yalnız uygulamanın kendi adresinden yüklenebilir.');
    const headers=new Headers(options.headers);if(this.bearer)headers.set('Authorization',this.bearer);
    let r=await this.fetcher(target.href,{...options,headers,credentials:'same-origin'});
    if(r.status===401&&retry){await this.renew();return this.response(url,options,false);}
    return r;
  }
  async request(path,body){
    const r=await this.response(path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},...(body!==undefined?{body:JSON.stringify(body)}:{})});
    const data=await r.json();if(!r.ok)throw Error(data.detail||'İşlem tamamlanamadı. Tekrar deneyebilirsin.');return data;
  }
  async image(url){const r=await this.response(url);if(!r.ok)throw Error('Görsel yüklenemedi. Bağlantını kontrol edip tekrar dene.');return URL.createObjectURL(await r.blob());}
}
export class WebLearningWorkspace {
  constructor(api,{onHome=()=>location.reload()}={}) {
    this.api=api;this.onHome=onHome;this.viewer=new FullscreenImageViewer();this.urls=new Set();this.generation=0;
    this.dialog=element('dialog',undefined,'grc-web-workspace');this.dialog.setAttribute('aria-label','Görselli öğrenme görevleri');
    this.dialog.addEventListener('cancel',e=>e.preventDefault());document.body.append(this.dialog);
  }
  open(state){this.state=state;if(!this.dialog.open)this.dialog.showModal();this.render();}
  draftKey(){return `grc:web:draft:${this.state.id}:${this.state.question?.id}`;}
  save(){try{sessionStorage.setItem(this.draftKey(),JSON.stringify(this.draft));}catch{}}
  load(){try{return JSON.parse(sessionStorage.getItem(this.draftKey()))||{selected:[],arranged:[],text:''};}catch{return{selected:[],arranged:[],text:''};}}
  clearMedia(){this.viewer.close();for(const url of this.urls)URL.revokeObjectURL(url);this.urls.clear();}
  base(){
    this.clearMedia();this.dialog.replaceChildren();const top=element('header',undefined,'grc-web-top');top.append(element('h1',this.state.path.title));
    const home=element('button','Ana sayfa');home.type='button';home.addEventListener('click',()=>{this.save();this.onHome();});top.append(home);this.dialog.append(top);
    this.main=element('main',undefined,'grc-web-main');this.dialog.append(this.main);this.dialog.scrollTop=0;
  }
  render(){
    const generation=++this.generation;this.base();this.error=element('p','', 'grc-web-error');this.error.setAttribute('role','alert');
    if(this.state.complete){this.main.append(element('h2','Bölüm tamamlandı 🎉'),element('p',`${this.state.correct}/${this.state.question_total} doğru · ${this.state.xp_earned} XP`));
      if(this.state.evaluation)this.main.append(element('p',this.state.evaluation.text,'grc-web-explanation'));
      if(!this.state.path.is_complete){const next=element('button','Sonraki bölüm','grc-web-primary');next.addEventListener('click',async()=>{next.disabled=true;try{this.state=await this.api.request('/web-api/sessions/',{path_id:this.state.path.id});this.render();}catch(e){this.error.textContent=e.message;next.disabled=false;}});this.main.append(next);}
      this.main.append(this.error);return;
    }
    const q=this.state.question;this.draft=this.load();this.viewed=Date.now();this.imageReady=!q.image;
    this.main.append(element('p',`${q.chapter||this.state.path.title} · ${q.number?`Soru ${q.number}`:`Görev ${this.state.answered+1}`} · ${this.state.answered+1}/${this.state.total}`,'grc-web-meta'));
    const progress=element('progress',undefined,'grc-web-progress');progress.max=this.state.total;progress.value=this.state.answered;progress.setAttribute('aria-label','Bölüm ilerlemesi');this.main.append(progress);
    if(q.context)this.main.append(element('p',q.context,'grc-web-context'));
    if(q.image){this.preview=element('section',undefined,'grc-preview');this.main.append(this.preview);this.loadImage(q,generation);}
    this.main.append(element('h2',q.prompt));
    if(q.hint){const hint=element('details',undefined,'grc-web-hint');hint.append(element('summary','📘 AD İpucu'),element('p',q.hint));this.main.append(hint);}
    if(q.audio?.length)this.audio(q.audio,generation);
    if(q.kind==='info'){const pages=q.card_pages?.length?q.card_pages:[{title:q.prompt,body:q.context}];for(const page of pages){this.main.append(element('h3',page.title),element('p',page.body,'grc-web-context'));if(page.reveal){const d=element('details');d.append(element('summary','Açıklamayı aç'),element('p',page.reveal));this.main.append(d);}}}
    else if(q.kind==='sentence_order')this.order(q);
    else if(['fill_blank','text','voice'].includes(q.kind)){
      const input=element(q.kind==='fill_blank'?'input':'textarea',undefined,'grc-web-input');input.setAttribute('aria-label','Yanıtın');input.placeholder='Yanıtın';input.value=this.draft.text;input.addEventListener('input',()=>{this.draft.text=input.value;this.save();});this.main.append(input);
      if(q.kind==='voice')this.voice(q);
    }else this.choices(q);
    this.submitButton=element('button',q.kind==='info'?'Okudum, devam et':'Cevabımı kontrol et','grc-web-primary');this.submitButton.type='button';this.submitButton.disabled=!this.imageReady;
    this.submitButton.addEventListener('click',()=>this.submit(q));this.main.append(this.submitButton,this.error);
  }
  async loadImage(q,generation){
    this.imageReady=false;if(this.submitButton)this.submitButton.disabled=true;
    this.preview.replaceChildren();const status=element('div','Görsel yükleniyor…','grc-image-status');status.setAttribute('role','status');this.preview.append(status);
    try{const url=await this.api.image(q.image);if(generation!==this.generation){URL.revokeObjectURL(url);return;}
      const img=element('img');img.alt=q.synthetic_image?'Eğitim amaçlı sentetik AD ekranı':'Soru ekran görüntüsü';img.src=url;await img.decode();if(generation!==this.generation){URL.revokeObjectURL(url);return;}
      this.urls.add(url);this.preview.replaceChildren();const open=element('button',undefined,'grc-image-open');open.type='button';open.setAttribute('aria-label','Ekran görüntüsünü büyüt');open.append(img);
      open.addEventListener('click',()=>this.viewer.open(url,img.alt).catch(()=>{this.viewer.close();this.error.textContent='Görsel açılamadı. Önizlemedeki yeniden denemeyi kullanabilirsin.';}));
      this.preview.append(open,element('p','🔍 Ekran görüntüsünü büyütmek için tıkla'));if(q.synthetic_image)this.preview.append(element('small','Eğitim amaçlı sentetik ekran · Kurgusal veri'));
      this.imageReady=true;if(this.submitButton)this.submitButton.disabled=false;
    }catch(e){if(generation!==this.generation)return;this.preview.replaceChildren(element('p',e.message,'grc-web-error'));const retry=element('button','Görseli yeniden yükle');retry.addEventListener('click',()=>this.loadImage(q,generation));this.preview.append(retry);}
  }
  choices(q){
    const list=element('div',undefined,'grc-web-choices');for(const option of q.options){
      const label=element('label',undefined,'grc-web-option'),input=element('input');input.type=q.kind==='multi_select'?'checkbox':'radio';input.name=`question-${q.id}`;input.value=option.id;input.checked=this.draft.selected.includes(option.id);
      input.addEventListener('change',()=>{if(input.type==='radio')this.draft.selected=[option.id];else this.draft.selected=input.checked?[...new Set([...this.draft.selected,option.id])]:this.draft.selected.filter(v=>v!==option.id);this.save();});label.append(input,element('span',option.text));if(q.kind==='drag_select'){label.draggable=true;label.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',option.id));}list.append(label);
    }this.main.append(list);
    if(q.kind==='drag_select'){const zone=element('div','Risk kartını buraya sürükle veya kartı tıklayarak seç.','grc-drop-zone');zone.setAttribute('aria-label','Seçilen risk kartı');zone.addEventListener('dragover',e=>e.preventDefault());zone.addEventListener('drop',e=>{e.preventDefault();const id=e.dataTransfer.getData('text/plain'),input=[...list.querySelectorAll('input')].find(i=>i.value===id);if(input){input.click();zone.textContent=q.options.find(o=>o.id===id).text;}});this.main.append(zone);}
  }
  order(q){
    const container=element('section');container.setAttribute('aria-label','Sıralama kartları');
    const paint=()=>{container.replaceChildren();const selected=this.draft.arranged;for(const id of selected){const option=q.options.find(o=>o.id===id),row=element('div',undefined,'grc-order-row');row.draggable=true;row.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',id));row.addEventListener('dragover',e=>e.preventDefault());row.addEventListener('drop',e=>{e.preventDefault();const moved=e.dataTransfer.getData('text/plain');if(!selected.includes(moved)||moved===id)return;selected.splice(selected.indexOf(moved),1);selected.splice(selected.indexOf(id),0,moved);this.save();paint();});row.append(element('span',`${selected.indexOf(id)+1}. ${option.text}`));for(const [label,delta] of [['↑',-1],['↓',1]]){const b=element('button',label);b.setAttribute('aria-label',`${option.text}: ${delta<0?'yukarı':'aşağı'} taşı`);b.addEventListener('click',()=>{const at=selected.indexOf(id),to=at+delta;if(to>=0&&to<selected.length){[selected[at],selected[to]]=[selected[to],selected[at]];this.save();paint();}});row.append(b);}const remove=element('button','Çıkar');remove.addEventListener('click',()=>{selected.splice(selected.indexOf(id),1);this.save();paint();});row.append(remove);container.append(row);}
      const pool=element('div',undefined,'grc-web-choices');for(const option of q.options.filter(o=>!selected.includes(o.id))){const b=element('button',option.text);b.addEventListener('click',()=>{selected.push(option.id);this.save();paint();});pool.append(b);}container.append(pool);
    };paint();this.main.append(container);
  }
  async audio(urls,generation){for(const url of urls){const audio=element('audio',undefined,'grc-web-audio');audio.controls=true;audio.preload='none';this.main.append(audio);try{const blob=await this.api.image(url);if(generation!==this.generation){URL.revokeObjectURL(blob);continue;}this.urls.add(blob);audio.src=blob;}catch(e){audio.replaceWith(element('p','Ses yüklenemedi. Soruyu metinle okuyabilirsin.','grc-web-error'));}}}
  async submit(q){
    if(q.image&&!this.imageReady)return;this.submitButton.disabled=true;this.error.textContent='';
    let answer=['fill_blank','text','voice'].includes(q.kind)?this.draft.text:q.kind==='sentence_order'?this.draft.arranged:this.draft.selected;
    try{
      if(q.kind==='info'){this.state=await this.api.request(`/api/mobile/v1/sessions/${this.state.id}/continue/`,{question_id:q.id});this.render();return;}
      const result=await this.api.request(`/web-api/sessions/${this.state.id}/answer/`,{question_id:q.id,answer,duration_seconds:Math.min(86400,Math.floor((Date.now()-this.viewed)/1000))});this.showFeedback(result);
    }catch(e){this.error.textContent=e.message;this.submitButton.disabled=!this.imageReady;}
  }
  showFeedback(result){
    try{sessionStorage.removeItem(this.draftKey());}catch{}++this.generation;this.base();this.main.append(element('h2',result.correct?'Doğru karar ✅':result.pending?'Yanıt incelemeye gönderildi':'Birlikte değerlendirelim'),element('p',result.explanation||result.detail,'grc-web-explanation'));
    const next=element('button','Devam et','grc-web-primary');next.addEventListener('click',()=>{this.state=result.session;this.render();});this.main.append(next);next.focus();
  }
  voice(q){
    const start=element('button','Sesli yanıt kaydet'),stop=element('button','Kaydı bitir ve gönder');stop.hidden=true;
    start.addEventListener('click',async()=>{try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:true});this.stream=stream;const audioContext=new AudioContext(),input=audioContext.createMediaStreamSource(stream),processor=audioContext.createScriptProcessor(4096,1,1),chunks=[];this.audioContext=audioContext;
      processor.onaudioprocess=e=>chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));input.connect(processor);processor.connect(audioContext.destination);this.recorded=Date.now();start.hidden=true;stop.hidden=false;
      stop.onclick=async()=>{try{stop.disabled=true;processor.disconnect();input.disconnect();stream.getTracks().forEach(t=>t.stop());const duration=Math.max(1,Math.round((Date.now()-this.recorded)/1000));await audioContext.close();
        if(duration>180)throw Error('Sesli yanıt en fazla 3 dakika olabilir.');let length=chunks.reduce((n,a)=>n+a.length,0),samples=new Float32Array(length),offset=0;for(const c of chunks){samples.set(c,offset);offset+=c.length;}
        const rate=16000,sourceRate=audioContext.sampleRate,resampled=new Float32Array(Math.floor(samples.length*rate/sourceRate));for(let i=0;i<resampled.length;i++){const at=i*sourceRate/rate,lo=Math.floor(at),fraction=at-lo;resampled[i]=samples[lo]*(1-fraction)+(samples[Math.min(lo+1,samples.length-1)]||0)*fraction;}samples=resampled;
        const bytes=new ArrayBuffer(44+samples.length*2),v=new DataView(bytes),write=(at,s)=>{for(let i=0;i<s.length;i++)v.setUint8(at+i,s.charCodeAt(i));};write(0,'RIFF');v.setUint32(4,36+samples.length*2,true);write(8,'WAVE');write(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);write(36,'data');v.setUint32(40,samples.length*2,true);samples.forEach((s,i)=>v.setInt16(44+i*2,Math.max(-1,Math.min(1,s))*32767,true));
        const form=new FormData();form.set('question_id',q.id);form.set('duration',duration);form.set('file',new Blob([bytes],{type:'audio/wav'}),'response.wav');const r=await this.api.response(`/api/mobile/v1/sessions/${this.state.id}/voice/`,{method:'POST',body:form});const result=await r.json();if(!r.ok)throw Error(result.detail);this.showFeedback({...result,pending:true});
      }catch(e){this.error.textContent=e.message;start.hidden=false;stop.hidden=true;stop.disabled=false;}};
    }catch(e){this.error.textContent=e.message;start.hidden=false;stop.hidden=true;}});this.main.append(start,stop);
  }
  destroy(){++this.generation;this.stream?.getTracks().forEach(t=>t.stop());this.audioContext?.close();this.clearMedia();this.viewer.destroy();this.dialog.close();this.dialog.remove();}
}
