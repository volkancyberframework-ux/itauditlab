import json,random
from pathlib import Path
root=Path(__file__).resolve().parent
def save(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
rows=[]
for n,line in enumerate((root/'grc-bootcamp/cases.txt').read_text().splitlines(),1):
 topic,evidence,right,a,b,c,why,impact=line.split('|')
 command,*out=evidence.split('~');chapter=(n-1)//16+1
 opts=[{'id':k,'text':t,'feedback':why if k=='a' else 'Bu yaklaşım kanıttaki kontrol amacını karşılamaz. '+why} for k,t in zip('abcd',[right,a,b,c])]
 random.Random(1400+n).shuffle(opts)
 explanation=f'✅ Doğru yanıt\n{right}\n\n🧠 Teknik gerekçe\n{why}\n\n⚠️ Risk\nKanıtta görülen durum: {"; ".join(out)}. Bu durum kontrolün kapsamı, zamanı veya işletimine ilişkin doğrulama gerektirir.\n\n💼 İş etkisi\n{impact}\n\n🛠️ Önerilen kontrol\n{right}. Sorumlu ve vade belirlenmeli; uygulama bağımsız kanıtla tekrar test edilmelidir.\n\nDiğer yanıtların değerlendirilmesi\n'+'\n'.join(f'{o["text"]}: {o["feedback"]}' for o in opts if o['id']!='a')
 rows.append(dict(external_id=f'grc-bootcamp-v1-{n:03}',number=n,chapter=chapter,kind='image',topic=topic,prompt='Görsel kanıtı incele. Bu durumda en uygun denetim değerlendirmesi veya sonraki adım hangisidir?',context=f'GRC Ustası Bootcamp · Vaka {n}/80\n\nNovaTek şirketinin denetim ekibindesin. {topic} kontrolü için ekrandaki kayıt sana sunuldu. Kayıttaki kapsam, dönem ve fiili uygulamayı esas alarak karar ver. Görsel eğitim için üretilmiş kurgusal kanıttır.',options=opts,answer=['a'],explanation=explanation,hint=why,difficulty='beginner' if n<=32 else 'intermediate' if n<=64 else 'advanced',goals=[topic],base_xp=10,premium=True,published=True,order=n,card_pages=[],image=f'grc-bootcamp/screen_{n:03}.png',technical=why,risk='; '.join(out),impact=impact,control=right,evidence=dict(command=command,output='\n'.join(out))))
assert len(rows)==80
save(root/'grc-bootcamp/package.json',dict(slug='grc-bootcamp-v1',title='GRC Ustası · Bootcamp Senaryoları',description='80 özgün görselli denetim vakası. Yönetişim, kanıt, erişim, değişiklik, süreklilik, tedarikçi ve bulgu yönetimi. Yalnızca ücretli mobil üyeler. Her görsel kurgusal eğitim kanıtıdır.',modules=['Denetim planlama ve kanıt','Kimlik ve ayrıcalıklı erişim','Değişiklik ve IT operasyonları','Güvenlik, veri ve süreklilik','Risk, tedarikçi ve raporlama'],questions=rows))
rows=[];pattern=['choice','scenario','sentence_order','drag_select','multi_select','choice','scenario','sentence_order','drag_select','fill_blank']
orders=json.loads((root/'cism-manager/orders.json').read_text())
for n,line in enumerate((root/'cism-manager/cases.txt').read_text().splitlines(),1):
 topic,context,right,a,b,why,validate,term=line.split('|');kind=pattern[(n-1)%10];domain=(n-1)//25+1
 opts=[dict(id=k,text=t,feedback=why if k=='a' else 'Bu karar vakadaki yönetim amacını karşılamaz. '+why) for k,t in zip('abc',[right,a,b])];answer=['a'];prompt='Bilgi güvenliği yöneticisi olarak en uygun yaklaşım hangisidir?'
 if kind=='multi_select':
  opts.append(dict(id='d',text=validate,feedback='Bu doğrulama kararın uygulanması ve etkinliği için gerekli kanıtı sağlar.'));answer=['a','d'];prompt='Bu vakada uygun olan iki tamamlayıcı adımı seç.'
 elif kind=='sentence_order':
  steps=orders[str(n)];opts=[dict(id=f's{i}',text=t,feedback=f'Bu vakada doğru süreçte {i+1}. adımdır. '+why) for i,t in enumerate(steps)];answer=[f's{i}' for i in range(4)];prompt='Vakayı yönetmek için adımları ilk yapılacak olandan son yapılacak olana sırala.'
 elif kind=='fill_blank':
  opts=[];answer=[term];prompt=f'Bu karar hangi temel kavramı uygular? Beklenen kavramın Türkçe adını yaz: “{right}”.'
 elif kind=='drag_select':prompt='Karar kartları arasından bu vaka için en uygun olanı seç.'
 random.Random(2300+n).shuffle(opts)
 # Lowercase variants are accepted by the existing normalized text evaluator.
 rows.append(dict(external_id=f'cism-manager-v1-{n:03}',number=n,domain=domain,kind=kind,topic=topic,prompt=prompt,context=f'CISM yönetici simülasyonu · Vaka {n}/100\n\n{context} Elindeki bilgileri kullanarak iş riskini, yetkiyi ve kontrol amacını birlikte değerlendir.',options=opts,answer=answer,explanation=f'🧠 Neden doğru?\n{why}\n\n💼 Gerçek iş hayatında\n{validate}. Kararı ilgili iş/risk sahibiyle kayıt altına al; etkisini ve kalan riski izle.',hint='Teknik aracın varlığından önce iş hedefini, risk karar yetkisini ve eldeki kanıtı düşün.',difficulty='beginner' if (n-1)%25<8 else 'intermediate' if (n-1)%25<18 else 'advanced',goals=[topic],base_xp=10,premium=True,published=True,order=n,card_pages=[]))
for n in (11,31,51,71,91):
 row=rows[n-1];original=row['options'];claim=next(o['text'] for o in original if o['id']==('a' if n in (11,51,91) else 'b'))
 truth=n in (11,51,91);reason=row['explanation'].split('\n\n💼')[0].removeprefix('🧠 Neden doğru?\n')
 row.update(presentation='true_false',prompt='“'+claim+'” yaklaşımı bu vaka için uygundur. Doğru mu, yanlış mı?',options=[dict(id='dogru',text='Doğru',feedback=reason),dict(id='yanlis',text='Yanlış',feedback=reason)],answer=['dogru' if truth else 'yanlis'])
for n in (15,35,55,75,95):
 row=rows[n-1];row['presentation']='pair_matching';row['prompt']='Bu vaka için doğru olan iki amaç–uygulama eşleştirmesini seç.'
 for o in row['options']:
  o['text']=('Uygun karar → ' if o['id']=='a' else 'Doğrulama kanıtı → ' if o['id']=='d' else 'Etkin risk yönetimi → ')+o['text']
assert len(rows)==100
save(root/'cism-manager/package.json',dict(slug='cism-manager-v1',title='CISM · Güvenlik Yöneticisi Simülasyonu',description='100 özgün vaka; CISA simülasyonundaki aynı altı soru türü ve dağılımı. Dört CISM alanında 25’er uygulama. Dengeli eğitim setidir; resmi sınav sorusu veya resmi sınav ağırlıklarının kopyası değildir. Yalnızca ücretli mobil üyeler.',modules=['Domain 1: Bilgi güvenliği yönetişimi','Domain 2: Bilgi güvenliği risk yönetimi','Domain 3: Bilgi güvenliği programı','Domain 4: Olay yönetimi'],questions=rows))
