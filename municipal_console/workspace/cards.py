import secrets
import string
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import urlencode, quote
from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac, constant_time_compare
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.debug import sensitive_post_parameters
from accounts.privacy import accepted, PRIVACY_VERSION
from .models import Audit, Control, Membership, CardAccess, CardDraft
from .views import ready, scope, shared
from .branding import organization_brand
from . import services

CHOICES=[('implemented','Yapılıyor'),('partial','Kısmen yapılıyor'),('missing','Yapılamıyor'),('na','Uygulanamaz')]
def digest(value):return salted_hmac('card-access',value,algorithm='sha256').hexdigest()

def pending_controls(audit):
    result=[]
    for control in audit.controls.prefetch_related('revisions','card_draft').all():
        revision=next(iter(control.revisions.all()),None)
        if not revision or revision.status=='unanswered' or not revision.explanation.strip():
            draft=getattr(control,'card_draft',None)
            result.append({'id':control.pk,'code':control.code,'title':control.title,'question':control.description,'guidance':control.evidence_guidance,'status':draft.status if draft else (revision.status if revision and revision.status!='unanswered' else ''),'explanation':draft.explanation if draft else (revision.explanation if revision else ''),'deferred':bool(draft or revision)})
    return result

def portal_url(request,audit):
    if audit.organization.subdomain:return f'https://{audit.organization.subdomain}.{settings.TENANT_BASE_DOMAIN}/cards/'
    base=getattr(settings,'PUBLIC_CONSOLE_URL','').rstrip('/')
    return base+'/cards/' if base else request.build_absolute_uri(reverse('card_entry'))

def grant_for(request):
    grant=CardAccess.objects.select_related('audit__organization','user').filter(pk=request.session.get('card_access_id'),revoked=False,expires_at__gt=timezone.now(),audit__archived=False,user__is_active=True).first()
    if not grant or not grant.used_at or grant.used_at+timedelta(hours=12)<=timezone.now():return None
    if not constant_time_compare(grant.session_digest,digest(request.session.get('card_session',''))):return None
    if getattr(request,'tenant',None) and request.tenant.pk!=grant.audit.organization_id:return None
    if not Membership.objects.filter(user=grant.user,audit=grant.audit,role='it').exists():return None
    return grant

class EntryForm(forms.Form):
    code=forms.RegexField(r'^[A-Za-z0-9]{12}$',label='12 karakterlik giriş kodu',max_length=12,min_length=12,widget=forms.TextInput(attrs={'autocomplete':'one-time-code','autocapitalize':'none','spellcheck':'false','placeholder':'E-postanızdaki kod'}))

@never_cache
@sensitive_post_parameters('code')
def entry(request):
    if grant_for(request):return redirect('card_workspace')
    form=EntryForm(request.POST if request.method=='POST' else None)
    if request.method=='POST' and form.is_valid():
        key='card-attempt:'+digest(request.META.get('REMOTE_ADDR',''))
        cache.add(key,0,900)
        attempts=cache.incr(key)
        if attempts>15:form.add_error(None,'Çok fazla deneme. 15 dakika sonra tekrar deneyin.')
        else:
            with transaction.atomic():
                grant=CardAccess.objects.select_for_update().select_related('audit__organization','user').filter(code_digest=digest(form.cleaned_data['code']),used_at__isnull=True,revoked=False,expires_at__gt=timezone.now(),audit__archived=False,user__is_active=True).first()
                if grant and getattr(request,'tenant',None) and grant.audit.organization_id!=request.tenant.pk:grant=None
                if grant and not Membership.objects.filter(user=grant.user,audit=grant.audit,role='it').exists():grant=None
                if grant:
                    token=secrets.token_urlsafe(32)
                    grant.used_at=timezone.now();grant.session_digest=digest(token);grant.save(update_fields=['used_at','session_digest'])
                    request.session.cycle_key()
                    request.session['card_access_id']=grant.pk;request.session['card_session']=token
                    cache.delete(key)
                    return redirect('card_workspace')
                form.add_error(None,'Kod geçersiz, kullanılmış veya süresi dolmuş. Denetçinizden yeni kod isteyin.')
    return render(request,'cards/entry.html',{'form':form})

class ConsentForm(forms.Form):
    consent=forms.BooleanField(label='Gizlilik sözleşmesini okudum ve kabul ediyorum.')
    acknowledgement=forms.CharField(label='“okudum, anladım” yazın',max_length=100)
    def clean_acknowledgement(self):
        value=self.cleaned_data['acknowledgement'].strip().translate(str.maketrans('Iİ','ıi')).lower()
        if value!='okudum, anladım':raise forms.ValidationError('Lütfen “okudum, anladım” yazın.')
        return value

@never_cache
def workspace(request):
    grant=grant_for(request)
    if not grant:return redirect('card_entry')
    ctx={**organization_brand(grant.audit.organization),'audit':grant.audit,'card_user':grant.user}
    if not accepted(grant.user):
        form=ConsentForm(request.POST if request.method=='POST' else None)
        if request.method=='POST' and form.is_valid():
            grant.user.privacy_accepted_at=timezone.now();grant.user.privacy_version=PRIVACY_VERSION
            grant.user.save(update_fields=['privacy_accepted_at','privacy_version'])
            return redirect('card_workspace')
        return render(request,'cards/consent.html',{**ctx,'form':form})
    return render(request,'cards/workspace.html',{**ctx,'cards':pending_controls(grant.audit)})

