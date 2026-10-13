/* Web-only adapter loaded by the Python HTML response, never a Flutter edit. */
(()=>{
  const nativeFetch=window.fetch.bind(window);
  const ready=import('/web-features/web-learning.mjs');
  let api,workspace,active=false;
  const map=path=>{
    if(path==='/api/mobile/v1/paths/')return '/web-api/paths/';
    if(path==='/api/mobile/v1/sessions/')return '/web-api/sessions/';
    if(/^\/api\/mobile\/v1\/sessions\/[0-9a-f-]+\/answer\/$/.test(path))return path.replace('/api/mobile/v1/','/web-api/');
    for(const action of ['login','refresh','logout'])if(path===`/api/mobile/v1/auth/${action}/`)return `/web-api/auth/${action}/`;
    return path;
  };
  window.fetch=async(input,init)=>{
    const req=new Request(input,init),url=new URL(req.url);
    if(url.origin!==location.origin||!url.pathname.startsWith('/api/mobile/v1/'))return nativeFetch(input,init);
    let module;try{module=await ready;}catch{return nativeFetch(input,init);}api??=new module.WebApi(nativeFetch);
    const authorization=req.headers.get('Authorization');if(authorization&&!api.bearer)api.bearer=authorization;
    const route=map(url.pathname);url.pathname=route;const headers=new Headers(req.headers);
    if(route==='/web-api/paths/')headers.set('X-GRC-Web-Bridge','1');
    const response=await nativeFetch(url.href,{method:req.method,headers,credentials:'same-origin',signal:req.signal,...(!['GET','HEAD'].includes(req.method)?{body:await req.clone().arrayBuffer()}: {})});
    if(route==='/web-api/auth/logout/'&&response.ok){api.bearer='';workspace?.destroy();workspace=null;active=false;return response;}
    if(response.ok&&response.headers.get('Content-Type')?.includes('json')){
      const data=await response.clone().json();
      if(route.startsWith('/web-api/auth/')&&data.access)api.bearer=`Bearer ${data.access}`;
      if(route==='/web-api/sessions/'&&data.question&&(data.path.web_has_images||data.question.image)&&!active){
        workspace??=new module.WebLearningWorkspace(api);active=true;workspace.open(data);
      }
    }
    return response;
  };
})();
