# Ağ Denetimi

55 özgün görselli ve uygulamalı Türkçe soru; beş bölümde 11 soru: VLAN/ağ kapsamı, firewall, VPN, segmentasyon, ağ logları/denetim sonucu. 22 başlangıç, 22 orta, 11 ileri. Her soruda ayrı 2560×1440 sentetik yapılandırma, politika, trafik yolu veya log kanıtı; doğru yanıt, teknik gerekçe, risk, iş etkisi ve önerilen kontrol bulunur.

Linux ve Veritabanı modüllerinin aynı renk, font, çerçeve, önizleme, tam ekran, zoom/pan, ipucu ve cevap bileşenleri kullanılır. Oturumlar bölüm başına 11 soruyla devam eder. Mobil mevcut yol yüzdesini, web genel yüzde ve bölüm ilerlemesini gösterir. Mevcut akıştaki gibi doğru cevaplanan sorular kalıcı ilerlemeye işlenir; yanlışlar açıklamadan öğrenilip sonraki oturumlarda tekrar çalışılır.

55 görsel gerçek cihaz ekranı değildir. Eğitim için özgün ve sadeleştirilmiş kanıtlardır; gerçek kişi, IP sahibi, anahtar veya müşteri logu kullanılmaz. Dış IP örneklerinde dokümantasyon blokları kullanılır. İlk eşleşme ve mevcut oturum davranışı genel firewall sorularında açıkça kanıt içinde belirtilir; bütün üreticilere aynı varsayılan atfedilmez. Cisco örnekleri IOS XE 17.12, OpenVPN örnekleri 2.6 bağlamındadır; AWS security group/NACL farklılıkları ayrı tutulur. Üretim cihazına bağlanılmaz, gerçek tarama veya yapılandırma değişikliği yapılmaz.

## Yeniden üretme ve yayın

```sh
python content/learning-paths/network-auditor/build_content.py
python content/learning-paths/network-auditor/render_evidence.py
python manage.py seed_network_auditor_path          # dry-run
python manage.py seed_network_auditor_path --apply
python manage.py test mobile_api.test_network_auditor mobile_api.test_database_auditor mobile_api.test_linux_auditor mobile_web.test_ad_web
```

0038 migration içeriği yayınlar ve mevcut aktif ücretli mobil hesaplara boş ilerleme kaydı atar. Ömür boyu, geçerli süreli ve geçerli mağaza üyelikleri mevcut premium erişim kuralıyla kapsanır. Gelecekte ücretli olan kullanıcılar ortak yayın sayesinde otomatik erişir. Digest ve external_id registry tekrar importu güvenli tutar; yönetici değişikliğinin üzerine yazılmaz. Diğer yolların soru, görsel, cevap, ilerleme ve XP kayıtları değiştirilmez. Ters migration yalnız yeni yolu yayından kaldırır, kullanıcı kaydı silmez.

Görseller PrivateVoiceStorage ve mevcut yetkili API üzerinden sunulur. Web resim alternatif metni yalnız yeni ağ sorularında kanıt konusunu içerir. Mevcut yolların bileşen davranışı korunur.

## Teknik inceleme kaynakları (29 Ekim 2026)

- Cisco VLAN trunk/access/DTP/native/allowed VLAN: https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-12/configuration_guide/vlan/b_1712_vlan_9300_cg/configuring_vlan_trunks.html
- OpenVPN 2.6 sertifika kimliği/iptali ve istemci kontrolleri: https://openvpn.net/community-docs/community-articles/openvpn-2-6-manual/
- AWS NACL kural sırası, stateless dönüş ve kapsam: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- AWS security group stateful davranışı ve kaynak kapsamı: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
- AWS Flow Logs kayıt tamlığı, ACCEPT ve SKIPDATA: https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html
- Örnek IPv4 blokları: https://www.rfc-editor.org/rfc/rfc5737.html

Yerel browser QA: `python content/learning-paths/network-auditor/qa/serve_browser_qa.py`, localhost:8767. Mock API ile görsel bileşenleri test eder; grading/progress ayrıca Django API üzerinden uçtan uca doğrulanır. Fiziksel iOS/Android ve gerçek ağ cihazı testi yapılmaz.