@never_cache
@require_POST
def save(request):
    grant=grant_for(request)
    if not grant or not accepted(grant.user):return JsonResponse({'error':'Oturum sona erdi. Yeniden giriş yapın.'},status=403)
    status=request.POST.get('status','');explanation=request.POST.get('explanation','').strip()
    if status not in dict(CHOICES) or len(explanation)>4000:return JsonResponse({'error':'Bir yanıt seçin; açıklama en fazla 4000 karakter olabilir.'},status=400)
    defer=request.POST.get('defer')=='1'
    try:control_id=int(request.POST.get('control',''))
    except (ValueError,TypeError):return JsonResponse({'error':'Geçersiz kontrol.'},status=400)
    if not defer and (not explanation or request.POST.get('declaration')!='on'):return JsonResponse({'error':'Açıklama yazın ve doğruluk onayını işaretleyin.'},status=400)
    with transaction.atomic():
        audit=Audit.objects.select_for_update().get(pk=grant.audit_id)
        # Recheck authorization inside the write transaction.
        if not grant_for(request):return JsonResponse({'error':'Erişiminiz kaldırılmış.'},status=403)
        control=get_object_or_404(Control,audit=audit,pk=control_id)
        if control.pk not in {c['id'] for c in pending_controls(audit)}:return JsonResponse({'error':'Bu kontrol başka bir oturumda tamamlandı. Sayfayı yenileyin.'},status=409)
        if defer:
            CardDraft.objects.update_or_create(control=control,defaults={'actor':grant.user,'status':status,'explanation':explanation})
            services.log(audit,grant.user,'it','Kart yanıtı taslak kaydedildi',control=control.code)
        else:
            services.answer(audit,control,grant.user,'it',{'status':status,'explanation':explanation,'declaration':True})
            CardDraft.objects.filter(control=control).delete()
    return JsonResponse({'cards':pending_controls(audit),'message':'Açıklama bekleyenlere eklendi.' if defer else 'Yanıt kaydedildi.'})

@require_POST
@never_cache
def leave(request):
    grant=grant_for(request)
    if grant:CardAccess.objects.filter(pk=grant.pk).update(revoked=True)
    request.session.pop('card_access_id',None);request.session.pop('card_session',None)
    return redirect('card_entry')

class DispatchForm(forms.Form):
    recipient=forms.ModelChoiceField(queryset=Membership.objects.none(),label='BT sorumlusu')
    selection=forms.ChoiceField(choices=[('pending','Yanıtlanmayan / açıklaması eksik kontroller'),('all','Tüm kontroller — önceki yanıt ve tarih ile')],label='Gönderilecek kontroller')
    def __init__(self,*args,audit,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['recipient'].queryset=audit.membership_set.filter(role='it',user__is_active=True).select_related('user')
        self.fields['recipient'].label_from_instance=lambda m: m.user.get_full_name() or m.user.email

@ready
def dispatch(request,audit_id):
    audit,role,preview=scope(request,audit_id)
    if role not in ('admin','auditor') or getattr(request,'auditor_readonly',False):raise PermissionDenied
    form=DispatchForm(request.POST if request.method=='POST' else None,audit=audit)
    ctx=shared(request,audit,role,preview)
    if request.method=='POST' and form.is_valid():
        user=form.cleaned_data['recipient'].user
        pending={c['id'] for c in pending_controls(audit)}
        rows=[]
        for c in audit.controls.prefetch_related('revisions').all():
            if form.cleaned_data['selection']=='pending' and c.pk not in pending:continue
            previous=next(iter(c.revisions.all()),None)
            rows.append({'code':c.code,'title':c.title,'question':c.description,'previous':previous if form.cleaned_data['selection']=='all' else None})
        if not rows:form.add_error(None,'Gönderilecek kontrol bulunmuyor.')
        else:
            alphabet=string.ascii_letters+string.digits
            code=''.join(secrets.choice(alphabet) for _ in range(12))
            while not (any(c.isdigit() for c in code) and any(c.isalpha() for c in code)):code=''.join(secrets.choice(alphabet) for _ in range(12))
            with transaction.atomic():
                Audit.objects.select_for_update().get(pk=audit.pk)
                CardAccess.objects.filter(audit=audit,user=user,revoked=False).update(revoked=True)
                CardAccess.objects.create(audit=audit,user=user,code_digest=digest(code),expires_at=timezone.now()+timedelta(days=7))
                services.log(audit,request.user,role,'BT kontrol e-posta taslağı hazırlandı',recipient=user.pk,selection=form.cleaned_data['selection'],count=len(rows))
            draft_context={'rows':rows,'recipient':user,'audit':audit,'code':code,'portal_url':portal_url(request,audit)}
            body=render_to_string('cards/email.txt',draft_context)
            html=render_to_string('cards/email.html',draft_context)
            subject=f'{audit.organization.name} · BT kontrol yanıtları · {audit.title}'.replace('\r',' ').replace('\n',' ')
            mailto='mailto:'+quote(user.email,safe='@')+'?'+urlencode({'subject':subject,'body':body.replace('\n','\r\n')},quote_via=quote)
            message=EmailMessage();message['To']=user.email;message['Subject']=subject;message['X-Unsent']='1'
            message.set_content(body);message.add_alternative(html,subtype='html')
            ctx.update(draft={'mailto':mailto,'eml':message.as_string()},email_html=html)
    ctx['form']=form
    response=render(request,'cards/dispatch.html',ctx);response['Referrer-Policy']='same-origin'
    return response
