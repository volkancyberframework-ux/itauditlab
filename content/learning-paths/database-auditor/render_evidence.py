"""Readable, original 2560x1440 synthetic database audit evidence, one asset per case."""
import hashlib,json,textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).parent;DEST=ROOT.parents[2]/'mobile_api/demo_assets/database_auditor';DEST.mkdir(parents=True,exist_ok=True)
FONT='/System/Library/Fonts/Menlo.ttc';SANS='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(n,mono=False):return ImageFont.truetype(FONT if mono else SANS,n)
manifest=[]
for q in json.loads((ROOT/'package.json').read_text())['questions']:
 im=Image.new('RGB',(2560,1440),'#0b1523');d=ImageDraw.Draw(im)
 d.rounded_rectangle((64,60,2496,1380),radius=28,fill='#101e30',outline='#28435f',width=3)
 for x,col in [(108,'#ff6d6d'),(146,'#ffc45c'),(184,'#58d99a')]:d.ellipse((x,94,x+20,114),fill=col)
 d.text((240,84),'NovaTek • Veritabanı kanıt laboratuvarı',font=font(30),fill='#d9e7f6')
 d.text((2070,84),f'DB-{q["number"]:03} / 055',font=font(30,True),fill='#6dd7c7')
 d.line((65,150,2495,150),fill='#28435f',width=2)
 d.text((110,190),q['topic'],font=font(42),fill='#ffffff')
 d.text((110,252),f'Bölüm {q["chapter"]}: '+json.loads((ROOT/'package.json').read_text())['modules'][q['chapter']-1],font=font(27),fill='#9bb3cc')
 d.rounded_rectangle((108,330,2450,1190),radius=16,fill='#07111c',outline='#294158',width=2)
 prefixes={'PG':'PG-CRM / psql > ', 'MY':'MYSQL-WEB / mysql > ', 'MS':'SQL-ERP / query > ', 'OR':'ORA-PAY / SQL > '}
 command=prefixes[q['engine']]+q['evidence']['command']
 command_lines=textwrap.wrap(command,145,break_long_words=False,break_on_hyphens=False)
 for i,line in enumerate(command_lines):
  assert font(25,True).getlength(line)<2300,(q['number'],'command width')
  d.text((145,365+i*36),line,font=font(25,True),fill='#70e0bd')
 y=365+len(command_lines)*36+36
 for line in q['evidence']['output'].splitlines():
  for wrapped in textwrap.wrap(line,110,replace_whitespace=False,drop_whitespace=False) or ['']:
   assert y<1130,(q['number'],y)
   assert font(29,True).getlength(wrapped)<2300,(q['number'],'output width')
   d.text((145,y),wrapped,font=font(29,True),fill='#e0eaf6');y+=48
 d.text((145,1135),'[end of evidence • read-only training view]',font=font(23,True),fill='#7793ae')
 d.text((110,1230),'EĞİTİM SİMÜLASYONU • Kurgusal sistemler ve veriler • Gerçek sunucudan alınmamıştır.',font=font(29),fill='#ffc97b')
 d.text((110,1290),'Kanıtı oku → Kapsamı ayır → Karar ver → Açıklamadan öğren',font=font(28),fill='#b5cada')
 target=DEST/Path(q['image']).name;im.save(target,optimize=True)
 manifest.append({'number':q['number'],'file':q['image'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(ROOT/'images.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'{len(manifest)} images rendered')
