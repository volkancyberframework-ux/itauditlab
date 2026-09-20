import secrets
import string
from urllib.parse import quote, urlencode
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from .models import Organization, Audit, Membership, ROLES
from .views import ready, scope, shared
from .services import log

SECTORS = {
    'belediye': ('Belediye', 'bir belediyede', 'Belediyelerin', 'belediyede'),
    'hastane': ('Hastane', 'bir hastanede', 'Hastanelerin', 'hastanede'),
    'sirket': ('Şirket', 'bir şirkette', 'Şirketlerin', 'şirkette'),
    'universite': ('Üniversite', 'bir üniversitede', 'Üniversitelerin', 'üniversitede'),
    'kamu': ('Kamu kurumu', 'bir kamu kurumunda', 'Kamu kurumlarının', 'kamu kurumunda'),
    'diger': ('Diğer kurum', 'bir kurumda', 'Kurumların', 'kurumda'),
}


def sector_for(audit):
    name = ((audit.template.name if audit.template else '')+' '+audit.organization.name).casefold()
    for token, key in [('belediye', 'belediye'), ('hastane', 'hastane'), ('üniversite', 'universite')]:
        if token in name:return key
    return 'sirket'


class CreateAccountForm(forms.Form):
    first_name = forms.CharField(label='Ad', max_length=150)
    last_name = forms.CharField(label='Soyad', max_length=150)
    email = forms.EmailField(label='E-posta / kullanıcı adı', max_length=254)
    organization = forms.ModelChoiceField(queryset=Organization.objects.none(), label='Kurum / şirket')
    audit = forms.ModelChoiceField(queryset=Audit.objects.none(), label='Denetim / proje')
    role = forms.ChoiceField(choices=ROLES[1:], label='Hesap rolü')
    auditor_readonly = forms.BooleanField(required=False, label='Stajyer tüm denetçi verilerini salt okunur görebilsin')
    sector = forms.ChoiceField(choices=[(key, value[0]) for key, value in SECTORS.items()], label='Kurum türü (karşılama e-postası)')

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        organizations = Organization.objects.all()
        if tenant:organizations = organizations.filter(pk=tenant.pk)
        self.fields['organization'].queryset = organizations.order_by('name')
        self.fields['audit'].queryset = Audit.objects.filter(organization__in=organizations, archived=False).select_related('organization', 'template').order_by('organization__name', 'title')
        self.fields['audit'].label_from_instance = lambda audit: f'{audit.organization.name} · {audit.title}'

    def clean_email(self):
        value = self.cleaned_data['email'].lower()
        if get_user_model().objects.filter(email__iexact=value).exists():
            raise forms.ValidationError('Bu e-posta zaten kayıtlı. Mevcut kullanıcıya merkezi yönetimde denetim üyeliği ekleyin; parolası değiştirilmez.')
        return value

    def clean(self):
        data = super().clean()
        audit, organization = data.get('audit'), data.get('organization')
        if audit and organization and audit.organization_id != organization.pk:
            self.add_error('audit', 'Seçilen denetim bu kuruma ait değil.')
        if data.get('auditor_readonly') and data.get('role') != 'intern':
            self.add_error('auditor_readonly', 'Bu seçenek yalnızca stajyer rolü içindir.')
        return data


def temporary_password():
    alphabet = string.ascii_letters+string.digits+'!@#%+-'
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(12))
        if all(any(c in group for c in password) for group in (string.ascii_lowercase, string.ascii_uppercase, string.digits, '!@#%+-')):
            return password


def project_url(request, audit):
    if audit.organization.subdomain:
        # Tenant hosts are routed to the console at /, including shared deployment.
        base = f'https://{audit.organization.subdomain}.{settings.TENANT_BASE_DOMAIN}'
        return base+'/console/?'+urlencode({'audit': audit.pk})
    public = getattr(settings, 'PUBLIC_CONSOLE_URL', '').rstrip('/')
    return (public+'/console/' if public else request.build_absolute_uri(reverse('console')))+'?'+urlencode({'audit': audit.pk})


