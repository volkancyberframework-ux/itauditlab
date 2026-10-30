"""Explicit superuser cleanup; ordinary admin permissions and PROTECT stay intact."""
import re
from django import forms
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import render
from django.utils import timezone
from .models import CustomUser, LessonEvidence
from mobile_api.models import AccountDeletionRequest, Subscription, MobilePayment, MobileCheckoutRequest, XPTransaction, BootcampMobileGrant

OWNERS = {'guler.volkan@yahoo.com', 'volkancyberframework@gmail.com'}
SALT = 'core.guarded-account-cleanup.v1'


class CleanupForm(forms.Form):
    emails = forms.CharField(label='Silinecek e-posta adresleri', max_length=60000, widget=forms.Textarea(attrs={'rows':12,'cols':90}))

    def clean_emails(self):
        values = sorted(set(x.lower() for x in re.split(r'[\s,;]+', self.cleaned_data['emails'].strip()) if x))
        if not values or len(values) > 1000:
            raise forms.ValidationError('1–1000 e-posta girin.')
        for value in values:
            validate_email(value)
        return values


def eligible(user):
    if (not user.is_active or user.is_staff or user.is_superuser or user.email.lower() in OWNERS
            or user.mobile_full_access or (user.mobile_paid_until and user.mobile_paid_until > timezone.now())):
        return False
    return not (user.learning_programs.exists() or Subscription.objects.filter(user=user).exists()
                or MobilePayment.objects.filter(user=user).exists()
                or BootcampMobileGrant.objects.filter(user=user, fulfilled_at__isnull=False).exists())


def delete_reviewed(actor, ids):
    deleted, skipped = [], []
    for pk in ids:
        try:
            with transaction.atomic():
                user = CustomUser.objects.select_for_update().filter(pk=pk).first()
                if user is None:
                    continue
                if not eligible(user):
                    skipped.append((user.email, 'Korunan hesap / güncel kapsam dışında'))
                    continue
                email = user.email
                # These non-financial records are explicitly included in the preview.
                LessonEvidence.objects.filter(user=user).delete()
                AccountDeletionRequest.objects.filter(user=user).delete()
                LogEntry.objects.log_action(user_id=actor.pk,
                    content_type_id=ContentType.objects.get_for_model(CustomUser).pk,
                    object_id=user.pk, object_repr=str(user), action_flag=DELETION,
                    change_message='Onaylı hesap temizliği: program kaydı, ücretli mobil ve sahip hesapları korunarak silindi.')
                # XP points protect their attempt; remove the user's ledger first.
                XPTransaction.objects.filter(user=user).delete()
                # Retain unpaid checkout history without retaining the free account.
                MobileCheckoutRequest.objects.filter(user=user).update(user=None)
                BootcampMobileGrant.objects.filter(user=user, fulfilled_at__isnull=True).update(user=None)
                user.delete()
                deleted.append(email)
        except ProtectedError:
            skipped.append((email, 'Diğer korunan ilişkili kayıtlar; işlem geri alındı'))
    return deleted, skipped


def cleanup_view(model_admin, request):
    if not request.user.is_superuser or not model_admin.has_delete_permission(request):
        raise PermissionDenied
    context = {**model_admin.admin_site.each_context(request), 'title':'Korumalı hesap temizliği',
               'opts':CustomUser._meta, 'form':CleanupForm()}
    if request.method == 'POST' and request.POST.get('confirm') == 'yes':
        try:
            payload = signing.loads(request.POST.get('token',''), salt=SALT, max_age=1800)
            if payload['actor'] != request.user.pk:
                raise signing.BadSignature
        except (signing.BadSignature, KeyError, TypeError):
            raise PermissionDenied('Silme önizlemesi geçersiz veya süresi dolmuş.')
        context['deleted'], context['skipped'] = delete_reviewed(request.user, payload['ids'])
        context['finished'] = True
    elif request.method == 'POST':
        form = CleanupForm(request.POST)
        context['form'] = form
        if form.is_valid():
            # Lower() matches duplicate addresses regardless of database collation.
            from django.db.models.functions import Lower
            users = list(CustomUser.objects.annotate(normalized_email=Lower('email')).filter(normalized_email__in=form.cleaned_data['emails']).order_by('pk'))
            selected = [u for u in users if eligible(u)]
            ids = [u.pk for u in selected]
            context.update(review=True, selected=selected, protected=[u for u in users if u not in selected],
                evidence_count=LessonEvidence.objects.filter(user_id__in=ids).count(),
                deletion_request_count=AccountDeletionRequest.objects.filter(user_id__in=ids).count(),
                token=signing.dumps({'actor':request.user.pk,'ids':ids},salt=SALT,compress=True))
    return render(request, 'admin/account_cleanup.html', context)
