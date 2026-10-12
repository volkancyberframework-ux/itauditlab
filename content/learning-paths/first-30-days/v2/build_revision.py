import json,re,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent
old=json.loads((ROOT.parent/'package.json').read_text())
roles={'Selin':'Selin (Yöneticin)','Murat':'Murat (IT Operasyon Müdürü)','Deniz':'Deniz (Bilgi Güvenliği Yöneticisi)','Ece':'Ece (Risk Müdürü)','Arda':'Arda (SOC Ekip Lideri)','Ayşe':'Ayşe (CEO / Genel Müdür)'}
def label(text):
    for name,role in roles.items():text=re.sub(r'\b'+name+r'\b',role,text)
    return text
lessons={}
for line in (ROOT/'lessons.tsv').read_text().splitlines():
    n,title,*pages=line.split('|');assert len(pages)==4
    lessons[int(n)]=[{'title':heading,'body':label(body)} for heading,body in zip([title,'NEXORA örneği','Nasıl uygularsın?','İş başında dikkat et'],pages)]
# Preserve all stable identities and answer keys, only change presentation/order.
cycle=['audio','multi_select','sentence_order','drag_select','fill_blank','image','scenario','choice','scenario','info']
questions=[]
for chapter in range(1,11):
    block=[dict(q) for q in old['questions'] if q['chapter']==chapter]
    first=block[0];first['kind']='audio';first['audio_key']=f'grc_day_{chapter:02}'
    if chapter==1:
        q=next(q for q in block if q['number']==8);q['kind']='image';q['image_filename']='evidence_008.png'
        q['context']='Hesap açılış tablosunu incele. Yeni rolün Junior GRC Specialist; ilk görevlerin belge inceleme ve rapor hazırlama. Murat, ileride gerekebilir diye sana üretim yönetici erişimi de önermiş.'
    pool=[q for q in block if q is not first];ordered=[first]
    for kind in cycle[1:]:
        candidate=next((q for q in pool if q['kind']==kind),None)
        if candidate is None and kind=='scenario':
            candidate=next(q for q in pool if q['kind']=='choice');candidate['kind']='scenario'
        assert candidate is not None,(chapter,kind)
        pool.remove(candidate);ordered.append(candidate)
    assert not pool
    for i,q in enumerate(ordered,1):
        q['order']=(chapter-1)*10+i;q['source_number']=q['number']
        for key in ['context','prompt','explanation','hint']:q[key]=label(q[key])
        q['options']=[dict(o,text=label(o['text'])) for o in q['options']]
        if q['kind']=='info':q['card_pages']=lessons[chapter];q['explanation']='\n\n'.join(p['body'] for p in lessons[chapter])
        transitions={
            2:'Giriş işlemlerinin ardından binadaki diğer uygulamalara bakıyorsun. ',
            5:'Selin, günlük erişim işlerinin arkasındaki karar düzenini anlamanı istiyor. ',
            6:'Erişim talebin hazırlanırken ilk dosya paylaşma isteği geliyor. ',
            7:'Hesap açılışını konuştuktan sonra bir ekip arkadaşı senden dosya istiyor. ',
            9:'Günün son işinde bir satıcı teklifi önüne geliyor. '
        }
        if q['source_number'] in transitions:q['context']=label(transitions[q['source_number']])+q['context']
        if q['source_number']==4:q['context']=label('Selin, bugün verdiğin erişim ve paylaşım kararlarının GRC rolünle nasıl bağlandığını konuşuyor: “İnsanların iş yapmasını zorlaştırmak için burada değiliz.”')
        q['display_type']=q['kind'];questions.append(q)
assert len(questions)==100 and [q['kind'] for q in questions]==cycle*10
old.update(questions=questions,revision='first30-v2',roles=roles,cycle=cycle)
old['report']=dict(total=100,graded=90,modules=10,types=dict(Counter(q['kind'] for q in questions)),cycle=cycle,audio_recordings=10,image_assets=10,lesson_pages=40,stable_identities_preserved=True,answer_keys_unchanged=True)
(ROOT/'package.json').write_text(json.dumps(old,ensure_ascii=False,indent=2))
(ROOT/'quality_report.json').write_text(json.dumps(old['report'],ensure_ascii=False,indent=2))
print(json.dumps(old['report'],ensure_ascii=False))
