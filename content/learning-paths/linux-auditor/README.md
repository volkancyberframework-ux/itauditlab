# Linux: Denetçi Gözüyle

80 özgün Türkçe soru; beş bölümde 16 soru. 32 başlangıç, 32 orta, 16 ileri. 52 görsel karar, 12 çoktan seçmeli, 16 senaryo; her soruda ayrı 2560×1440 sentetik terminal PNG'si, ipucu, cevap ve açıklama bulunur. Gerçek sunucu verisi veya gerçek kimlik bilgisi kullanılmaz. Görseller cevap metni değil, yorumlanması gereken sistem kanıtıdır.

Bölümler: temel Linux/kanıt okuma; hesaplar ve ayrıcalıklar; izinler/ACL/güvenlik sınırları; servisler/SSH/ağ/yama; loglar ve uçtan uca denetim. Ubuntu/OpenSSH/systemd örnekleri her Linux dağıtımında aynı dosya yolları veya davranış garantisi değildir. Çıktılar kurgusal eğitim örnekleridir; üretim üzerinde komut çalıştırılması beklenmez.

Mevcut AD yolu korunur. Linux yolu premium, published ve owner=None olduğu için mevcut ve gelecekteki ücretli üyelerin native ve web listesinde görünür. Migration ayrıca mevcut aktif ücretli kullanıcılar için boş ilerleme kaydı oluşturur; eski ilerleme, cevap ve XP korunur. Oturumlar 16 soru ile bölüm sınırında ilerler ve yarım kalan oturum devam ettirilir. Görseller mevcut yetkili API ve PrivateVoiceStorage ile sunulur; herkese açık media URL'si yoktur.

```sh
python content/learning-paths/linux-auditor/build_content.py
python content/learning-paths/linux-auditor/render_evidence.py
python manage.py seed_linux_auditor_path
python manage.py seed_linux_auditor_path --apply
```

Import digest ve external_id registry ile tekrar güvenlidir; yönetici tarafından değiştirilmiş içerik üzerine yazmaz. 0036 migration yayını ve mevcut ücretli kullanıcılara atamayı yapar. Ters migration yalnız yayını kapatır; cevap/ilerleme silmez.

Teknik kaynaklar (29 Ekim 2026):
- https://www.man7.org/linux/man-pages/man1/chmod.1.html
- https://www.man7.org/linux/man-pages/man5/sshd_config.5.html
- https://www.freedesktop.org/software/systemd/man/latest/journalctl.html

Kontroller: 80 sorunun API ile cevaplanması, 80 yetkili PNG checksum kontrolü, bölüm sınırları, devam etme, tekrar yanıtta XP çoğalmaması, ücretsiz erişim reddi, web oturumu, import idempotency ve ücretli kullanıcı ataması.