def invitation_draft(request, user, audit, role, password, sector, readonly):
    role_name = dict(ROLES)[role]
    intro = f'Merhaba {user.get_full_name()},\n\n{audit.organization.name} kurumunun “{audit.title}” projesi için {role_name} hesabınız oluşturuldu.'
    paragraphs = [intro]
    if role == 'executive':
        paragraphs.append('Denetimin haftalık ve aylık durumuyla ilgili bilgilendirmeler alacaksınız.')
    elif role == 'intern':
        _, location, plural, at = SECTORS[sector]
        paragraphs.append(f'''{location[0].upper()+location[1:]} gerçekleştireceğimiz BT ve siber güvenlik denetimi kapsamında kapsamlı bir kontrol listesi oluşturmak istiyoruz.

Bu doğrultuda aşağıdaki konularda çalışma yapılmasını rica ederim:

1. {plural} BT, bilgi güvenliği, siber güvenlik, kişisel verilerin korunması ve ilgili süreçlerde uyması gereken kanun, yönetmelik, rehber, tebliğ, genelge ve diğer düzenlemelerin belirlenmesi.
2. Bu mevzuat ve düzenlemeler kapsamında {at} bulunması veya uygulanması beklenen kontrollerin çıkarılması.
3. Mevzuatta doğrudan zorunlu tutulmasa dahi ISO 27001, COBIT, CIS Controls, NIST gibi iyi uygulamalar dikkate alınarak {location} bulunmasını beklediğimiz ek BT ve siber güvenlik kontrollerinin belirlenmesi.

Çalışmanın Excel formatında hazırlanmasını ve en az aşağıdaki sütunları içermesini rica ederim:

• Kontrol
• Kontrol Açıklaması
• İlgili Kanun / Yönetmelik / Rehber / Standart
• İlgili Madde / Referans
• Kontrol Türü (Mevzuat / İyi Uygulama)
• Kontrol Alanı (AD, Network, Backup, IAM, KVKK, Loglama, İş Sürekliliği vb.)

Mümkün olduğunca her kontrolün doğrudan ilgili madde veya referansla eşleştirilmesini istiyorum.''')
        if readonly:paragraphs.append('Bu denetimde denetçi kayıtlarını salt okunur görüntüleyebilirsiniz; kayıt değiştirme yetkiniz bulunmamaktadır.')
    elif role == 'auditor':
        paragraphs.append('Denetim kontrollerini inceleyebilir, test sonuçlarını ve denetçi görüşlerinizi kaydedebilir, katalogdan kontrol ekleyebilir ve bulguları yönetebilirsiniz.')
    else:
        paragraphs.append('Denetim kontrollerine BT yanıtlarınızı girebilir, mevcut durum ve kanıt açıklamalarınızı kaydedebilir, bulgular için giderim veya itiraz bildirebilirsiniz.')
    paragraphs.append(f'''Kurum: {audit.organization.name}
Proje / denetim: {audit.title}
Hesap türü: {role_name}
Kullanıcı adı: {user.email}
Tek kullanımlık geçici parola: {password}
Projeye giriş: {project_url(request, audit)}

Geçici parola 12 karakterlidir ve ilk başarılı girişte geçersiz olur. Açılan ekranda yeni parolanızı belirleyin. Yeni parolayı belirlemeden oturumu kapatırsanız yeniden erişim için kurum yöneticinize başvurun.
İlk erişimde gizlilik sözleşmesini kabul etmeniz ve “okudum, anladım” yazmanız istenecektir.

Teşekkürler.''')
    subject = f'{audit.organization.name} · {role_name} hesabınız · {audit.title}'
    subject = subject.replace('\r', ' ').replace('\n', ' ')
    body = '\n\n'.join(paragraphs)
    return {'email': user.email, 'subject': subject, 'body': body,
            'mailto': 'mailto:'+quote(user.email, safe='@')+'?'+urlencode({'subject': subject, 'body': body}, quote_via=quote)}


@ready
def create_account(request):
    if not request.user.is_superuser:return HttpResponseForbidden('Kullanıcı oluşturma yalnızca platform yöneticisine açıktır.')
    audit, _, _ = scope(request)
    initial = {'organization': audit.organization_id, 'audit': audit.pk, 'sector': sector_for(audit), 'role': 'intern'} if audit else {'role': 'intern', 'sector': 'sirket'}
    form = CreateAccountForm(request.POST if request.method == 'POST' else None, initial=initial, tenant=getattr(request, 'tenant', None))
    ctx = shared(request, audit, 'admin', False)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        password = temporary_password()
        try:
            with transaction.atomic():
                user = get_user_model().objects.create_user(data['email'], password, first_name=data['first_name'], last_name=data['last_name'], must_change_password=True, temporary_password=True)
                Membership.objects.create(user=user, audit=data['audit'], role=data['role'], auditor_readonly=data['auditor_readonly'])
                log(data['audit'], request.user, 'admin', 'Kullanıcı oluşturuldu', user_id=user.pk, assigned_role=data['role'], auditor_readonly=data['auditor_readonly'])
        except IntegrityError:
            form.add_error('email', 'Bu e-posta eşzamanlı bir işlemle kaydedilmiş olabilir. Kullanıcı listesini kontrol edin.')
        else:
            ctx.update(draft=invitation_draft(request, user, data['audit'], data['role'], password, data['sector'], data['auditor_readonly']), created_user=user, assigned_audit=data['audit'])
            response = render(request, 'workspace/account_created.html', ctx)
            response['Referrer-Policy'] = 'no-referrer'
            return response
    ctx.update(form=form, account_audits=[{'id': a.pk, 'organization': a.organization_id, 'sector': sector_for(a)} for a in form.fields['audit'].queryset])
    return render(request, 'workspace/create_account.html', ctx)
