export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
export class ImageTransform {
  constructor(width, height, viewportWidth, viewportHeight) {
    this.width=width; this.height=height; this.resize(viewportWidth,viewportHeight);
  }
  resize(w,h) { this.viewportWidth=w;this.viewportHeight=h;this.fit(); }
  fit() { this.fitScale=Math.min(this.viewportWidth/this.width,this.viewportHeight/this.height);this.scale=this.fitScale;this.x=(this.viewportWidth-this.width*this.scale)/2;this.y=(this.viewportHeight-this.height*this.scale)/2; }
  reset() { this.scale=1;this.x=(this.viewportWidth-this.width)/2;this.y=(this.viewportHeight-this.height)/2;this.bound(); }
  zoom(factor, anchorX=this.viewportWidth/2,anchorY=this.viewportHeight/2) {
    const next=clamp(this.scale*factor,Math.min(this.fitScale,1)*.5,Math.max(8,this.fitScale*8));
    const ratio=next/this.scale;this.x=anchorX-(anchorX-this.x)*ratio;this.y=anchorY-(anchorY-this.y)*ratio;this.scale=next;this.bound();
  }
  pan(dx,dy) { this.x+=dx;this.y+=dy;this.bound(); }
  bound() {
    const w=this.width*this.scale,h=this.height*this.scale;
    this.x=w<=this.viewportWidth?(this.viewportWidth-w)/2:clamp(this.x,this.viewportWidth-w,0);
    this.y=h<=this.viewportHeight?(this.viewportHeight-h)/2:clamp(this.y,this.viewportHeight-h,0);
  }
}
