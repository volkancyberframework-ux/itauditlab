from django.conf import settings
from django.core import signing
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_POST

CONSENT_COOKIE = 'grc_consent'
CONSENT_VERSION = '2026-10-11'
CONSENT_AGE = 60 * 60 * 24 * 180


def analytics_allowed(request):
    try:
        value = signing.loads(request.COOKIES.get(CONSENT_COOKIE, ''), salt='grc-cookie-consent', max_age=CONSENT_AGE)
        return value.get('version') == CONSENT_VERSION and value.get('analytics') is True
    except (signing.BadSignature, AttributeError, TypeError):
        return False


@require_POST
def cookie_consent(request):
    choice = request.POST.get('analytics')
    if choice not in ('true', 'false'):
        return JsonResponse({'ok': False}, status=400)
    response = JsonResponse({'ok': True, 'analytics': choice == 'true', 'version': CONSENT_VERSION})
    response.set_cookie(CONSENT_COOKIE, signing.dumps({'version': CONSENT_VERSION, 'analytics': choice == 'true'}, salt='grc-cookie-consent'), max_age=CONSENT_AGE, secure=not settings.DEBUG, httponly=True, samesite='Lax')
    if choice == 'false':
        response.delete_cookie('grc_vid', samesite='Lax')
    return response


