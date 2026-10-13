"""Draw faithful synthetic Windows console layouts, not text-only evidence sheets."""
import json,textwrap,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).parent
OUT=ROOT.parents[2]/'mobile_api/demo_assets/ad_auditor'
OUT.mkdir(parents=True,exist_ok=True)
S=2;W=1280;H=720
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
MONO='/System/Library/Fonts/Menlo.ttc'
class UI:
 def __init__(self):
  self.im=Image.new('RGB',(W*S,H*S),'#f0f0f0');self.d=ImageDraw.Draw(self.im);self.issues=[]
 def box(self,xy,fill,outline=None,width=1):self.d.rectangle(tuple(int(v*S) for v in xy),fill,outline,width=width*S)
 def text(self,x,y,t,size=12,bold=False,color='#202020',mono=False):
  font=ImageFont.truetype(MONO if mono else BOLD if bold else FONT,size*S)
  bounds=self.d.textbbox((x*S,y*S),str(t),font=font)
  if bounds[2]>W*S or bounds[3]>H*S:self.issues.append(str(t))
  self.d.text((x*S,y*S),str(t),font=font,fill=color)
 def line(self,xy,fill='#b6b6b6',width=1):self.d.line(tuple(v*S for v in xy),fill,width=width*S)
 def wrap(self,x,y,t,width=95,size=12,color='#202020'):
  lines=textwrap.wrap(str(t),width=width,break_long_words=False,break_on_hyphens=False) or ['']
  for i,l in enumerate(lines):self.text(x,y+i*(size+5),l,size,color=color)
  return len(lines)*(size+5)
 def icon(self,x,y,kind='folder'):
  if kind=='user':
   self.d.ellipse((x*S,(y+2)*S,(x+9)*S,(y+11)*S),fill='#277ab0');self.box((x-2,y+12,x+12,y+21),'#277ab0')
  elif kind=='Computer':
   self.box((x,y+2,x+15,y+13),'#92bad6','#365c77');self.line((x+8,y+13,x+8,y+19));self.line((x+2,y+20,x+14,y+20))
  else:self.box((x,y+6,x+17,y+19),'#e7c15c','#ac873b');self.box((x+1,y+3,x+9,y+8),'#e7c15c')
 def frame(self,title,num):
  self.box((0,0,W,31),'#e6edf5');self.icon(12,4,'Computer');self.text(37,8,title,13)
  self.text(W-108,7,'—     □     ×',15);self.box((0,31,W,57),'#f6f6f6')
  self.text(12,37,'File      Action      View      Help',12);self.line((0,57,W,57))
  self.box((0,58,W,87),'#f0f0f0');self.text(14,65,'←   →    ↑     ↻     ▣    ?     Find…',14,color='#23628c');self.line((0,87,W,87))
  self.box((0,679,W,H),'#e8edf3');self.text(13,691,f'Eğitim amaçlı sentetik ekran · Kurgusal veri · AD-{num:03}',12,bold=True,color='#314f66')
 def tree(self,items,selected=''):
  self.box((0,88,237,678),'#fff','#c3c3c3');self.text(10,97,'Console Root',12,bold=True)
  items=items or ['corp.local','Builtin','Users','Computers','Finance','Groups','Domain Controllers']
  selected=selected.split('/')[-1].strip()
  selected=selected if selected in items else items[0]
  for i,t in enumerate(items):
   y=125+i*33
   if t == selected:self.box((8,y-3,227,y+27),'#d9e8f7')
   self.text(9,y+1,'>',11,color='#555');self.icon(29,y-1);self.text(53,y+2,t,11)
 def table(self,x,y,w,headers,rows,maxheight=380):
  n=len(headers);ratios=[.33,.25,.42] if n==3 else [.22,.24,.30,.24] if n==4 else [1/n]*n
  col=[w*r for r in ratios];self.box((x,y,x+w,y+30),'#edf1f5','#c9c9c9');cx=x
  for i,h in enumerate(headers):self.text(cx+9,y+8,h,11,bold=True);cx+=col[i];self.line((cx,y,cx,y+30))
  cy=y+31
  for r in rows:
   wraps=[textwrap.wrap(str(v),max(12,int(col[j]/6)),break_long_words=False) or [''] for j,v in enumerate(r)]
   rh=max(34,min(72,18*max(len(v) for v in wraps)+9))
   if cy+rh>y+maxheight:break
   self.box((x,cy,x+w,cy+rh),'#fff' if rows.index(r)%2==0 else '#f4f7fa');cx=x
   for j,v in enumerate(wraps):
    for k,l in enumerate(v[:3]):self.text(cx+9,cy+7+k*17,l,11)
    cx+=col[j]
   self.line((x,cy+rh,x+w,cy+rh),'#e0e0e0');cy+=rh
  return cy
 def fields(self,x,y,w,fields,rowheight=43):
  for i,(label,value) in enumerate(fields):
   cy=y+i*rowheight;self.text(x,cy+8,label+':',11,bold=True)
   self.box((x+260,cy,x+w,cy+33),'#fff','#b1b1b1')
   if value in ('Checked','Unchecked'):
    self.box((x+273,cy+8,x+288,cy+23),'#fff','#777')
    if value=='Checked':self.line((x+276,cy+14,x+281,cy+20,x+288,cy+9),'#333',2)
    self.text(x+302,cy+8,value,11)
   else:self.wrap(x+273,cy+6,value,width=max(25,int((w-290)/6)),size=11)
 def tabs(self,x,y,names,active):
  cx=x
  for name in names:
   width=max(78,len(name)*7+22);self.box((cx,y,cx+width,y+29),'#fff' if name==active else '#e5e5e5','#aaa');self.text(cx+11,y+8,name,11,bold=name==active);cx+=width
