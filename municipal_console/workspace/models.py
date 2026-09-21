from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

def default_due_date():
    return timezone.localdate()+timedelta(days=30)

ROLES = [('admin','Platform yöneticisi'),('executive','Kurum yöneticisi'),('it','BT sorumlusu'),('auditor','Denetçi'),('intern','Stajyer')]
STATUSES = [('implemented','Yapılıyor'),('partial','Kısmen yapılıyor'),('missing','Yapılmıyor'),('na','Uygulanamaz'),('unanswered','Başlanmadı')]
ASSESSMENTS = [('compliant','Uygun'),('partial','Kısmen uygun'),('noncompliant','Uygun değil'),('pending','İnceleme bekliyor')]
DEFICIENCIES = [('design','Tasarım'),('implementation','Uygulama'),('both','Tasarım ve uygulama')]

class Legislation(models.Model):
    code = models.CharField('Kanun / düzenleme kodu', max_length=80, unique=True)
    title = models.CharField('Adı', max_length=250)
    source_url = models.URLField('Resmî kaynak', blank=True)
    class Meta:
        ordering = ['code']
        verbose_name = 'Kanun / düzenleme'
        verbose_name_plural = 'Kanunlar / düzenlemeler'
    def __str__(self):return f'{self.code} · {self.title}'

class LegalArticle(models.Model):
    legislation = models.ForeignKey(Legislation, on_delete=models.PROTECT, related_name='articles', verbose_name='Kanun / düzenleme')
    number = models.CharField('Madde / fıkra', max_length=80)
    text = models.TextField('Madde metni')
    class Meta:
        ordering = ['legislation__code', 'number']
        verbose_name = 'Mevzuat maddesi'
        verbose_name_plural = 'Mevzuat maddeleri'
        constraints = [models.UniqueConstraint(fields=['legislation', 'number'], name='unique_legal_article')]
    def __str__(self):return f'{self.legislation.code} · Madde {self.number}'

class ControlDefinition(models.Model):
    legal_articles=models.ManyToManyField(LegalArticle, blank=True, related_name="catalog_controls", verbose_name="Kanun / madde referansları")
    code=models.CharField(max_length=30,unique=True)
    title=models.CharField(max_length=180)
    description=models.TextField()
    evidence_guidance=models.TextField(verbose_name='Beklenen kanıtlar / test rehberi')
    framework=models.CharField(max_length=60)
    theme=models.CharField(max_length=80)
    risk=models.CharField(max_length=10,choices=[('high','Yüksek'),('medium','Orta'),('low','Düşük')])
    intern_visible=models.BooleanField(default=False)
    class Meta:
        ordering=['code']
        verbose_name='Kontrol kataloğu kaydı'
        verbose_name_plural='Kontrol kataloğu'
    def __str__(self):return f'{self.code} · {self.title}'

class AuditTemplate(models.Model):
    name=models.CharField(max_length=180,unique=True)
    description=models.TextField(blank=True)
    controls=models.ManyToManyField(ControlDefinition,blank=True,verbose_name='Hazır kontroller')
    class Meta:
        verbose_name='Denetim şablonu'
        verbose_name_plural='Denetim şablonları'
    def __str__(self):return self.name

class Organization(models.Model):
    name=models.CharField(max_length=180)
    slug=models.SlugField(unique=True)
    subdomain=models.SlugField(max_length=63,unique=True,null=True,blank=True,help_text='Örnek: torbalibld. DNS/Render alan adı ayrıca yapılandırılmalıdır.')
    logo_data=models.BinaryField(blank=True,default=bytes,editable=False)
    def __str__(self):return self.name
class Audit(models.Model):
    template=models.ForeignKey(AuditTemplate,on_delete=models.PROTECT,null=True,blank=True,verbose_name='Hazır denetim şablonu')
    organization=models.ForeignKey(Organization,on_delete=models.PROTECT)
    title=models.CharField(max_length=180)
    is_demo=models.BooleanField(default=False)
    archived=models.BooleanField(default=False)
    phase=models.CharField(max_length=20,default='responses',choices=[('responses','BT yanıtları'),('fieldwork','Saha denetimi'),('remediation','Bulgu giderme'),('completed','Sürekli kontrol')])
    appointment_at=models.DateTimeField(null=True,blank=True)
    appointment_status=models.CharField(max_length=20,default='none',choices=[('none','Planlanmadı'),('proposed','BT onayı bekleniyor'),('counter','Denetim ekibi onayı bekleniyor'),('confirmed','Onaylandı')])
    appointment_note=models.TextField(blank=True)
    def __str__(self):return self.title
    def save(self,*args,**kwargs):
        from django.db import transaction
        with transaction.atomic():
            previous=type(self).objects.filter(pk=self.pk).values_list('template_id',flat=True).first() if self.pk else None
            super().save(*args,**kwargs)
            if self.template_id and self.template_id!=previous:
                from .services import add_catalog_controls
                add_catalog_controls(self,self.template.controls.all())
