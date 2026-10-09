"""StoreKit 2 transactions: Apple's signature and account token are authoritative."""
from datetime import datetime, timezone as utc
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException, VerificationStatus
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied, APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from .models import AppleEntitlement, BillingIdentity, Subscription
from .views import MobileView, premium


class AppleUnavailable(APIException):
    status_code = 503
    default_detail = 'Apple doğrulaması geçici olarak kullanılamıyor. Tekrar deneyebilirsin.'


class PurchaseThrottle(UserRateThrottle):
    rate = '30/min'


class NotificationThrottle(AnonRateThrottle):
    rate = '300/min'


@lru_cache(maxsize=2)
def verifier(environment):
    roots = [p.read_bytes() for p in (Path(__file__).parent / 'apple_roots').glob('*.cer')]
    return SignedDataVerifier(roots, True, environment, settings.APPLE_BUNDLE_ID, settings.APPLE_APP_ID)


def decode(signed, notification=False):
    if not isinstance(signed, str) or not 100 < len(signed) < 50000:
        raise ValidationError('Apple satın alma belgesi geçersiz.')
    environments = [Environment.PRODUCTION]
    if settings.APPLE_ALLOW_SANDBOX:
        environments.append(Environment.SANDBOX)
    retryable = False
    for environment in environments:
        try:
            check = verifier(environment)
            payload = (check.verify_and_decode_notification(signed) if notification
                       else check.verify_and_decode_signed_transaction(signed))
            return payload, check
        except VerificationException as error:
            retryable |= error.status == VerificationStatus.RETRYABLE_VERIFICATION_FAILURE
            continue
    if retryable:
        raise AppleUnavailable()
    raise ValidationError('Satın alma Apple tarafından doğrulanamadı.')


def timestamp(value):
    if type(value) is not int or value <= 0:
        raise ValidationError('Satın alma tarihleri doğrulanamadı.')
    try:
        return datetime.fromtimestamp(value / 1000, tz=utc.utc)
    except (ValueError, OverflowError):
        raise ValidationError('Satın alma tarihleri doğrulanamadı.')


def apply_purchase(payload, user=None):
    if (payload.productId != settings.APPLE_MONTHLY_PRODUCT_ID
            or payload.bundleId != settings.APPLE_BUNDLE_ID
            or payload.type != 'Auto-Renewable Subscription'
            or not payload.originalTransactionId or not payload.transactionId
            or len(payload.originalTransactionId) > 100 or len(payload.transactionId) > 100):
        raise ValidationError('Satın alma ürünü doğrulanamadı.')
    try:
        identity_id = UUID(str(payload.appAccountToken))
    except (ValueError, TypeError):
        raise ValidationError('Satın alma hesabı doğrulanamadı.')
    identity = BillingIdentity.objects.select_related('user').filter(pk=identity_id).first()
    if identity is None:
        if user is None:
            return None  # Deleted accounts cannot be resurrected by Apple notifications.
        raise PermissionDenied('Bu satın alma hesabına bağlı değil.')
    if user is not None and identity.user_id != user.pk:
        raise PermissionDenied('Bu satın alma başka bir GRC Ustası hesabına bağlı.')
    expires = timestamp(payload.expiresDate)
    timestamp(payload.purchaseDate)
    signed_at = timestamp(payload.signedDate)
    if signed_at > timezone.now() + timezone.timedelta(minutes=5):
        raise ValidationError('Satın alma tarihi geçersiz.')
    state = 'cancelled' if payload.revocationDate else ('active' if expires > timezone.now() else 'expired')
    key = f'apple:{payload.environment.value}:{payload.originalTransactionId}'
    with transaction.atomic():
        # Serialize notifications, restores and renewals for the same GRC account.
        BillingIdentity.objects.select_for_update().get(pk=identity_id)
        subscription, created = Subscription.objects.get_or_create(transaction_id=key, defaults={
            'user': identity.user, 'provider': 'apple', 'product_id': payload.productId,
            'status': state, 'expires_at': expires, 'verified_at': timezone.now()})
        if subscription.user_id != identity.user_id:
            raise PermissionDenied('Bu satın alma başka bir hesaba bağlı.')
        record, _ = AppleEntitlement.objects.select_for_update().get_or_create(subscription=subscription,
            defaults={'latest_transaction_id': payload.transactionId, 'signed_at': signed_at})
        # An old captured transaction must not undo a refund or overwrite a renewal.
        if not created and (signed_at < record.signed_at or expires < subscription.expires_at):
            return subscription
        if not created and signed_at == record.signed_at and subscription.status == 'cancelled' and state != 'cancelled':
            return subscription
        subscription.status = state
        subscription.expires_at = expires
        subscription.verified_at = timezone.now()
        subscription.save(update_fields=['status', 'expires_at', 'verified_at'])
        record.latest_transaction_id = payload.transactionId
        record.signed_at = signed_at
        record.save(update_fields=['latest_transaction_id', 'signed_at'])
        return subscription


class ApplePurchase(MobileView):
    throttle_classes = [PurchaseThrottle]

    def post(self, request):
        payload, _ = decode(request.data.get('signed_transaction'))
        apply_purchase(payload, request.user)
        return Response({'premium': premium(request.user)})


class AppleNotification(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [NotificationThrottle]

    def post(self, request):
        notification, check = decode(request.data.get('signedPayload'), notification=True)
        if notification.data and notification.data.signedTransactionInfo:
            try:
                payload = check.verify_and_decode_signed_transaction(notification.data.signedTransactionInfo)
            except VerificationException as error:
                if error.status == VerificationStatus.RETRYABLE_VERIFICATION_FAILURE:
                    raise AppleUnavailable()
                raise ValidationError('Apple bildirimi doğrulanamadı.')
            apply_purchase(payload)
        return Response({'received': True})
