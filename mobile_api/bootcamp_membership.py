"""Lifetime mobile access is fulfilled only from verified Stripe payment events."""
import hashlib
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from .models import BootcampMobileGrant

BENEFIT = 'Ücretsiz ömür boyu GRC Ustası mobil uygulaması tam üyeliği dahildir.'

def prepare(product, amount_minor, currency):
    return BootcampMobileGrant.objects.create(product=product,amount_minor=amount_minor,currency=currency)

@transaction.atomic
def fulfil(session):
    """Caller must have validated the webhook signature and Stripe live/test mode."""
    meta=session.get('metadata') or {}
    try:
        grant=BootcampMobileGrant.objects.select_for_update().get(pk=meta.get('bootcamp_checkout_id'))
    except (BootcampMobileGrant.DoesNotExist,ValidationError,ValueError,TypeError):
        raise ValidationError('Unknown bootcamp checkout')
    if grant.fulfilled_at:
        transaction.on_commit(lambda: send_receipt(grant.pk))
        return grant
    total=session.get('amount_total');subtotal=session.get('amount_subtotal')
    if (session.get('payment_status')!='paid' or session.get('mode')!='payment'
        or not session.get('id') or not session.get('payment_intent')
        or session.get('id')!=grant.checkout_session_id
        or meta.get('product')!=grant.product or session.get('currency')!=grant.currency
        or subtotal!=grant.amount_minor or type(total)is not int or not 0<=total<=subtotal):
        raise ValidationError('Invalid bootcamp payment')
    email=((session.get('customer_details') or {}).get('email') or '').strip().casefold()
    validate_email(email)
    User=get_user_model();matches=list(User.objects.select_for_update().filter(email__iexact=email)[:2])
    if len(matches)>1 or (matches and not matches[0].is_active):
        raise ValidationError('Account requires manual reconciliation')
    if matches:user=matches[0]
    else:
        username='mobile_'+hashlib.sha256(email.encode()).hexdigest()[:40]
        user,created=User.objects.get_or_create(username=username,defaults={'email':email,'first_name':email.split('@')[0][:150],'is_mobile':True,'mobile_email_verified':False,'mobile_must_change_password':True})
        user=User.objects.select_for_update().get(pk=user.pk)
        if user.email.casefold()!=email or not user.is_active:raise ValidationError('Account mismatch')
        if created:user.set_unusable_password()
    user.is_mobile=True;user.mobile_full_access=True;user.mobile_last_date=None
    user.save(update_fields=['is_mobile','mobile_full_access','mobile_last_date','password'])
    # Keep email verification, password, roles, progress and existing purchases intact.
    grant.user=user;grant.payment_intent_id=session['payment_intent'];grant.fulfilled_at=timezone.now()
    grant.save(update_fields=['user','payment_intent_id','fulfilled_at'])
    transaction.on_commit(lambda: send_receipt(grant.pk))
    return grant

@transaction.atomic
def fulfil_travel(session):
    """Travel handler has already verified price, signature, and transaction identity."""
    existing=BootcampMobileGrant.objects.filter(payment_intent_id=session['payment_intent'],fulfilled_at__isnull=False).first()
    if existing:return existing
    grant,_=BootcampMobileGrant.objects.get_or_create(checkout_session_id=session['id'],defaults={
        'product':'travel_bootcamp','amount_minor':session['amount_total'],'currency':session['currency']})
    snapshot=dict(session);snapshot['amount_subtotal']=grant.amount_minor
    snapshot['metadata']={**(session.get('metadata') or {}),'bootcamp_checkout_id':str(grant.pk),'product':'travel_bootcamp'}
    return fulfil(snapshot)


def send_receipt(pk):
    """Transactional access instructions; verified email and password safeguards remain."""
    import secrets
    from django.conf import settings
    from django.core.mail import send_mail,get_connection
    try:
        with transaction.atomic():
            grant=BootcampMobileGrant.objects.select_for_update().select_related('user').get(pk=pk)
            if grant.receipt_sent_at or not grant.fulfilled_at:return bool(grant.receipt_sent_at)
            user=get_user_model().objects.select_for_update().get(pk=grant.user_id)
            first=not user.has_usable_password()
            password='Grc-'+secrets.token_urlsafe(18)+'9!' if first else None
            body='Bootcamp katılımınıza ücretsiz ömür boyu GRC Ustası mobil uygulaması tam üyeliği eklendi. Ek ücret veya otomatik yenileme yoktur.\n\nUygulama: https://app.grcustasi.com/\nHesap e-postanız: '+user.email
            if first:body+='\nİlk giriş şifreniz: '+password+'\nİlk girişte şifrenizi yenilemeniz istenir.'
            else:body+='\nMevcut hesap şifreniz geçerlidir.'
            if not user.mobile_email_verified:
                from .email_verification import verification_url
                body+='\n\nÖnce e-postanızı doğrulayın (24 saat geçerli):\n'+verification_url(user)
            body+='\n\nLinux: Denetçi Gözüyle ve ücretli öğrenme yollarına hesabınızla erişebilirsiniz.\nDestek: volkan@grcustasi.com'
            if send_mail('GRC Ustası • Ömür boyu mobil üyeliğiniz',body,settings.DEFAULT_FROM_EMAIL,[user.email],connection=get_connection(timeout=10))!=1:
                raise RuntimeError('Receipt not accepted')
            if first:
                user.set_password(password);user.mobile_must_change_password=True
                user.save(update_fields=['password','mobile_must_change_password'])
            grant.receipt_sent_at=timezone.now();grant.receipt_error='';grant.save(update_fields=['receipt_sent_at','receipt_error'])
            return True
    except Exception:
        BootcampMobileGrant.objects.filter(pk=pk,receipt_sent_at=None).update(receipt_error='Üyelik açık; erişim e-postası yeniden gönderilmeli.')
        return False
