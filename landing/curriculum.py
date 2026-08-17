CURRICULUM = [
    {
        'number': '01', 'title': 'GRC ve Risk Temelleri', 'hours': 10, 'lessons': 14, 'labs': 4, 'cases': 2,
        'summary': 'Risk konuşmadan önce şirketin nasıl düşündüğünü öğren.',
        'topics': ['Governance vs management', 'Asset · threat · vulnerability', 'Inherent & residual risk', 'Likelihood & impact', 'Risk appetite & tolerance', 'Risk response seçenekleri', 'Risk / control / issue owner', '1LoD · 2LoD · 3LoD', 'Preventive · detective · corrective', 'Manual & automated controls', 'Control design & effectiveness', 'Business impact', 'Risk matrix', 'Risk scoring workshop'],
        'lab': 'Hayali fintech şirketinin asset inventory ve risk register’ını oluştur; likelihood/impact puanla.',
        'case': 'Teknik bulguyu yönetim için business risk diline çevir ve ilk risk hikâyeni kazan.',
    },
    {
        'number': '02', 'title': 'Network & İşletim Sistemleri', 'hours': 10, 'lessons': 14, 'labs': 4, 'cases': 2,
        'summary': 'Router yapılandırmak zorunda değilsin; neye baktığını bilmelisin.',
        'topics': ['TCP/IP · LAN · WAN', 'DNS · DHCP · NAT', 'Ports & protocols', 'Firewall · WAF · IDS/IPS', 'Segmentation · VLAN · VPN', 'DMZ · proxy · load balancer', 'Zero Trust temeli', 'Windows Server', 'Linux', 'Users · groups · permissions', 'Services & processes', 'Active Directory · GPO', 'Patch & vulnerability', 'Network diagram okuma'],
        'lab': 'Şirket network diagramında kritik sistemleri, trust boundary’leri ve internet-facing varlıkları bul.',
        'case': '“Firewall açık ama gerçekten risk var mı?” vakasında bağlam ve iş etkisini değerlendir.',
    },
    {
        'number': '03', 'title': 'Cloud & IAM', 'hours': 10, 'lessons': 14, 'labs': 5, 'cases': 2,
        'summary': 'Kim, neye, neden erişebiliyor?',
        'topics': ['IaaS · PaaS · SaaS', 'Shared responsibility', 'EC2 · S3 · RDS · VPC', 'CloudTrail · CloudWatch', 'IAM users · groups · roles', 'Policies & least privilege', 'Root · MFA · privileged access', 'Joiner · Mover · Leaver', 'Provisioning & deprovisioning', 'Access review & SoD', 'Service accounts · secrets', 'PAM · RBAC · ABAC', 'Encryption & key management', 'Cloud evidence'],
        'lab': 'Kontrollü AWS ortamında policy oku, excessive permission, inactive user ve MFA istisnası bul.',
        'case': 'Eski çalışanın aktif hesabını teknik açık değil, governance problemi olarak savun.',
    },
    {
        'number': '04', 'title': 'IT Audit & Controls', 'hours': 10, 'lessons': 14, 'labs': 5, 'cases': 3,
        'summary': 'Bir kontrolün var olması ile çalışması aynı şey değildir.',
        'topics': ['Audit lifecycle & universe', 'Risk-based planning', 'Scope & objective', 'Walkthrough & interview', 'Evidence reliability', 'Population & sampling', 'Design assessment', 'Operating effectiveness', 'Inquiry · observation · inspection', 'Reperformance', 'Working papers & audit trail', 'Exception & finding', 'Root cause · 5 Why', 'Report & remediation'],
        'lab': 'Policy, user list, screenshots, export, e-posta ve ticket kanıtlarını test dosyasına dönüştür.',
        'case': 'Management ile anlaşmazlık yaşanan bulguyu kanıt ve risk diliyle savun.',
    },
    {
        'number': '05', 'title': 'ISO 27001 & CISA', 'hours': 10, 'lessons': 14, 'labs': 4, 'cases': 2,
        'summary': 'Sertifikayı ezberleme; standardın neden var olduğunu anla.',
        'topics': ['ISMS scope & context', 'Interested parties', 'Leadership', 'Risk assessment & treatment', 'Statement of Applicability', 'Internal audit', 'Management review', 'Corrective actions', 'Annex A control grupları', 'Control mapping', 'Audit evidence', 'Major / minor uygunsuzluk', 'CISA domainleri', 'Auditor mindset & best answer'],
        'lab': 'Küçük SaaS şirketi için ISO 27001 gap assessment ve yönetim özeti hazırla.',
        'case': 'Önce risk mi kontrol mü? Auditor ne yapar ve nerede durur?',
    },
    {
        'number': '06', 'title': 'Cybersecurity GRC', 'hours': 10, 'lessons': 14, 'labs': 4, 'cases': 3,
        'summary': 'Teknik olayların arkasındaki governance problemini gör.',
        'topics': ['NIST CSF · CIS · COBIT', 'Framework mapping', 'Vulnerability governance', 'Incident response', 'SOC · SIEM · logging', 'EDR · DLP · encryption', 'Backup & disaster recovery', 'BCP · RTO · RPO', 'Third-party risk', 'Vendor due diligence', 'SOC 1 / SOC 2', 'Pentest raporu okuma', 'KPI · KRI', 'Board reporting'],
        'lab': 'Ransomware vakasında her yeni evidence ile risk değerlendirmesini güncelle.',
        'case': 'Backup var; restore testi 14 aydır yok. Tasarım ile etkinliği ayır.',
    },
    {
        'number': '07', 'title': 'AWS Lab & Case Studies', 'hours': 10, 'lessons': 10, 'labs': 10, 'cases': 10,
        'summary': 'Burada artık ders değil, iş başlıyor.', 'featured': True,
        'topics': ['IAM review', 'CloudTrail review', 'S3 security', 'Public exposure', 'Encryption controls', 'Security groups', 'Backup configuration', 'Evidence standards', 'Working paper', 'Finding & recommendation', 'Management response', 'Remediation validation'],
        'lab': 'Former employee, public bucket, disabled CloudTrail, MFA exception ve excessive admin vakalarını yürüt.',
        'case': 'Her vakayı risk → control → evidence → finding → STAR mülakat hikâyesine dönüştür.',
    },
    {
        'number': '08', 'title': 'Teknik İngilizce & Kariyer', 'hours': 10, 'lessons': 14, 'labs': 4, 'cases': 2,
        'summary': 'Bilmek yetmez; bildiğini anlatabilmelisin.',
        'topics': ['Audit & GRC vocabulary', 'Evidence request e-mail', 'Finding writing', 'Opening / closing meeting', 'Risk discussion', 'Challenging stakeholders', 'Executive communication', 'GRC & Audit CV', 'LinkedIn optimization', 'STAR method', 'Behavioural interview', 'Technical interview', 'Mock interview', 'CISA & ISO roadmap'],
        'lab': 'Bootcamp vakalarını CV’ye doğru aktar; evidence isteği ve finding metni yaz.',
        'case': 'IAM, cloud ve risk hikâyelerini mock interview’da savun.',
    },
]

CURRICULUM_STATS = {'hours': 80, 'modules': 8, 'labs': 40, 'cases': 10, 'portfolio': 1}
