from django.db import models
class AssessmentSession(models.Model):
    PROFILE_CHOICES = [('student', 'Üniversite öğrencisi'), ('graduate', 'Yeni mezun'), ('working', 'Çalışıyor')]
    email = models.EmailField('E-posta', unique=True)
    profile_type = models.CharField('Profil', max_length=20, choices=PROFILE_CHOICES)
    answers = models.JSONField('Anket cevapları', default=dict, blank=True)
    discount_percent = models.PositiveSmallIntegerField('İndirim oranı', default=15)
    discount_expires_at = models.DateTimeField('İndirim son tarihi')
    completed = models.BooleanField('Tamamlandı', default=False)
    created_at = models.DateTimeField('Başlangıç', auto_now_add=True)
    updated_at = models.DateTimeField('Son hareket', auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Kariyer pusulası kaydı'
        verbose_name_plural = 'Kariyer pusulası kayıtları'

    @staticmethod
    def discount_for(profile_type):
        return {'student': 50, 'graduate': 25, 'working': 15}.get(profile_type, 15)

    def __str__(self): return f'{self.email} — %{self.discount_percent}'


class Lead(models.Model):
    PROFILE_CHOICES = [('student', 'Üniversite öğrencisi'), ('graduate', 'Yeni mezun'), ('working', 'Çalışıyor')]
    RESULT_CHOICES = [('strong', 'Güçlü Uyum'), ('develop', 'Uygun — Bazı Alanları Güçlendir'), ('wait', 'Şimdilik Bekle')]
    RESIDENCE_CHOICES = [('turkey', 'Türkiye'), ('abroad', 'Yurtdışı')]
    REGION_CHOICES = [('europe', 'Avrupa'), ('usa', 'ABD / Kuzey Amerika'), ('south_america', 'Güney Amerika'), ('asia', 'Asya'), ('australia', 'Avustralya / Okyanusya')]
    name = models.CharField('Ad', max_length=120)
    email = models.EmailField('E-posta', unique=True)
    whatsapp = models.CharField('WhatsApp', max_length=30, blank=True)
    profile_type = models.CharField('Profil', max_length=20, choices=PROFILE_CHOICES)
    english_awareness = models.BooleanField('İngilizce farkındalığı', default=False)
    weekly_time = models.BooleanField('Haftalık zaman ayırabilir', default=False)
    age_over_45 = models.BooleanField('45 yaş üzeri', default=False)
    existing_it_experience = models.BooleanField('İlgili tecrübe', default=False)
    eligibility_awareness = models.BooleanField('Rol uygunluğu farkındalığı', default=False)
    career_clarity = models.BooleanField('Kariyer hedefi net', default=False)
    opportunity_awareness = models.BooleanField('İş fırsatları farkındalığı', default=False)
    effort_awareness = models.BooleanField('Çalışma yoğunluğu farkındalığı', default=False)
    ethics_commitment = models.BooleanField('Etik kullanım taahhüdü', default=False)
    residence_type = models.CharField('Yaşanılan yer', max_length=12, choices=RESIDENCE_CHOICES, blank=True)
    region = models.CharField('Yurtdışı bölgesi', max_length=20, choices=REGION_CHOICES, blank=True)
    test_score = models.PositiveSmallIntegerField('Test puanı', default=0)
    result_type = models.CharField('Sonuç', max_length=20, choices=RESULT_CHOICES)
    student_discount_eligible = models.BooleanField('Öğrenci avantajı', default=False)
    discount_percent = models.PositiveSmallIntegerField('İndirim oranı', default=15)
    discount_expires_at = models.DateTimeField('İndirim son tarihi', null=True, blank=True)
    consent = models.BooleanField('İletişim izni', default=False)
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lead'
        verbose_name_plural = 'Leadler'

    def __str__(self): return f'{self.name} — {self.email}'


class WaitingList(models.Model):
    name = models.CharField('Ad', max_length=120)
    email = models.EmailField('E-posta', unique=True)
    whatsapp = models.CharField('WhatsApp', max_length=30, blank=True)
    consent = models.BooleanField('İletişim izni', default=False)
    created_at = models.DateTimeField('Oluşturulma', auto_now_add=True)
    class Meta:
        ordering = ['-created_at']; verbose_name = 'Bekleme listesi kaydı'; verbose_name_plural = 'Bekleme listesi'
    def __str__(self): return self.email


class JobMarketCount(models.Model):
    country = models.CharField('Ülke', max_length=60, unique=True)
    flag = models.CharField('Bayrak', max_length=8, blank=True)
    grc = models.PositiveIntegerField(default=0)
    it_audit = models.PositiveIntegerField('IT Audit', default=0)
    it_risk = models.PositiveIntegerField('IT Risk', default=0)
    it_controls = models.PositiveIntegerField('IT Controls', default=0)
    compliance = models.PositiveIntegerField(default=0)
    cyber_risk = models.PositiveIntegerField('Cyber Risk', default=0)
    search_url = models.URLField('Arama bağlantısı', blank=True)
    source_label = models.CharField('Veri kaynağı', max_length=80, default='Manuel veri')
    last_checked_at = models.DateTimeField('Son kontrol', null=True, blank=True)
    last_error = models.CharField('Son hata', max_length=240, blank=True)
    is_demo = models.BooleanField('Demo veri', default=True)
    updated_at = models.DateTimeField('Güncelleme', auto_now=True)
    class Meta:
        verbose_name = 'İş piyasası verisi'
        verbose_name_plural = 'İş piyasası verileri'
        ordering = ['id']

    @property
    def display_count(self):
        if self.country == 'Türkiye' and self.grc >= 99:
            return '99+'
        return f'{self.grc:,}'.replace(',', '.')

    @property
    def is_fresh(self):
        if not self.last_checked_at or self.is_demo:
            return False
        from django.utils import timezone
        return self.last_checked_at >= timezone.now() - timezone.timedelta(hours=36)
    def __str__(self): return self.country


class Certificate(models.Model):
    STATUS = [('valid', 'Geçerli'), ('expired', 'Süresi dolmuş'), ('revoked', 'İptal')]
    certificate_id = models.CharField('Sertifika ID', max_length=60, unique=True)
    participant_name = models.CharField('Katılımcı', max_length=120)
    issue_date = models.DateField('Veriliş tarihi')
    expiry_date = models.DateField('Son geçerlilik', null=True, blank=True)
    status = models.CharField('Durum', max_length=12, choices=STATUS, default='valid')
    class Meta: verbose_name = 'Sertifika'; verbose_name_plural = 'Sertifikalar'
    def __str__(self): return self.certificate_id


class SiteSetting(models.Model):
    bootcamp_price = models.PositiveIntegerField('Bootcamp fiyatı', default=59999)
    payment_url = models.URLField('Ödeme URL', blank=True)
    program_start_date = models.CharField('Program başlangıcı', max_length=80, default='Yakında')
    seats_remaining = models.PositiveSmallIntegerField('Kalan kontenjan', default=12)
    student_discount = models.PositiveSmallIntegerField('Öğrenci indirimi (%)', default=50)
    potential_customer_count = models.PositiveIntegerField('Potansiyel kurum', default=490000)
    certificate_validity = models.CharField('Sertifika geçerliliği', max_length=100, default='Admin tarafından belirlenir')
    minimum_coe = models.CharField('Minimum eğitim kredisi', max_length=40, default='30 COE')
    youtube_url = models.URLField('Ücretsiz ders URL', blank=True)
    linkedin_url = models.URLField('LinkedIn URL', blank=True)
    whatsapp_url = models.URLField('WhatsApp URL', blank=True)
    contact_email = models.EmailField('İletişim e-postası', default='info@grcmastery.com')
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = 'Site ayarı'; verbose_name_plural = 'Site ayarları'
    def __str__(self): return 'GRC Ustası site ayarları'

    @property
    def bootcamp_price_display(self):
        return f'{self.bootcamp_price:,}'.replace(',', '.')

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