class Membership(models.Model):
    auditor_readonly=models.BooleanField(default=False,verbose_name='Stajyer denetçi görünümü (salt okunur)',help_text='Stajyer bu denetimde tüm denetçi verilerini görebilir; hiçbir kayıt değiştiremez.')
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    audit=models.ForeignKey(Audit,on_delete=models.CASCADE)
    role=models.CharField(max_length=20,choices=ROLES[1:])
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','audit'],name='one_membership_per_audit')]
class Control(models.Model):
    legal_articles=models.ManyToManyField(LegalArticle, blank=True, related_name="audit_controls", verbose_name="Kanun / madde referansları")
    source=models.ForeignKey(ControlDefinition,on_delete=models.SET_NULL,null=True,blank=True,related_name='audit_controls')
    audit=models.ForeignKey(Audit,on_delete=models.PROTECT,related_name='controls')
    code=models.CharField(max_length=30)
    title=models.CharField(max_length=180)
    description=models.TextField()
    evidence_guidance=models.TextField(verbose_name='Beklenen kanıtlar / test rehberi',help_text='İstenecek belge, ekran görüntüsü, kayıt ve test adımlarını yazın.')
    framework=models.CharField(max_length=60)
    theme=models.CharField(max_length=80)
    risk=models.CharField(max_length=10,choices=[('high','Yüksek'),('medium','Orta'),('low','Düşük')])
    intern_visible=models.BooleanField(default=False)
    class Meta:
        ordering=['code']
        constraints=[models.UniqueConstraint(fields=['audit','code'],name='unique_audit_control_code'),models.UniqueConstraint(fields=['audit','source'],name='unique_audit_catalog_control')]
class ResponseRevision(models.Model):
    control=models.ForeignKey(Control,on_delete=models.PROTECT,related_name='revisions')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    status=models.CharField(max_length=20,choices=STATUSES)
    explanation=models.TextField()
    declaration=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at','-pk']
    def save(self,*args,**kwargs):
        if self.pk:raise ValueError('Yanıt geçmişi değiştirilemez.')
        return super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValueError('Yanıt geçmişi silinemez.')
class Evaluation(models.Model):
    deficiency=models.CharField(max_length=20,choices=DEFICIENCIES,blank=True,default='',verbose_name='Eksiklik türü')
    control=models.OneToOneField(Control,on_delete=models.PROTECT,related_name='evaluation')
    assessment=models.CharField(max_length=20,choices=ASSESSMENTS)
    rationale=models.TextField()
    private_note=models.TextField(blank=True)
    customer_visible=models.BooleanField(default=True)
    verified=models.BooleanField(default=False,verbose_name='Test edildi ve son onay verildi')
    updated_at=models.DateTimeField(auto_now=True)
class Finding(models.Model):
    audit=models.ForeignKey(Audit,on_delete=models.PROTECT,related_name='findings')
    title=models.CharField(max_length=180)
    recommendation=models.TextField()
    severity=models.CharField(max_length=10,choices=[('high','Yüksek'),('medium','Orta')])
    customer_visible=models.BooleanField(default=True)

    control=models.OneToOneField(Control,on_delete=models.PROTECT,null=True,blank=True,related_name='finding')
    status=models.CharField(max_length=25,default='open',choices=[('open','Açık'),('remediation_submitted','Giderim incelemede'),('disputed','İtiraz incelemede'),('closed','Kapatıldı'),('risk_accepted','Risk kabul edildi')])
    due_date=models.DateField(default=default_due_date,verbose_name='Giderilme son tarihi')
    treatment=models.CharField(max_length=20,default='undecided',choices=[('undecided','Karar bekliyor'),('acknowledged','Bulgu kabul edildi'),('mitigate','Risk giderilecek'),('risk_requested','Risk kabulü onay bekliyor'),('risk_accepted','Risk kabul edildi')])
    @property
    def is_terminal(self):return self.status in ('closed','risk_accepted')
    @property
    def overdue(self):return not self.is_terminal and self.due_date<timezone.localdate()
    created_at=models.DateTimeField(default=timezone.now,editable=False)
    updated_at=models.DateTimeField(auto_now=True)

class FindingUpdate(models.Model):
    finding=models.ForeignKey(Finding,on_delete=models.PROTECT,related_name='updates')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    role=models.CharField(max_length=20)
    action=models.CharField(max_length=30,choices=[('remediate','Giderim bildirimi'),('dispute','İtiraz'),('close','Kapanış onayı'),('reopen','Tekrar açıldı'),('reject','İtiraz/giderim reddi'),('acknowledge','Bulgu kabul edildi'),('plan','Risk giderilecek'),('request_risk','Risk kabulü talebi'),('accept_risk','Yönetici risk kabul onayı'),('set_due','Son tarih değişti')])
    explanation=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at','-pk']

class Suggestion(models.Model):
    audit=models.ForeignKey(Audit,on_delete=models.PROTECT,related_name='suggestions')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    title=models.CharField(max_length=180)
    framework=models.CharField(max_length=80)
    description=models.TextField()
    test_steps=models.TextField()
    status=models.CharField(max_length=15,default='pending',choices=[('pending','İnceleme bekliyor'),('accepted','Kontrole dönüştürüldü'),('rejected','Revizyon istendi')])
    review_note=models.TextField(blank=True)
    control=models.OneToOneField(Control,on_delete=models.PROTECT,null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at','-pk']

class Activity(models.Model):
    audit=models.ForeignKey(Audit,on_delete=models.PROTECT)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True)
    role=models.CharField(max_length=20)
    action=models.CharField(max_length=80)
    metadata=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at','-pk']

class Notification(models.Model):
    message=models.TextField()
    delivered_at=models.DateTimeField(null=True,blank=True)
    attempts=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)

class ControlEmail(models.Model):
    control=models.ForeignKey(Control,on_delete=models.PROTECT)
    recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    email=models.EmailField()
    subject=models.CharField(max_length=250)
    body=models.TextField()
    delivered_at=models.DateTimeField(null=True,blank=True)
    attempts=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['control','recipient'],name='one_new_control_email_per_recipient')]
