from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


def check_mobile_access(user):
    if not user or not user.is_active or not user.is_mobile:
        raise PermissionDenied("Bu hesap için mobil erişim açık değil.")
    if user.mobile_last_date and user.mobile_last_date < timezone.localdate():
        raise PermissionDenied("Mobil erişim süren doldu. Yöneticiyle iletişime geçebilirsin.")


class MobileAccessPermission(BasePermission):
    def has_permission(self, request, view):
        check_mobile_access(request.user)
        return True


class MobileTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = RefreshToken(attrs["refresh"])
        user = get_user_model().objects.filter(
            **{api_settings.USER_ID_FIELD: token[api_settings.USER_ID_CLAIM]}
        ).first()
        check_mobile_access(user)
        return super().validate(attrs)


class MobilePasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        return (user for user in super().get_users(email) if user.is_mobile)
