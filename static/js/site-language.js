/* Local catalogs: user data is never sent to a translation service. */
(()=>{'use strict';
const script=document.currentScript,urls=JSON.parse(script.dataset.catalogs),root=document.documentElement;
const languages=new Set(['tr','en','fr','es','ja','zh-CN','vi','ar']);
const normalize=value=>value.replace(/\s+/g,' ').trim();
const originals=new WeakMap(),attributes=new WeakMap(),cache=new Map();
let catalog={},sequence=0,observer;
const switcher=document.querySelector('[data-language-switcher]');
if(!switcher)return;
const header=document.querySelector('.nav-inner,.tb-header-inner,.site-header .container,header .container,.grc-legal-toolbar');
if(header){const anchor=header.querySelector('.theme-toggle,.login-btn');header.insertBefore(switcher,anchor)}else switcher.classList.add('grc-language-fallback');
// Measure the real translated menu instead of assuming every language fits
// the same desktop breakpoint. Temporary measurement styles never paint.
const navigation=document.querySelector('header.nav,header.corp-nav');
const navRow=navigation?.querySelector('.nav-inner,.nav-row');
let layoutFrame=0;
function fitNavigation(){
  if(!navRow)return;
  navigation.classList.add('grc-nav-measuring');
  navigation.classList.remove('grc-nav-no-cta');
  const style=getComputedStyle(navRow);
  const available=navRow.clientWidth-(parseFloat(style.paddingLeft)||0)-(parseFloat(style.paddingRight)||0);
  const requiredWidth=()=>{
    const items=[...navRow.children].filter(item=>getComputedStyle(item).display!=='none');
    return items.reduce((width,item)=>width+item.getBoundingClientRect().width,0)+(parseFloat(style.columnGap)||0)*Math.max(0,items.length-1);
  };
  // Keep desktop links visible when dropping the duplicate CTA is enough.
  navigation.classList.toggle('grc-nav-no-cta',requiredWidth()>available-12);
  const compact=requiredWidth()>available-12||matchMedia(navigation.matches('.nav')?'(max-width:1120px)':'(max-width:1080px)').matches;
  navigation.classList.remove('grc-nav-measuring');
  navigation.classList.toggle('grc-nav-compact',compact);
  if(!compact&&navigation.classList.contains('open')){
    navigation.classList.remove('open');
    navigation.querySelector('.menu,.nav-menu')?.setAttribute('aria-expanded','false');
  }
}
function scheduleLayout(){cancelAnimationFrame(layoutFrame);layoutFrame=requestAnimationFrame(fitNavigation)}
if(navRow){
  if('ResizeObserver'in window)new ResizeObserver(scheduleLayout).observe(navRow);
  window.addEventListener('resize',scheduleLayout,{passive:true});
  document.fonts?.ready.then(scheduleLayout);
  scheduleLayout();
}

const excluded=element=>!element||element.closest('script,style,noscript,textarea,code,pre,.brand,.tb-brand,.newsletter-brand,[translate="no"],.notranslate,[contenteditable="true"]');
let patterns=[];
const translate=value=>{const key=normalize(value);let translated=catalog[key];if(!translated){for(const pattern of patterns){const match=key.match(pattern.regex);if(match){translated=pattern.value.replace(/GRCPLACEHOLDER(\d+)/g,(_,index)=>match[Number(index)+1]);break}}}return translated?value.replace(value.trim(),translated):value};
const compilePatterns=copy=>Object.entries(copy).filter(([key])=>key.includes('${')).map(([key,value])=>{const parts=key.split(/\$\{[^}]+\}/g);return {regex:new RegExp('^'+parts.map(part=>part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('(.+?)')+'$'),value}});
function apply(scope){
  if(scope.nodeType===Node.TEXT_NODE){if(!excluded(scope.parentElement)){const last=originals.get(scope);if(!last||scope.nodeValue!==last.output)originals.set(scope,{source:scope.nodeValue,output:scope.nodeValue});const record=originals.get(scope);record.output=translate(record.source);if(scope.nodeValue!==record.output)scope.nodeValue=record.output}return}
  if(scope.nodeType!==Node.ELEMENT_NODE&&scope.nodeType!==Node.DOCUMENT_NODE)return;
  if(scope.nodeType===Node.ELEMENT_NODE&&excluded(scope))return;
  const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode()))apply(node);
  const elements=scope.querySelectorAll('[title],[placeholder],[aria-label],[alt],meta[name="description"],meta[property="og:title"],meta[property="og:description"]');
  const update=el=>{if(excluded(el))return;let records=attributes.get(el);if(!records){records={};attributes.set(el,records)}for(const key of ['title','placeholder','aria-label','alt',...(el.tagName==='META'?['content']:[])]){if(!el.hasAttribute(key))continue;const value=el.getAttribute(key),record=records[key];if(!record||value!==record.output)records[key]={source:value,output:value};records[key].output=translate(records[key].source);if(value!==records[key].output)el.setAttribute(key,records[key].output)}};
  if(scope.nodeType===Node.ELEMENT_NODE)update(scope);elements.forEach(update);
}
function observe(){observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['title','placeholder','aria-label','alt']})}
observer=new MutationObserver(changes=>{observer.disconnect();for(const change of changes){if(change.type==='childList')change.addedNodes.forEach(apply);else apply(change.target)}observe()});
async function select(language,persist=true){
  if(!languages.has(language))language='tr';const request=++sequence,status=switcher.querySelector('[role=status]');status.textContent='';switcher.setAttribute('aria-busy','true');
  try{
    let next={};if(language!=='tr'){if(!cache.has(language)){const response=await fetch(urls[language],{credentials:'same-origin'});if(!response.ok)throw Error('catalog');cache.set(language,await response.json())}next=cache.get(language)}
    if(request!==sequence)return;observer.disconnect();catalog=next;patterns=compilePatterns(next);apply(document);root.lang=language;root.dir=language==='ar'?'rtl':'ltr';document.querySelectorAll('form[action*="checkout"]').forEach(form=>{let input=form.querySelector('input[name="language"]');if(!input){input=document.createElement('input');input.type='hidden';input.name='language';form.append(input)}input.value=language});scheduleLayout();
    switcher.querySelector('[data-language-code]').textContent=language==='zh-CN'?'ZH':language.toUpperCase();switcher.querySelectorAll('[data-language]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.language===language)));observe();
    if(persist){try{localStorage.setItem('grc-language',language)}catch{}const url=new URL(location.href);if(language==='tr')url.searchParams.delete('lang');else url.searchParams.set('lang',language);try{history.replaceState(null,'',url)}catch{}}
    switcher.open=false;
  }catch{status.textContent='Çeviri yüklenemedi. Lütfen tekrar deneyin. / Please try again.'}finally{if(request===sequence)switcher.removeAttribute('aria-busy')}
}
switcher.querySelectorAll('[data-language]').forEach(button=>button.addEventListener('click',()=>select(button.dataset.language)));
document.addEventListener('click',event=>{if(!switcher.contains(event.target))switcher.open=false});document.addEventListener('keydown',event=>{if(event.key==='Escape'&&switcher.open){switcher.open=false;switcher.querySelector('summary').focus()}});
let saved='tr';try{saved=localStorage.getItem('grc-language')||'tr'}catch{}const requested=new URL(location.href).searchParams.get('lang');select(requested||saved,Boolean(requested));observe();
})();
