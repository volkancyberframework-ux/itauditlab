import {ImageTransform} from './viewer-math.mjs';
export class FullscreenImageViewer {
  constructor() {
    this.dialog=document.createElement('dialog');this.dialog.className='grc-image-viewer';
    this.dialog.setAttribute('aria-label','Ekran görüntüsünü tam ekran incele');
    this.dialog.innerHTML=`<div class="grc-viewer-toolbar"><strong>Ekran görüntüsü</strong><output aria-live="polite"></output><button type="button" data-action="fit">Ekrana sığdır</button><button type="button" data-action="reset">Zoom sıfırla · %100</button><button type="button" data-action="close" aria-label="Görseli kapat">✕ Kapat</button></div><div class="grc-viewer-stage"><img alt="Denetim ekran görüntüsü" draggable="false"></div><p class="grc-viewer-help">Tekerlek veya iki parmakla yakınlaştır · Sürükle · Çift tıkla · ESC ile kapat</p>`;
    document.body.append(this.dialog);this.stage=this.dialog.querySelector('.grc-viewer-stage');this.image=this.stage.querySelector('img');this.output=this.dialog.querySelector('output');this.pointers=new Map();this.previousGesture=null;
    this.dialog.querySelector('[data-action="close"]').addEventListener('click',()=>this.close());
    this.dialog.querySelector('[data-action="fit"]').addEventListener('click',()=>{this.transform?.fit();this.paint();});
    this.dialog.querySelector('[data-action="reset"]').addEventListener('click',()=>{this.transform?.reset();this.paint();});
    this.dialog.addEventListener('cancel',e=>{e.preventDefault();e.stopPropagation();this.close();});
    this.stage.addEventListener('wheel',e=>{if(!this.transform)return;e.preventDefault();const p=this.position(e);this.transform.zoom(Math.exp(-e.deltaY*.002),p.x,p.y);this.paint();},{passive:false});
    this.stage.addEventListener('dblclick',e=>{const p=this.position(e);this.transform.zoom(this.transform.scale>this.transform.fitScale*1.8 ? 0.5 : 2,p.x,p.y);this.paint();});
    this.stage.addEventListener('pointerdown',e=>{if(e.button!==0&&e.pointerType==='mouse')return;e.preventDefault();try{this.stage.setPointerCapture(e.pointerId);}catch{}this.pointers.set(e.pointerId,this.position(e));this.previousGesture=this.gesture();});
    this.stage.addEventListener('pointermove',e=>{
      if(!this.pointers.has(e.pointerId)||!this.transform)return;
      e.preventDefault();this.pointers.set(e.pointerId,this.position(e));const current=this.gesture(),previous=this.previousGesture;
      if(previous){if(current.distance&&previous.distance)this.transform.zoom(current.distance/previous.distance,previous.x,previous.y);this.transform.pan(current.x-previous.x,current.y-previous.y);this.paint();}
      this.previousGesture=current;
    });
    const release=e=>{this.pointers.delete(e.pointerId);this.previousGesture=this.gesture();};
    for(const name of ['pointerup','pointercancel','lostpointercapture'])this.stage.addEventListener(name,release);
    this.resizeObserver=new ResizeObserver(()=>{if(this.dialog.open&&this.transform){this.transform.resize(this.stage.clientWidth,this.stage.clientHeight);this.paint();}});this.resizeObserver.observe(this.stage);
  }
  position(e) {const r=this.stage.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}
  gesture() {const points=[...this.pointers.values()];if(!points.length)return null;if(points.length===1)return{...points[0],distance:0};return{x:(points[0].x+points[1].x)/2,y:(points[0].y+points[1].y)/2,distance:Math.hypot(points[1].x-points[0].x,points[1].y-points[0].y)};}
  async open(src,alt='Denetim ekran görüntüsü') {
    this.returnFocus=document.activeElement;this.image.src=src;this.image.alt=alt;this.dialog.showModal();
    await this.image.decode();if(!this.dialog.open)return;
    this.transform=new ImageTransform(this.image.naturalWidth,this.image.naturalHeight,this.stage.clientWidth,this.stage.clientHeight);this.paint();this.dialog.querySelector('[data-action="close"]').focus();
  }
  paint() {if(!this.transform)return;const t=this.transform;this.image.style.transform=`translate(${t.x}px,${t.y}px) scale(${t.scale})`;this.image.style.width=`${t.width}px`;this.image.style.height=`${t.height}px`;this.output.textContent=`%${Math.round(t.scale*100)}`;this.stage.dataset.scale=String(t.scale);}
  close() {if(this.dialog.open)this.dialog.close();this.pointers.clear();this.previousGesture=null;this.returnFocus?.focus();}
  destroy() {this.close();this.resizeObserver.disconnect();this.image.removeAttribute('src');this.dialog.remove();}
}
