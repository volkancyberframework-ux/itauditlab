from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail, get_connection
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from rest_framework.response import Response
from .views import Login, RegistrationThrottle

SALT = 'grc-mobile-email-verification-v1'


def verification_url(user):
    token = signing.dumps({'id': user.pk, 'email': user.email.casefold()}, salt=SALT)
    return settings.PUBLIC_BASE_URL.rstrip('/') + reverse('mobile_verify_email', args=[token])


def send_verification_email(user_id):
    user = get_user_model().objects.filter(pk=user_id, is_active=True, is_mobile=True, mobile_email_verified=False).first()
    if not user:
        return False
    try:
        return send_mail('GRC Ustası • E-postanı doğrula',
            'GRC Ustası hesabına giriş yapabilmek için e-posta adresini doğrula:\n\n' + verification_url(user) +
            '\n\nBağlantı 24 saat geçerlidir. Açılan sayfada E-postamı doğrula düğmesine bas, sonra uygulamaya dönüp giriş yap.\nBu hesabı sen oluşturmadıysan bu e-postayı yok sayabilirsin.\n\nDestek: volkan@grcustasi.com',
            settings.DEFAULT_FROM_EMAIL, [user.email], connection=get_connection(timeout=10)) == 1
    except Exception:
        return False


class ResendVerification(Login):
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        email = request.data.get('email', '')
        if isinstance(email, str) and len(email) <= 254:
            users = list(get_user_model().objects.filter(email__iexact=email.strip(), is_mobile=True, is_active=True, mobile_email_verified=False)[:2])
            if len(users) == 1:
                send_verification_email(users[0].pk)
        return Response({'detail': 'Doğrulama bekleyen hesabın varsa bağlantı e-postana gönderildi. Gelen kutunu ve spam klasörünü kontrol et.'})


class VerifyEmail(View):
    def user(self, token, lock=False):
        try:
            data = signing.loads(token, salt=SALT, max_age=86400)
            queryset = get_user_model().objects.all()
            if lock:
                queryset = queryset.select_for_update()
            return queryset.filter(pk=data['id'], email__iexact=data['email'], is_active=True, is_mobile=True).first()
        except (signing.BadSignature, KeyError, ValueError, TypeError):
            return None

    def get(self, request, token):
        user = self.user(token)
        return render(request, 'mobile_api/verify_email.html', {'valid': bool(user), 'verified': bool(user and user.mobile_email_verified)}, status=200 if user else 400)

    def post(self, request, token):
        with transaction.atomic():
            user = self.user(token, lock=True)
            if user:
                user.mobile_email_verified = True
                user.save(update_fields=['mobile_email_verified'])
        return render(request, 'mobile_api/verify_email.html', {'valid': bool(user), 'verified': bool(user)}, status=200 if user else 400)
