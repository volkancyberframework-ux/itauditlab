from django.conf import settings as django_settings
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
import logging
import requests
from .forms import LeadForm, WaitingListForm
from .models import AssessmentSession, Certificate, JobMarketCount, NewsletterSubscriber, SiteSetting
from .curriculum import CURRICULUM, CURRICULUM_STATS

logger = logging.getLogger(__name__)


def _notify_telegram(message):
    token = getattr(django_settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(django_settings, 'TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data={'chat_id': chat_id, 'text': message},
            timeout=5,
        ).raise_for_status()
    except requests.RequestException:
        logger.exception('Kariyer pusulası Telegram bildirimi gönderilemedi.')


def home(request):
    site = SiteSetting.load()
    payment_url = site.payment_url or getattr(django_settings, 'PAYMENT_URL', '')
    return render(request, 'landing/index.html', {
        'site': site, 'payment_url': payment_url, 'jobs': JobMarketCount.objects.all(),
        'curriculum': CURRICULUM, 'curriculum_stats': CURRICULUM_STATS,
        'open_assessment': request.path.rstrip('/').endswith('kariyer-pusulasi'),
    })


@require_POST
def create_checkout(request):
    if not django_settings.STRIPE_SECRET_KEY:
        return JsonResponse({'ok': False, 'message': 'Stripe ödeme ayarı eksik.'}, status=503)
    import stripe
    stripe.api_key = django_settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            allow_promotion_codes=True,
            billing_address_collection='required',
            line_items=[{
                'price_data': {
                    'currency': 'try',
                    'unit_amount': 5_999_900,
                    'product_data': {
                        'name': '80 Saatlik GRC Ustası Yoğun Eğitim Programı',
                        'description': '6 ay eğitim ve uygulama, 6 ay kariyer desteği, ömür boyu içerik erişimi.',
                    },
                },
                'quantity': 1,
            }],
            metadata={'product': 'grc_ustasi_80_saat', 'price_try': '59999'},
            success_url=request.build_absolute_uri(reverse('landing:home') + '?payment=success#fiyat'),
            cancel_url=request.build_absolute_uri(reverse('landing:home') + '?payment=cancel#fiyat'),
        )
    except Exception:
        return JsonResponse({'ok': False, 'message': 'Ödeme şu anda başlatılamadı. Lütfen volkan@grcustasi.com adresine yazın.'}, status=502)
    return redirect(session.url, permanent=False)


def _errors(form): return {k: [str(x) for x in v] for k, v in form.errors.items()}


@require_POST
def save_assessment(request):
    email = request.POST.get('email', '').strip().lower()
    profile = request.POST.get('profile_type', '').strip()
    if profile not in dict(AssessmentSession.PROFILE_CHOICES):
        return JsonResponse({'ok': False, 'message': 'Lütfen profilini yeniden seç.'}, status=400)
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try: validate_email(email)
    except ValidationError: return JsonResponse({'ok': False, 'message': 'Geçerli bir e-posta adresi yaz.'}, status=400)
    allowed = ('residence_type','region','age_over_45','eligibility_awareness','career_clarity','opportunity_awareness','effort_awareness','english_awareness','weekly_time','ethics_commitment','assessment_completed')
    incoming = {key: request.POST.get(key) for key in allowed if key in request.POST}
    session = AssessmentSession.objects.filter(email=email).first()
    if request.POST.get('initial_capture') == 'true' and session:
        return JsonResponse({
            'ok': False,
            'message': 'Bu e-posta adresiyle daha önce kariyer pusulasına başlanmış. Aynı e-posta ile yeniden değerlendirme başlatamazsın.',
        }, status=409)
    answers = dict(session.answers) if session else {}
    answers.update(incoming)
    discount = AssessmentSession.discount_for(profile)
    expires = (session.discount_expires_at if session and session.profile_type == profile else timezone.now() + timezone.timedelta(days=3))
    session, created = AssessmentSession.objects.update_or_create(email=email, defaults={
        'profile_type': profile, 'answers': answers, 'discount_percent': discount,
        'discount_expires_at': expires, 'completed': request.POST.get('assessment_completed') == 'true' or bool(session and session.completed),
    })
    if created:
        _notify_telegram(
            '🧭 Yeni GRC Ustası kariyer pusulası\n'
            f'E-posta: {session.email}\n'
            f'Profil: {session.get_profile_type_display()}\n'
            f'İndirim: %{session.discount_percent}'
        )
    return JsonResponse({'ok': True, 'discount': discount, 'expires_at': session.discount_expires_at.isoformat()})


