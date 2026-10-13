# İç teknik kontrol notu

Kullanıcıya gösterilen cevaplarda referans yoktur. Teknik içerik Microsoft Learn'in AD DS ve Security Auditing belgeleriyle kontrol edilmiştir.

- lastLogon DC'ler arasında replike edilmez; lastLogonTimestamp yaklaşık/replike değerdir. Tek alan kesin son etkinlik veya kullanılmama kanıtı değildir.
- Security grupları yetki vermede kullanılır; distribution grupları aynı işlevi sağlamaz. Domain Admins / Enterprise Admins kapsamı farklıdır. İç içe üyelik etkin erişimle birlikte değerlendirilir.
- Fine-grained parola politikası OU'ya doğrudan uygulanmaz; kullanıcı/global security group ve resultant politika kontrol edilir.
- GPO bağlantısı ve Security Filtering etkin uygulama kanıtının yerine geçmez. Read/Apply, scope, inheritance/enforced ve sonuç ayrı incelenir.
- 4624 başarılı, 4625 başarısız giriş; olayın kaydedildiği host, Subject/Target, Logon Type ve kaynak adres birlikte yorumlanır. Tip 3 ağ girişidir; tek olay saldırı veya zarar kanıtı değildir.
- 4720 oluşturma, 4726 silme, 4728 security-enabled global group üyeliği, 4732 security-enabled local group üyeliği, 4740 kilitlenme, 4768 TGT, 4769 servis bileti, 1102 Security log temizleme. 1102 sağlayıcısı Microsoft-Windows-Eventlog olarak ayrı gösterilir.
- CH-108 onayı Windows olayının doğal alanı değildir; ayrı denetim uzlaştırma ekranında gösterilir. Servis hesabı sahibi ve HR mover kayıtları ADUC'nin uydurma native alanı olarak sunulmaz.

Birincil belgeler:
https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4624
https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4625
https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4728
https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-1102
https://learn.microsoft.com/en-us/windows/win32/adschema/a-lastlogon
https://learn.microsoft.com/en-us/windows/win32/adschema/a-lastlogontimestamp
https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/adac/fine-grained-password-policies
