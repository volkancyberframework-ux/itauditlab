"""Reviewed seed data plus editorial overrides; never cross-country/language fallback."""
import json
from pathlib import Path
from datetime import date
from django.db.utils import OperationalError, ProgrammingError
from .jurisdictions import LANGUAGE_COUNTRIES, COUNTRY_NAMES, preference

DATA = json.loads((Path(__file__).parent / 'data/regulations.json').read_text())
# UI strings are maintained independently from the site's general translation catalog.
UI = {
 'tr': ['Ülke mevzuatı','Siber güvenlik ve veri koruma: sorumluluğun yerel çerçevesi.','Ülke / hukuk alanı','Resmî kaynak','Son doğrulama','Yürürlükte','Yaklaşan düzenleme','Taslak / süreç devam ediyor','Yürürlükten kalktı','İş etkisi','Kapsam ve uygulama','Denetim odağı','Standartlar ve rehberler','ISO 27001/27002, NIST CSF, COBIT, SOC 2 ve IEC 62443 farklı standart, çerçeve ve güvence araçlarıdır. Tek başlarına ulusal kanun değildir; zorunluluk ayrıca mevzuat, sözleşme veya kapsamdan doğabilir.','Kapsamlı mevzuat görünümü','Genel bilgilendirmedir. Kapsam, sektör, eşik ve geçiş hükümleri kurum bazında değerlendirilmelidir. Resmî metin esastır.','Bu dil ve ülke için yayımlanmış doğrulanmış kayıt bulunmuyor.','Ana sayfa','Yürürlük / uygulama tarihi','Dili koruyarak ülkeyi değiştir','Ülke seçimi mevzuat görünümünü değiştirir; sözleşmenin tabi olduğu hukuku veya hizmet sağlayıcının gizlilik belgelerini değiştirmez.'],
 'en': ['Local legal framework','Cybersecurity and data protection: accountability in context.','Country / jurisdiction','Official source','Last verified','In force','Upcoming','Draft / rulemaking in progress','Repealed','Business impact','Scope and application','Audit focus','Standards and guidance','ISO 27001/27002, NIST CSF, COBIT, SOC 2 and IEC 62443 are distinct standards, frameworks and assurance tools. They are not national laws in themselves; requirements may arise separately from law, contract or scope.','Explore the legal framework','General information. Assess scope, sector, thresholds and transitional provisions for each organization. The official text controls.','No reviewed records are published for this language and jurisdiction.','Home','Effective / application date','Change jurisdiction while keeping the language','Country selection changes the legal information shown; it does not change governing contract law or the provider’s privacy documents.'],
 'fr': ['Cadre juridique local','Cybersécurité et données personnelles : des responsabilités contextualisées.','Pays / juridiction','Source officielle','Dernière vérification','En vigueur','À venir','Projet / procédure en cours','Abrogé','Impact pour l’organisation','Périmètre et application','Axes d’audit','Normes et recommandations','ISO 27001/27002, NIST CSF, COBIT, SOC 2 et IEC 62443 sont des normes, cadres ou outils d’assurance distincts. Ils ne constituent pas à eux seuls des lois nationales; une obligation peut résulter séparément de la loi, d’un contrat ou du périmètre applicable.','Explorer le cadre juridique','Information générale. Le périmètre, le secteur, les seuils et les dispositions transitoires doivent être examinés pour chaque organisation. Le texte officiel fait foi.','Aucun texte vérifié n’est publié pour cette langue et cette juridiction.','Accueil','Date d’entrée en vigueur / d’application','Changer de juridiction en conservant la langue','Le pays sélectionné modifie les informations juridiques affichées, sans modifier le droit du contrat ni les documents de confidentialité du prestataire.'],
 'es': ['Marco jurídico local','Ciberseguridad y protección de datos: responsabilidades según el contexto.','País / jurisdicción','Fuente oficial','Última verificación','En vigor','Próxima entrada en vigor','Proyecto / procedimiento en curso','Derogado','Impacto empresarial','Ámbito y aplicación','Enfoque de auditoría','Estándares y guías','ISO 27001/27002, NIST CSF, COBIT, SOC 2 e IEC 62443 son estándares, marcos y herramientas de aseguramiento diferentes. No son por sí mismos leyes nacionales; una obligación puede derivarse de la ley, un contrato o el ámbito aplicable.','Explorar el marco jurídico','Información general. El ámbito, el sector, los umbrales y las disposiciones transitorias deben evaluarse para cada organización. Prevalece el texto oficial.','No hay registros verificados publicados para este idioma y jurisdicción.','Inicio','Fecha de entrada en vigor / aplicación','Cambiar de jurisdicción conservando el idioma','La selección del país cambia la información jurídica mostrada, sin modificar la ley del contrato ni los documentos de privacidad del proveedor.'],
 'ja': ['国・地域別の法制度','サイバーセキュリティと個人情報保護：適用範囲に応じた責任。','国・法域','公式情報源','最終確認日','施行済み','施行予定','草案・手続進行中','廃止','事業への影響','適用範囲と留意点','監査の観点','標準・ガイドライン','ISO 27001/27002、NIST CSF、COBIT、SOC 2、IEC 62443は、それぞれ異なる標準、枠組み、保証の手法です。それ自体が国内法ではなく、法令、契約や適用範囲から別途義務が生じる場合があります。','法制度の詳細を見る','一般的な情報です。適用範囲、業種、基準と経過措置は組織ごとに確認してください。公式の法令本文が優先されます。','この言語と法域の確認済み公開記録はありません。','ホーム','施行日・適用開始日','言語を維持して法域を変更','国の選択は表示する法制度の情報を変更します。契約の準拠法や提供者のプライバシー文書は変更しません。'],
 'zh-CN': ['当地法律框架','网络安全与个人信息保护：结合适用范围明确责任。','国家或法域','官方来源','最后核实日期','已生效','即将生效','草案或程序进行中','已废止','业务影响','适用范围与说明','审计重点','标准与指南','ISO 27001/27002、NIST CSF、COBIT、SOC 2和IEC 62443分别属于不同的标准、框架或鉴证工具。它们本身并非国内法律；具体义务可能另行来自法律、合同或适用范围。','查看法律框架详情','仅供一般参考。请按组织核实适用范围、行业、门槛和过渡条款。以官方文本为准。','此语言和法域暂无已审核发布的记录。','首页','生效或适用日期','保留语言并更改法域','国家选择仅改变显示的法律信息，不改变合同适用法律或服务提供者的隐私文件。'],
 'vi': ['Khung pháp lý theo quốc gia','An ninh mạng và bảo vệ dữ liệu: trách nhiệm theo phạm vi áp dụng.','Quốc gia / khu vực pháp lý','Nguồn chính thức','Xác minh lần cuối','Đang có hiệu lực','Sắp có hiệu lực','Dự thảo / đang xây dựng','Đã hết hiệu lực','Tác động đối với doanh nghiệp','Phạm vi và áp dụng','Trọng tâm kiểm toán','Tiêu chuẩn và hướng dẫn','ISO 27001/27002, NIST CSF, COBIT, SOC 2 và IEC 62443 là các tiêu chuẩn, khung và công cụ bảo đảm khác nhau. Bản thân chúng không phải luật quốc gia; nghĩa vụ có thể phát sinh riêng từ pháp luật, hợp đồng hoặc phạm vi áp dụng.','Xem khung pháp lý chi tiết','Thông tin chung. Cần đánh giá phạm vi, ngành, ngưỡng và điều khoản chuyển tiếp cho từng tổ chức. Văn bản chính thức là căn cứ.','Chưa có bản ghi đã xác minh được công bố cho ngôn ngữ và quốc gia này.','Trang chủ','Ngày có hiệu lực / áp dụng','Đổi quốc gia và giữ nguyên ngôn ngữ','Lựa chọn quốc gia thay đổi thông tin pháp lý hiển thị, không thay đổi luật điều chỉnh hợp đồng hay tài liệu quyền riêng tư của nhà cung cấp.'],
 'ar': ['الإطار القانوني المحلي','الأمن السيبراني وحماية البيانات: مسؤوليات وفق نطاق التطبيق.','الدولة / الولاية القانونية','المصدر الرسمي','آخر تحقق','ساري المفعول','قادم','مشروع / إجراءات جارية','ملغى','الأثر على الأعمال','النطاق والتطبيق','محاور التدقيق','المعايير والأدلة الإرشادية','تعد ISO 27001/27002 وNIST CSF وCOBIT وSOC 2 وIEC 62443 معايير وأطر وأدوات ضمان مختلفة. وهي ليست قوانين وطنية بحد ذاتها؛ وقد تنشأ متطلبات مستقلة من التشريع أو العقد أو نطاق التطبيق.','استعراض الإطار القانوني','معلومات عامة. يجب تقييم النطاق والقطاع والحدود والأحكام الانتقالية لكل جهة. النص الرسمي هو المرجع.','لا توجد سجلات مراجعة منشورة لهذه اللغة والولاية القانونية.','الرئيسية','تاريخ النفاذ / التطبيق','تغيير الدولة مع الاحتفاظ باللغة','يغير اختيار الدولة المعلومات القانونية المعروضة ولا يغير القانون الحاكم للعقد أو وثائق خصوصية مقدم الخدمة.']}