DOCUMENTS = {
'gizlilik': ('Gizlilik Politikası', [
('Kapsam ve iletişim', 'Bu politika grcustasi.com üzerindeki eğitim, kariyer pusulası, kurumsal talep, partnerlik, bülten ve bekleme listesi hizmetlerini kapsar. İletişim ve kişisel veri başvuruları: volkan@grcustasi.com.'),
('Hangi bilgiler işlenir?', 'Kullandığınız forma göre ad soyad, e-posta, telefon/WhatsApp, şirket, pozisyon, LinkedIn adresi, talep metni ve kariyer değerlendirme yanıtları işlenir. Hesap hizmetlerinde kimlik doğrulama ve eğitim ilerleme bilgileri; ödemelerde işlem ve üyelik bilgileri işlenir. Kart bilgileri ödeme sağlayıcısının ekranında alınır; site kart numaranızı saklamaz. Sunucu güvenlik kayıtlarında IP adresi ve teknik istek bilgileri bulunabilir.'),
('Güvenlik ve saklama', 'Verilere erişim görev ve yetkiyle sınırlandırılır. Bilgiler talebin/hizmetin yürütülmesi, hukuki yükümlülükler ve uyuşmazlıkların çözümü için gerekli süre boyunca saklanır; işleme sebebi sona erdiğinde silinir, yok edilir veya anonimleştirilir. Bülten izninizi geri çekmek veya bekleme listesinden çıkmak için iletişim adresine yazabilirsiniz.'),
('Dış hizmetler', 'Site barındırma için Render, ödemeler için Stripe, eğitim topluluğu için Skool ve operasyonel talep bildirimleri için Telegram kullanır. Seçtiğiniz hizmete göre ilgili sağlayıcıya gerekli bilgiler iletilebilir. WhatsApp, LinkedIn ve diğer dış bağlantıları açtığınızda ilgili hizmetin politikaları geçerlidir. Yurt dışı aktarım şartları KVKK metninde açıklanır.'),
]),
'kvkk': ('KVKK Aydınlatma Metni', [
('Veri sorumlusu ve başvuru', 'Veri sorumlusu Volkan Güler — GRC Ustası’dır. Hizmet Vietnam’dan çevrim içi olarak yönetilir; başvuru ve hizmet verilerine bu ülkeden erişilmesi söz konusu olabilir. Hizmetler kapsamında kişisel veri işleme süreçleri hakkında bilgi almak ve haklarınızı kullanmak için volkan@grcustasi.com adresine başvurabilirsiniz. Başvurunuzda adınızı, talebinizi ve size yanıt verilebilecek iletişim bilgilerini belirtin. Kimlik doğrulaması için yalnızca gerekli ek bilgiler istenebilir.'),
('Toplama yöntemi, amaç ve hukuki sebepler', 'Veriler web formları, hesap işlemleri, ödeme bildirimleri, e-posta ve teknik kayıtlar üzerinden otomatik veya kısmen otomatik yollarla toplanır. Eğitim kaydı, hesap yönetimi, ödeme ve talep edilen teklif/görüşme süreçleri KVKK m.5/2(c) kapsamında sözleşmenin kurulması veya ifası; kanuni muhasebe ve benzeri yükümlülükler m.5/2(ç); hakların tesisi, kullanılması ve korunması m.5/2(e); güvenlik ve kötüye kullanımın önlenmesi temel haklarınıza zarar vermemek kaydıyla m.5/2(f) kapsamında işlenir. İsteğe bağlı ziyaretçi analitiği ve bülten pazarlaması için m.5/1 kapsamında ayrı açık rıza alınır. Aydınlatma metnini okumak pazarlama veya analitik izni değildir.'),
('Kariyer pusulası ve başvurular', 'Kariyer pusulasında iletişim bilgileriniz ve yanıtlarınız değerlendirme sonucu oluşturmak ve talebinizi takip etmek için işlenir. Sonuç yönlendirme amaçlıdır; işe alım kararı değildir. Kurumsal ve partnerlik formlarındaki bilgiler görüşme/başvuru sürecini yürütmek için kullanılır. Bültene veya bekleme listesine kayıt yalnızca ilgili duyurular için kullanılır. Özel nitelikli kişisel veri, adli sicil veya üçüncü kişilere ait gizli bilgi göndermeyin.'),
('Alıcılar ve yurt dışı aktarım', 'Hizmetin yürütülmesi için yetkili çalışanlar, barındırma/teknik destek sağlayıcıları, Stripe ödeme altyapısı, seçilen eğitim hizmetinde Skool, operasyonel bildirimlerde Telegram ve yasal talep halinde yetkili kamu kurumları gerekli verileri alabilir. Bu hizmetlerin yurt dışında bulunması veri aktarımına yol açabilir. Yurt dışı aktarım için KVKK m.9 uyarınca uygulanabilir yeterlilik kararı veya uygun güvence gibi geçerli bir aktarım mekanizmasının sağlanması gerekir. Çerez tercihi, yurt dışı aktarımın hukuki dayanağı yerine geçmez.'),
('KVKK m.11 kapsamındaki haklarınız', 'Verinizin işlenip işlenmediğini öğrenme; işlenmişse bilgi talep etme; amacı ve amaca uygun kullanımı öğrenme; yurt içi/yurt dışı alıcıları bilme; eksik veya yanlış verileri düzelttirme; kanuni koşullarda silme/yok etme ve bu işlemlerin alıcılara bildirilmesini isteme; yalnızca otomatik analizle aleyhinize sonuç doğmasına itiraz etme; hukuka aykırı işleme nedeniyle zararın giderilmesini isteme haklarınız vardır. Başvurular en kısa sürede ve en geç 30 gün içinde sonuçlandırılır. Başvuru usulüne uygun olarak yazılı veya kayıtlı e-posta/KEP gibi mevzuatta tanınan yöntemlerle başvurabilirsiniz.'),
]),
'cerez': ('Çerez Politikası', [
('Tercihiniz', 'Zorunlu çerezler hizmetin güvenliği ve çalışması için kullanılır. Analitik çerezleri varsayılan olarak kapalıdır. Kabul et, reddet veya tercihleri kaydet seçeneklerini kullanabilirsiniz. Sayfayı kaydırmak veya kullanmaya devam etmek izin sayılmaz. Çerez ayarları bağlantısından izninizi her zaman değiştirebilirsiniz.'),
('Zorunlu çerezler', 'csrftoken: form güvenliği; varsayılan süre 1 yıl. sessionid: giriş ve oturum işlemleri; varsayılan süre 14 gün. grc_consent: tercih ve politika sürümünü tutar; süre 180 gün. Bunlar birinci taraf çerezleridir. Oturum çerezi yalnızca oturum gerektiren işlemlerde oluşturulur.'),
('İsteğe bağlı analitik', 'grc_vid: birinci taraf ziyaretçi ölçüm çerezi; yalnızca analitik izninden sonra oluşturulur, süre 2 yıl. Rastgele ziyaretçi kimliği kullanılır; veritabanında özetlenmiş kimlik ve ziyaret tarihleri tutulur. İzin geri alındığında çerez silinir ve yeni analitik kayıt yapılmaz. Önceden işlenen verilerle ilgili haklarınızı KVKK iletişim adresinden kullanabilirsiniz.'),
('Tarayıcı depolaması ve dış hizmetler', 'grc-theme tema seçiminizi; grc-newsletter-seen-v1 bülten penceresini kapatma tercihinizi; grc-cookie-choice-v1 çerez seçiminizin yerel gösterimini tutar. Tarayıcı verilerini temizleyene kadar veya çerez tercihi için 180 gün saklanır. Bunlar reklam takibi için kullanılmaz. Stripe/Skool gibi dış hizmetlere geçtiğinizde o hizmetin çerez politikası uygulanır.'),
]),
'kullanim': ('Kullanım ve Tüketici Bilgilendirmesi', [
('Hizmet kapsamı', 'GRC Ustası eğitim, kariyer desteği ve kurumsal danışmanlık sunar. Program içeriği, süre ve bedel ilgili ürün sayfasında gösterilir. İşe yerleşme, gelir, sınav başarısı, vize veya bağımsız sertifikasyon garantisi verilmez. İçerikler izinsiz çoğaltılamaz; laboratuvar çalışmaları yalnızca yetkili ve hukuka uygun ortamlarda yapılmalıdır.'),
('Ödeme öncesi bilgiler', 'Satın almadan önce hizmet sağlayıcının resmi kimlik ve adresi, hizmetin kapsamı, toplam bedel ve vergiler, ifa tarihi, cayma/iptal koşulları ile uyuşmazlık başvuru yolları size sunulmalıdır. Bu sayfa, ürüne ve siparişe özel ön bilgilendirme formu veya mesafeli sözleşmenin yerine geçmez. Sorularınız için volkan@grcustasi.com adresine yazabilirsiniz.'),
('Cayma, iptal ve iade', 'Tüketici işlemlerinde 6502 sayılı Kanun ve Mesafeli Sözleşmeler Yönetmeliği kapsamındaki emredici haklarınız saklıdır. Uygulanabilir işlemlerde hizmet sözleşmesinin kurulmasından itibaren 14 günlük cayma hakkı bulunur. Dijital içerik veya erken ifa gibi istisnalar yalnızca mevzuattaki şartlar ve gerekli ön bilgilendirme/onay sağlandığında uygulanabilir. Genel bir “hiçbir koşulda iade yok” kaydı kanuni haklarınızı ortadan kaldırmaz. Cayma veya iade talebinizi iletişim adresimize iletebilirsiniz.'),
('Uyuşmazlıklar', 'Tüketiciler, güncel parasal sınır ve görev kurallarına göre tüketici hakem heyetlerine veya tüketici mahkemelerine başvurabilir. Mevzuatın gerektirdiği hallerde dava öncesi arabuluculuk uygulanır.'),
]),
}


def document(request, slug):
    if slug not in DOCUMENTS:
        raise Http404
    title, sections = DOCUMENTS[slug]
    return render(request, 'landing/legal.html', {'title': title, 'sections': sections, 'version': CONSENT_VERSION})