@require_POST
def submit_lead(request):
    form = LeadForm(request.POST)
    if not form.is_valid(): return JsonResponse({'ok': False, 'errors': _errors(form)}, status=400)
    d = form.cleaned_data
    awareness_score = sum(1 for key in ('eligibility_awareness','career_clarity','opportunity_awareness','effort_awareness','ethics_commitment') if d[key])
    score = awareness_score + (2 if d['english_awareness'] else 0) + (3 if d['weekly_time'] else 0)
    if d['profile_type'] == 'working' and d['residence_type'] == 'turkey' and d['age_over_45']: result = 'wait'
    elif score >= 9 and d['ethics_commitment']: result = 'strong'
    else: result = 'develop'
    lead = form.save(commit=False)
    lead.test_score, lead.result_type = score, result
    lead.student_discount_eligible = d['profile_type'] == 'student'
    assessment = AssessmentSession.objects.filter(email=d['email']).first()
    lead.discount_percent = AssessmentSession.discount_for(d['profile_type'])
    lead.discount_expires_at = assessment.discount_expires_at if assessment else timezone.now() + timezone.timedelta(days=3)
    try: lead.save()
    except IntegrityError:
        return JsonResponse({'ok': False, 'errors': {'email': ['Bu e-posta ile daha önce bir sonuç oluşturulmuş.']}}, status=409)
    reasons = {
        'strong': ['Hedefin, çalışma planın ve etik yaklaşımın programla uyumlu.', 'Risk, teknoloji ve iş süreçlerinin kesişimine açıksın.'],
        'develop': ['Başlamak için uygun bir profilsin.', 'Hedef, İngilizce, çalışma temposu veya etik sorumluluk başlıklarından bazılarını netleştirmen faydalı olur.'],
        'wait': ['Türkiye’deki mevcut başlangıç koşulların için bu yoğun program en verimli seçenek olmayabilir.', 'Önce daha kısa bir teknoloji ve iş süreçleri temeliyle ilerlemeni öneriyoruz.']}
    if lead.whatsapp:
        _notify_telegram(
            '📱 Kariyer pusulasında WhatsApp paylaşıldı\n'
            f'Ad: {lead.name}\n'
            f'E-posta: {lead.email}\n'
            f'WhatsApp: {lead.whatsapp}\n'
            f'Profil: {lead.get_profile_type_display()}\n'
            f'Sonuç: {lead.get_result_type_display()}'
        )
    if assessment:
        assessment.answers.update({key: request.POST.get(key, '') for key in request.POST if key not in ('csrfmiddlewaretoken','name','whatsapp','consent')})
        assessment.completed = True
        assessment.save(update_fields=['answers','completed','updated_at'])
    return JsonResponse({'ok': True, 'result': result, 'title': dict(lead.RESULT_CHOICES)[result], 'reasons': reasons[result], 'student': lead.student_discount_eligible, 'discount': lead.discount_percent, 'discount_expires_at': lead.discount_expires_at.isoformat()})


@require_POST
def join_waiting_list(request):
    form = WaitingListForm(request.POST)
    if not form.is_valid(): return JsonResponse({'ok': False, 'errors': _errors(form)}, status=400)
    try: form.save()
    except IntegrityError: return JsonResponse({'ok': False, 'message': 'Bu e-posta zaten listede.'}, status=409)
    return JsonResponse({'ok': True, 'message': 'Harika, yeni grup açıldığında sana haber vereceğiz.'})


@require_POST
def subscribe_newsletter(request):
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email
    email = request.POST.get('email', '').strip().lower()
    consent = request.POST.get('consent') == 'true'
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'ok': False, 'message': 'Geçerli bir e-posta adresi yaz.'}, status=400)
    if not consent:
        return JsonResponse({'ok': False, 'message': 'Bülten kaydı için iletişim iznini onaylamalısın.'}, status=400)
    subscriber, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={'consent': True, 'discount_percent': 5, 'is_active': True},
    )
    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.consent = True
        subscriber.save(update_fields=['is_active', 'consent'])
    return JsonResponse({
        'ok': True,
        'created': created,
        'message': 'Bülten kaydın tamamlandı. Tüm programlarda geçerli %5 ayrıcalığını kullanmak için volkan@grcustasi.com adresine e-posta gönder.',
    })


def verify_certificate(request):
    cid = request.GET.get('certificate_id', '').strip()
    if not cid: return JsonResponse({'ok': False, 'status': 'not_found', 'message': 'Sertifika ID girin.'}, status=400)
    cert = Certificate.objects.filter(certificate_id__iexact=cid).first()
    if not cert: return JsonResponse({'ok': True, 'status': 'not_found', 'message': 'Sertifika bulunamadı.'})
    expired = cert.status == 'expired' or (cert.expiry_date and cert.expiry_date < timezone.localdate())
    status = 'expired' if expired else ('valid' if cert.status == 'valid' else 'not_found')
    name_parts = cert.participant_name.split()
    safe_name = f'{name_parts[0]} {name_parts[-1][0]}.' if len(name_parts) > 1 else name_parts[0]
    return JsonResponse({'ok': True, 'status': status, 'message': 'Geçerli sertifika.' if status == 'valid' else 'Sertifikanın süresi dolmuş.', 'participant': safe_name, 'issue_date': cert.issue_date.strftime('%d.%m.%Y')})
