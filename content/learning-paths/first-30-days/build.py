"""Build exact, fictional evidence cards and the deterministic content package."""
import json, base64, textwrap
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
TITLES=['Tebrikler, İşe Alındın!','İlk Haftan: Kurumsal Hayatın Gerçekleri','İlk Görevin: Şirketi ve Risklerini Tanı','CISO Seni Toplantıya Çağırıyor','İlk IT Denetimine Katılıyorsun','Bir Güvenlik Açığı Keşfettin','Risk Müdürüyle Anlaşamıyorsun','Şirket Siber Saldırıya Uğradı!','CEO Kararını Sorguluyor','30. Gün: Performans Değerlendirmen']
EVIDENCE={
18:('Organizasyon şeması',['CEO Ayşe → IT Operasyon / Murat','IT Operasyon → Ödeme ekibi','IT Operasyon → İç Denetim','CISO Deniz → SOC / Arda','Risk Müdürü Ece → Risk ekibi','Denetim Komitesi: raporlama çizgisi yok']),
27:('Risk kaydı R-01',['Konu: Üretim hesaplarında MFA eksikliği','Etki: Yüksek | Olasılık: Orta','Risk sahibi: —','Aksiyon: MFA / eşdeğer koruma','Hedef tarih: —','Durum: Açık']),
38:('Risk ısı haritası',['                     Düşük etki | Orta etki | Yüksek etki','Yüksek olasılık         —      |    —      | R-03','Orta olasılık          R-04    |    —      | R-01','Düşük olasılık          —      |   R-02    |  —','R-03: Müşteri verisi sızıntısı','Not: R-03 yönetim raporuna alınmadı']),
47:('NEX-PAY giriş kayıtları',['İnceleme aralığı: 09.00–10.00','09.00 | admin-01 | giriş başarılı','09.19 | admin-02 | giriş başarılı','09.20–09.45 | kayıt yok','09.46 | admin-01 | giriş başarılı','Kaynak export: kişi ve saat dilimi belirtilmemiş']),
57:('IAM yetki karşılaştırması',['Hesap: svc-pay-prod','İş ihtiyacı: Ödeme işletimi','Yetki 1: Ödeme işletimi → Var','Yetki 2: Kullanıcı oluşturma → Var','Kullanıcı oluşturma onayı: bulunamadı','İnceleme sonucu: ihtiyaçla eşleşme kontrolü gerekli']),
68:('Süreli risk kabul formu',['Risk: svc-pay-prod fazla yetki','İmza: Karar sahibi','Kalan risk açıklaması: —','Kabul bitiş tarihi: —','Gözden geçirme tarihi: —','Aksiyon sahibi: Murat']),
77:('Olay zaman çizelgesi',['02.10 | NEX-PAY hizmet kesintisi başladı','02.12 | SOC alarmı oluştu','02.20 | Olay ekibi devreye alındı','03.25 | Hizmet geri döndü','Hedef: RTO 60 dakika / RPO 5 dakika','03.25 | Veri kaybı kontrolü sürüyor']),
87:('Yatırım seçenekleri — ilk yıl',['A | MFA / erişim koruması','Kurulum + bakım: 40.000 avro','Tahmini risk azalması: %60–75','B | Ek erişim izleme','Kurulum: 25.000 avro | Bakım: —','Tahmini risk azalması: %20–35']),
97:('30. gün kapanış paneli',['Panel kapsamı: NEX-PAY, tüm açık aksiyonlar','Panel: Kritik açık aksiyon = 0','Aksiyon listesi, aynı gün / aynı kapsam:','A-01 | Yetki daraltma | Kritik | Açık / gecikmiş','A-02 | MFA koruması | Yüksek | Test sürüyor','Veri kaynaklarının uzlaştırılması bekleniyor'])}
ROOT.joinpath('evidence').mkdir(exist_ok=True)
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
fonts=[ImageFont.truetype(font_path,s) for s in [36,26,21]]
assets={}
for n,(title,rows) in EVIDENCE.items():
    fonts=[ImageFont.truetype(font_path,size) for size in [34,30,23]]
    lines=[textwrap.wrap(row,46) for row in rows]
    height=240+sum(len(part)*43+25 for part in lines)
    im=Image.new('RGB',(900,height),'#f1f5f9');d=ImageDraw.Draw(im)
    d.rounded_rectangle((20,20,880,height-20),radius=20,fill='white')
    d.text((45,45),'NEXORA · '+title,font=fonts[0],fill='#115e59')
    d.text((45,102),f'Kanıt E-{n:03} · Kurgusal eğitim verisi',font=fonts[2],fill='#475569')
    y=155
    for part in lines:
        for line in part:
            d.text((45,y),line,font=fonts[1],fill='#0f172a');y+=43
        d.line((45,y+5,850,y+5),fill='#e2e8f0',width=2);y+=25
    d.text((45,height-60),'GRC Ustası · İlk 30 Gün',font=fonts[2],fill='#64748b')
    if n==38:
        im=Image.new('RGB',(900,780),'#f1f5f9');d=ImageDraw.Draw(im)
        d.text((35,30),'NEXORA · Risk ısı haritası',font=fonts[0],fill='#115e59')
        d.text((35,90),'E-038 · Kurgusal eğitim verisi',font=fonts[2],fill='#475569')
        for j,label in enumerate(['Düşük','Orta','Yüksek']):d.text((235+j*195,155),label,font=fonts[1],fill='#0f172a')
        for i,label in enumerate(['Yüksek','Orta','Düşük']):
            d.text((25,240+i*115),label,font=fonts[1],fill='#0f172a')
            for j in range(3):
                x=210+j*195;y=210+i*115
                color='#fecaca' if (i,j)==(0,2) else '#fef3c7' if j==2 or i==0 else '#dcfce7'
                d.rectangle((x,y,x+185,y+105),fill=color,outline='white',width=3)
                val={(0,2):'R-03',(1,2):'R-01',(1,0):'R-04',(2,1):'R-02'}.get((i,j),'—')
                d.text((x+45,y+32),val,font=fonts[1],fill='#0f172a')
        d.text((35,605),'Satırlar: Olasılık · Sütunlar: Etki',font=fonts[2],fill='#475569')
        d.text((35,650),'R-03: Müşteri verisi sızıntısı',font=fonts[1],fill='#0f172a')
        d.text((35,705),'Not: R-03 yönetim raporuna alınmadı',font=fonts[1],fill='#991b1b')
    file=ROOT/'evidence'/f'evidence_{n:03}.png';im.save(file)
    assets[str(n)]=base64.b64encode(file.read_bytes()).decode()
