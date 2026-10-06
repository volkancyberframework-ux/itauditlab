from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetConfirmView
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken


class MobileSetPasswordForm(SetPasswordForm):
    def save(self, commit=True):
        with transaction.atomic():
            self.user = get_user_model().objects.select_for_update().get(pk=self.user.pk)
            user = super().save(commit=commit)
            if commit:
                user.mobile_must_change_password = False
                user.save(update_fields=['mobile_must_change_password'])
                for token in OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now()):
                    BlacklistedToken.objects.get_or_create(token=token)
            return user


class MobileResetConfirm(PasswordResetConfirmView):
    form_class = MobileSetPasswordForm

    def get_user(self, uidb64):
        user = super().get_user(uidb64)
        return user if user and user.is_active and user.is_mobile else None
