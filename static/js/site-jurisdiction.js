/* Jurisdiction content is server-rendered from reviewed records. */
(()=>{'use strict';
const root=document.documentElement,script=document.currentScript,config=JSON.parse(script.dataset.config);
let sequence=0;
const store=(key,value)=>{try{localStorage.setItem(key,value)}catch{}document.cookie=encodeURIComponent(key)+'='+encodeURIComponent(value)+'; Path=/; Max-Age=31536000; SameSite=Lax'+(location.protocol==='https:'?'; Secure':'')};
const read=key=>{try{return localStorage.getItem(key)}catch{return null}};
function countryFor(language,initial=false){const allowed=config.countries[language];const query=new URL(location.href).searchParams;const explicit=initial?query.get('country'):null;const saved=read('grc-country-'+language);return allowed.includes(explicit)?explicit:allowed.includes(saved)?saved:allowed[0]}
function metadata(language,country){
 const url=new URL(location.href);url.search='';url.searchParams.set('lang',language);url.searchParams.set('country',country);
 document.querySelector('link[rel=canonical]')?.setAttribute('href',url.href.replace(location.origin,'https://www.grcustasi.com'));
 const copy=config.legalPage?{title:config.names[country]+' · '+config.eyebrows[language]+' | GRC Ustası',description:config.headings[language]+' '+config.names[country]}:config.seo[language];
 if(copy&&config.otPage){const quote=config.prices[language];const formatted=language==='tr'?new Intl.NumberFormat('tr-TR').format(quote.amount)+' TL':new Intl.NumberFormat(language,{style:'currency',currency:quote.currency,currencyDisplay:'code',maximumFractionDigits:0}).format(quote.amount);for(const key of Object.keys(copy))copy[key]=copy[key].replace(/119[.,]999[\s\S]*$/,formatted+'.')}
 if(copy){document.title=copy.title;for(const key of ['description','og:title','og:description']){const element=document.querySelector(key==='description'?'meta[name="description"]':'meta[property="'+key+'"]');if(element)element.content=copy[key]||(key==='og:title'?copy.title:copy.description)||''}}
 document.querySelector('meta[property="og:url"]')?.setAttribute('content',url.href.replace(location.origin,'https://www.grcustasi.com'));
 document.querySelector('meta[property="og:locale"]')?.setAttribute('content',language==='zh-CN'?'zh_CN':language+'_'+country);
}
function options(language,country){const switcher=document.querySelector('[data-language-switcher]');if(switcher){switcher.querySelector('.grc-language-heading').textContent=config.languageLabels[language];switcher.querySelector('summary').setAttribute('aria-label',config.languageLabels[language])}const menu=document.querySelector('[data-jurisdiction-menu]');if(!menu)return;menu.querySelector('label span').textContent=config.labels[language];const select=menu.querySelector('select');select.setAttribute('aria-label',config.labels[language]);select.replaceChildren(...config.countries[language].map(code=>{const option=document.createElement('option');option.value=code;option.textContent=config.names[code];option.selected=code===country;return option}));}
async function update(language,country,remember=true){
 const request=++sequence;country=config.countries[language].includes(country)?country:config.countries[language][0];
 if(remember){store('grc-language',language);store('grc-country-'+language,country);}options(language,country);metadata(language,country);root.dataset.jurisdiction=country;
 const url=new URL(location.href);url.searchParams.set('lang',language);url.searchParams.set('country',country);history.replaceState(null,'',url);
 document.querySelectorAll('a[data-legal-link]').forEach(link=>{link.href='/mevzuat/?lang='+language+'&country='+country});
 document.querySelectorAll('a[href]').forEach(link=>{const target=new URL(link.href,location.href);if(target.origin===location.origin&&['/','/kurumsal/','/mevzuat/','/ot-guvenligi-bootcamp/'].includes(target.pathname)){target.searchParams.set('lang',language);target.searchParams.set('country',country);link.href=target.href}});
 const section=document.querySelector('[data-legal-section]');if(section){
  section.setAttribute('aria-busy','true');
  try{const params=new URLSearchParams({lang:language,country,detail:config.detailed?'1':'0',surface:config.surface});const response=await fetch('/api/mevzuat/?'+params,{credentials:'same-origin'});if(!response.ok)throw Error('legal');const data=await response.json();if(request!==sequence)return;const parsed=new DOMParser().parseFromString(data.html,'text/html');const replacement=parsed.querySelector('[data-legal-section]');if(replacement){section.replaceWith(replacement);const schema=parsed.querySelector('[data-legal-schema]');const old=document.querySelector('[data-legal-schema]');if(schema&&old)old.replaceWith(schema)}}
  catch{if(request===sequence){section.hidden=true;const message=document.createElement('p');message.className='wrap notranslate';message.translate=false;message.textContent=config.errors[language];section.after(message)}}
 }
 if(request===sequence){document.querySelectorAll('[data-legal-section]').forEach(el=>el.removeAttribute('aria-busy'));root.dispatchEvent(new CustomEvent('grc:jurisdiction',{detail:{language,country}}))}
}
document.addEventListener('change',event=>{if(event.target.matches('[data-country-select]'))update(root.lang,event.target.value)});
root.addEventListener('grc:language',event=>{const query=new URL(location.href).searchParams;const remember=!event.detail.initial||query.has('lang')||query.has('country')||Boolean(read('grc-language'));update(event.detail.language,countryFor(event.detail.language,event.detail.initial),remember)});
})();