qs=[];single=0
for line in ROOT.joinpath('cases.tsv').read_text().splitlines():
    n,kind,context,prompt,a,b,c,e,explanation=line.split('|');n=int(n);chapter=(n-1)//10+1
    texts=[a,b,c,e];ids=list('abcd');answer=[];options=[]
    if kind in ['choice','scenario','image','drag_select']:
        # Correct positions cycle; rotate all original choices, not wording.
        pos=single%4;single+=1
        texts=texts[-pos:]+texts[:-pos] if pos else texts
        answer=[ids[pos]]
    elif kind=='multi_select':
        pos=(chapter-1)%4;texts=texts[-pos:]+texts[:-pos] if pos else texts
        answer=[ids[pos],ids[(pos+1)%4]]
    elif kind=='sentence_order':
        # Source is logical order; displayed order deliberately differs.
        perm=[2,0,3,1];texts=[texts[i] for i in perm]
        answer=[ids[perm.index(i)] for i in range(4)]
    elif kind=='fill_blank':answer=[a]
    elif kind=='info':answer=[]
    if kind not in ['fill_blank','info']:options=[dict(id=k,text=t) for k,t in zip(ids,texts)]
    q=dict(external_id=f'grc-first30-q-{n:03}',number=n,chapter=chapter,kind=kind,prompt=prompt,context=context,options=options,answer=answer,explanation=explanation,hint='Önce gözlenen bilgiyi, yetkiyi ve kararın iş etkisini düşün.',difficulty='beginner' if n<=30 else 'intermediate' if n<=70 else 'advanced',goals=['Risk analizi','Kanıt değerlendirme'] if kind=='image' else ['Profesyonel iletişim','Etik ve bağımsızlık'] if kind=='scenario' else ['Teknik kontrol bilgisi'],base_xp=0 if kind=='info' else 10,order=n,premium=False,published=True)
    q['card_pages']=[dict(title=prompt,body=a,reveal=explanation)] if kind=='info' else []
    if n in EVIDENCE:q['image_filename']=f'evidence_{n:03}.png'
    qs.append(q)
report=dict(total=len(qs),graded=sum(q['kind']!='info' for q in qs),modules=10,types=dict(Counter(q['kind'] for q in qs)),audio_questions=0,voice_questions=0,image_assets=len(assets),audio_intros_pending=10,text_mapping='10 professional written tasks → scenario: select a sound professional reply. No semantic prose grading is claimed.',difficulty=dict(Counter(q['difficulty'] for q in qs)))
assert len(qs)==100 and len({q['external_id'] for q in qs})==100
assert report['types']==dict(info=10,choice=19,multi_select=10,fill_blank=10,image=9,scenario=22,sentence_order=10,drag_select=10),report
assert Counter(q['chapter'] for q in qs)==Counter({i:10 for i in range(1,11)})
payload=dict(slug='grc-first-30-days',expected_path_id=26,title='🪪 İşe Alındın! İlk 30 Günün',description='NEXORA fintech şirketinde Junior GRC Specialist olarak ilk ayını yaşa. 10 bölümde 90 soru ve 10 bilgi kartıyla riskleri tanı, kanıtları incele ve yönetime karar öner. Sade Türkçe, kurgusal iş hayatı senaryoları.',modules=TITLES,questions=qs,images=assets,report=report)
ROOT.joinpath('package.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
ROOT.joinpath('quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
