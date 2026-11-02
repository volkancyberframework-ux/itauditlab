"""Explicit first-login service acknowledgement, separate from password changes."""
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import CustomUser, FirstLoginServiceConsent

NOTICE_VERSION = '2026-11-02-v1'
NOTICE_TEXT = (
    'Hizmet elektronik ortamda anında ifa edilir. Programa kontenjan dahilinde katılırsın. '
    'Cayma hakkı bulunmamaktadır. Ödenen tutar iade edilmez.'
)
IMMEDIATE_LABEL = 'Hizmetin elektronik ortamda hemen sunulmasını istiyorum.'
ACKNOWLEDGEMENT_LABEL = (
    'Bildirimi okudum; kontenjan dahilinde katıldığımı, cayma hakkı bulunmadığını '
    've ödenen tutarın iade edilmeyeceğini kabul ediyorum.'
)


def needs_service_consent(user):
    return (user.is_first_login and not user.is_staff and not user.is_superuser
            and not FirstLoginServiceConsent.objects.filter(user_id=user.pk).exists())


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def service_consent(request):
    if not needs_service_consent(request.user):
        return redirect('force_password_change_popup' if request.user.is_first_login else 'dashboard_student')
    error = None
    if request.method == 'POST':
        if (request.POST.get('notice_version') != NOTICE_VERSION
                or request.POST.get('immediate_performance') != 'yes'
                or request.POST.get('acknowledge') != 'yes'):
            error = 'Devam etmek için güncel bildirimi oku ve her iki onay kutusunu da işaretle.'
        else:
            with transaction.atomic():
                user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
                FirstLoginServiceConsent.objects.get_or_create(user=user, defaults={
                    'version': NOTICE_VERSION,
                    'notice_text': '\n\n'.join((NOTICE_TEXT, IMMEDIATE_LABEL, ACKNOWLEDGEMENT_LABEL)),
                    'immediate_performance': True, 'no_refund_acknowledged': True,
                })
            return redirect('force_password_change_popup')
    return render(request, 'first-login-service-consent.html', {
        'notice_text': NOTICE_TEXT, 'notice_version': NOTICE_VERSION,
        'immediate_label': IMMEDIATE_LABEL, 'acknowledgement_label': ACKNOWLEDGEMENT_LABEL,
        'consent_error': error,
    }, status=400 if error else 200)