GUIDANCE_STATUS = {'tr':'Yayımlanmış rehber','en':'Published guidance','fr':'Recommandations publiées','es':'Guía publicada','ja':'公表済みガイドライン','zh-CN':'已发布指南','vi':'Hướng dẫn đã công bố','ar':'دليل إرشادي منشور'}
KEYS = ('eyebrow','heading','country','source','verified','active','upcoming','draft','repealed','impact','scope','audit','standards','standards_note','explore','disclaimer','empty','home','effective','country_hint','provider_note')

def get_regulations(country, language, category=None):
    from .models import LegalRegulation
    try:
        records = {obj.pk:{field.name:getattr(obj,field.name) for field in obj._meta.fields}
                   for obj in LegalRegulation.objects.filter(country_code=country)}
    except (OperationalError, ProgrammingError):
        # An editorial withdrawal must never resurrect a bundled seed record.
        return []
    result=[]
    for record in records.values():
        copy=record['translations'].get(language)
        if not copy or not record['published'] or record['review_state']!='verified' or not record['last_verified_at'] or record['status']=='repealed':
            continue
        if category and record['category'] != category: continue
        effective=str(record.get('effective_date') or '')
        if record['status']=='active' and effective and effective > date.today().isoformat():
            record['status']='upcoming'
        record.update(copy)
        record['last_verified_at']=str(record['last_verified_at'])
        record['effective_date']=effective
        result.append(record)
    return sorted(result,key=lambda r:(r['category']=='guidance',r['status']!='active',r['id']))