for q in json.loads((ROOT/'package.json').read_text())['questions']:
 ev=q['evidence'];u=UI();tool=ev['tool'];n=q['number'];u.frame(ev['title'],n)
 if tool in ('properties','group','adac'):
  u.tree(ev['tree'],ev['title']);u.box((259,107,1254,659),'#f2f2f2','#aaa');u.text(279,124,ev['title'],15,bold=True)
  tabs=['General','Account','Member Of','Attribute Editor'] if tool=='properties' else ['General','Members','Member Of'] if tool=='group' else ['Overview','Password Settings']
  u.tabs(279,159,tabs,ev['tab']);y=205
  if ev['fields']:
   if ev['tab']=='Attribute Editor':u.table(281,y,946,['Attribute','Value'],ev['fields']);y+=len(ev['fields'])*43+18
   else:u.fields(281,y,946,ev['fields']);y+=len(ev['fields'])*43+18
  if ev['rows']:u.table(281,y,946,ev['headers'],ev['rows'],maxheight=max(70,620-y))
  for x,label in [(976,'OK'),(1060,'Cancel'),(1150,'Apply')]:u.box((x,626,x+76,650),'#f7f7f7','#aaa');u.text(x+16,632,label,11)
 elif tool=='event':
  u.tree(ev['tree'],'Security');u.box((1030,88,W,678),'#f3f5f7','#ccc');u.text(1050,102,'Actions',13,bold=True)
  for i,t in enumerate(['Open Saved Log…','Create Custom View…','Filter Current Log…','Properties','Find…','Save All Events As…']):u.text(1051,141+i*38,t,11,color='#22679a')
  u.text(251,100,'Security',15,bold=True);u.table(250,132,765,ev['headers'],ev['rows'],maxheight=170)
  u.tabs(250,312,['General','Details'],'General');u.box((250,344,1014,660),'#fff','#aaa');y=352
  for label,value in ev['fields']:
   u.text(264,y,label+':',11,bold=True);h=u.wrap(461,y,value,width=75,size=11);y+=max(25,h+5)
 elif tool=='powershell':
  u.box((0,88,W,678),'#012456');u.text(21,104,'Windows PowerShell',13,bold=True,color='#fff');y=132
  y+=u.wrap(21,y,'PS C:\\Audit> '+ev['title'],width=150,size=13,color='#fff')+10
  # Real console-style tabular output with explicit columns, not a screenshot of a prose paragraph.
  widths=[max(len(ev['headers'][i]),max((len(str(r[i])) for r in ev['rows']),default=0))+3 for i in range(len(ev['headers']))]
  widths=[min(v,65) for v in widths]
  head=''.join(h.ljust(widths[i]) for i,h in enumerate(ev['headers']));u.text(21,y,head,12,mono=True,color='#d6e8ff');y+=28
  u.text(21,y,' '.join('-'*(v-1) for v in widths),12,mono=True,color='#d6e8ff');y+=27
  for r in ev['rows']:
   u.text(21,y,''.join(str(v).ljust(widths[i]) for i,v in enumerate(r)),12,mono=True,color='#fff');y+=34
  u.text(21,y+30,'PS C:\\Audit> _',13,mono=True,color='#fff')
 else:
  u.tree(ev['tree'],ev['title']);u.text(255,103,ev['title'],15,bold=True)
  if tool=='gpmc':u.tabs(255,138,['Scope','Details','Settings','Delegation','Results','Group Policy Inheritance'],ev['tab']);y=184
  else:y=144
  if ev['fields']:u.fields(258,y,985,ev['fields']);y+=len(ev['fields'])*43+20
  if ev['rows']:u.table(254,y,997,ev['headers'],ev['rows'],maxheight=max(100,600-y))
  if tool=='workpaper':u.text(254,630,'Evidence owner: Selin (Denetim Yöneticin)   |   Snapshot: 2026-10-13',11,color='#526174')
 if ev['footer']:u.wrap(253 if tool!='powershell' else 22,646,ev['footer'],width=130,size=10,color='#526174' if tool!='powershell' else '#d6e8ff')
 if u.issues:raise ValueError(f'AD-{n:03}: clipped text {u.issues}')
 path=OUT/f'screen_{n:03}.png';u.im.save(path,optimize=True)
manifest=[{'number':q['number'],'file':q['image'],'sha256':hashlib.sha256((OUT/f'screen_{q["number"]:03}.png').read_bytes()).hexdigest(),'width':2560,'height':1440,'synthetic':True} for q in json.loads((ROOT/'package.json').read_text())['questions']]
(ROOT/'images.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Rendered',len(manifest),'unique synthetic Windows UIs')
