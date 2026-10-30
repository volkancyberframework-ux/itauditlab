const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('static/js/course-video.js', 'utf8');
function setup(sdk=true) {
  const events = {}, calls = [], callbacks = {};
  const frame = {dataset:{src:'https://iframe.mediadelivery.net/embed/1/lesson?token=keep'},contentWindow:{postMessage:(...a)=>calls.push(['message',...a])}};
  const modal = {matches:s=>s==='.course-video-modal',querySelector:()=>frame};
  let currentTime=127;
  const player = {on:(name,cb)=>callbacks[name]=cb,pause:()=>calls.push(['pause',currentTime])};
  const window={location:{origin:'https://example.test'}};
  if(sdk) window.playerjs={Player:function(f){assert.equal(f,frame);calls.push(['create']);return player;}};
  vm.runInNewContext(source,{document:{addEventListener:(n,cb)=>events[n]=cb},window,URL});
  const fire=(name,target=modal,relatedTarget)=>events[name]({target,relatedTarget});
  return {frame,modal,calls,callbacks,fire};
}
test('reopening keeps the same iframe, URL and playback position; closes pause',()=>{
 const s=setup();s.fire('show.bs.modal');s.callbacks.ready();const url=s.frame.src;
 s.fire('hide.bs.modal');s.fire('show.bs.modal');
 assert.equal(s.frame.src,url);assert.match(url,/token=keep/);assert.match(url,/autoplay=false/);
 assert.equal(s.calls.filter(c=>c[0]==='create').length,1);
 assert.deepEqual(s.calls.at(-1),['pause',127]);
});
test('close before ready pauses when the player finishes loading',()=>{
 const s=setup();s.fire('show.bs.modal');s.fire('hide.bs.modal');s.callbacks.ready();
 assert.equal(s.calls.at(-1)[0],'pause');
});
test('SDK failure sends pause to exact player origin without resetting src',()=>{
 const s=setup(false);s.fire('show.bs.modal');const url=s.frame.src;s.fire('hide.bs.modal');
 assert.equal(s.frame.src,url);assert.equal(s.calls[0][2],'https://iframe.mediadelivery.net');
 assert.equal(JSON.parse(s.calls[0][1]).method,'pause');
});
test('preview gets its URL from the trigger; unrelated modals stay untouched',()=>{
 const s=setup();delete s.frame.dataset.src;
 s.fire('show.bs.modal',{matches:()=>false});assert.equal(s.frame.src,undefined);
 s.fire('show.bs.modal',s.modal,{getAttribute:()=> 'https://iframe.mediadelivery.net/embed/1/preview'});
 assert.match(s.frame.src,/preview/);
});