HEADLINES = {
'TR':'Türkiye’de Başkanlık seviyesinde görülen milli güvenlik meselesi.',
'US':'U.S. disclosure requirements put cyber risk on the board’s agenda.',
'GB':'UK rules connect data protection, service security and accountability.',
'EU':'EU requirements depend on sector, role and national implementation.',
'FR':'En France, les obligations dépendent du périmètre et des textes applicables.',
'BE':'En Belgique, NIS2 renforce les responsabilités des entités concernées.',
'ES':'En España, la protección de datos y la seguridad tienen marcos propios.',
'CL':'En Chile, la ciberseguridad es una responsabilidad regulada para las entidades comprendidas.',
'MX':'En México, los regímenes de datos personales distinguen al sector público y al privado.',
'AR':'En Argentina, los datos personales exigen controles y responsabilidad.',
'JP':'日本では、適用法令に応じた安全管理と経営の関与が求められます。',
'CN':'在中国，网络安全和数据保护义务取决于主体、业务与适用范围。',
'VN':'Tại Việt Nam, trách nhiệm về an ninh mạng và dữ liệu được xác định theo phạm vi áp dụng.',
'SA':'في السعودية تتحدد المسؤوليات وفق نطاق الأنظمة والضوابط المطبقة.'}
INTRO = {
'en':'Laws differ across jurisdictions. Organizations within scope must identify obligations, document risk, test controls and maintain evidence. The selected country determines the legal framework shown below.',
'fr':'Les lois diffèrent selon les pays. Les organisations concernées doivent identifier leurs obligations, documenter les risques, tester les contrôles et conserver les preuves. Le pays sélectionné détermine le cadre présenté ci-dessous.',
'es':'Las leyes varían según el país. Las organizaciones comprendidas deben identificar sus obligaciones, documentar riesgos, probar controles y conservar evidencias. El país seleccionado determina el marco que se muestra a continuación.',
'ja':'法制度は国・地域によって異なります。対象となる組織は義務を特定し、リスクの文書化、統制テストと証拠の管理を行う必要があります。以下には選択した法域の制度を表示します。',
'zh-CN':'不同法域的法律要求各不相同。适用范围内的组织应识别义务、记录风险、测试控制并保存证据。以下内容依据所选国家或法域显示。',
'vi':'Quy định khác nhau giữa các quốc gia. Tổ chức thuộc phạm vi áp dụng cần xác định nghĩa vụ, ghi nhận rủi ro, kiểm thử kiểm soát và lưu giữ bằng chứng. Quốc gia được chọn quyết định khung pháp lý hiển thị bên dưới.',
'ar':'تختلف القوانين بين الدول. على الجهات المشمولة تحديد التزاماتها وتوثيق المخاطر واختبار الضوابط وحفظ الأدلة. تحدد الدولة المختارة الإطار القانوني المعروض أدناه.'}
INTRO['tr'] = "Her ülkede aynı kanun yok. Fakat Türkiye, Avrupa Birliği ve ABD'de yakın tarihlerde devreye giren düzenlemeler aynı yönü gösteriyor: kurumlar riski belgelemek, kontrolleri sınamak, olayları raporlamak ve teknoloji tedarikçilerini yönetmek zorunda."

def context(request, detailed=False):
    language,country=preference(request)
    ui=dict(zip(KEYS,UI[language]))
    records=get_regulations(country,language)
    for record in records: record['status_label']=GUIDANCE_STATUS[language] if record['category']=='guidance' else ui[record['status']]
    return {'legal_language':language,'legal_country':country,'legal_country_name':COUNTRY_NAMES[country],
            'legal_ui':ui,'legal_headline':HEADLINES[country],'legal_intro':INTRO[language],
            'legal_show_outcome':request.path in ('/','/kariyer-pusulasi/'),'legal_records':records,'legal_detailed':detailed,
            'legal_countries':[{'code':c,'name':COUNTRY_NAMES[c]} for c in LANGUAGE_COUNTRIES[language]],
            'legal_direction':'rtl' if language=='ar' else 'ltr',
            'legal_schema':json.dumps({'@context':'https://schema.org','@type':'ItemList',
                'name':ui['eyebrow']+' · '+COUNTRY_NAMES[country], 'inLanguage':language,
                'itemListElement':[{'@type':'ListItem','position':index+1,'item':{'@type':'CreativeWork',
                    'name':row['official_name'],'url':row['official_source_url'],'dateModified':row['last_verified_at'],
                    'inLanguage':language}} for index,row in enumerate(records)]},ensure_ascii=False).replace('<','\\u003c')}
