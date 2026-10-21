from datetime import timedelta
from types import SimpleNamespace

from django import forms
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods

from .guest_auth import clear_guest_session, pending_guest, session_user
from .models import OnboardingEvent, SkoolGuestAccount

DUMMY_PASSWORD = make_password("unusable-guest-timing-value")
LOGIN_ERROR = "E-posta veya şifre hatalı ya da misafir erişiminiz şu anda kullanılamıyor."


class GuestLoginForm(forms.Form):
    email = forms.EmailField(label="E-posta adresiniz", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "username", "placeholder": "Davet edilen e-posta adresiniz"}))
    password = forms.CharField(label="Şifreniz", max_length=256, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class GuestPasswordForm(forms.Form):
    full_name = forms.CharField(label="Adınız Soyadınız", min_length=2, max_length=160, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    new_password1 = forms.CharField(label="Yeni şifreniz", max_length=256, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    new_password2 = forms.CharField(label="Yeni şifreniz (tekrar)", max_length=256, strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, account, **kwargs):
        self.account = account
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        first, second = data.get("new_password1"), data.get("new_password2")
        if first and second and first != second:
            self.add_error("new_password2", "Şifreler eşleşmiyor.")
        if first:
            if self.account.check_password(first):
                self.add_error("new_password1", "İlk giriş şifrenizden farklı bir şifre seçin.")
            try:
                validate_password(first, SimpleNamespace(email=self.account.email, username=self.account.email, first_name=data.get("full_name", ""), last_name=""))
            except ValidationError as error:
                self.add_error("new_password1", error)
        return data


def _start_session(request, account):
    clear_guest_session(request)
    request.session["skool_guest_auth"] = account.session_hash()
    if account.must_change_password:
        request.session["skool_guest_pending_id"] = account.pk
        request.session.set_expiry(30 * 60)
    else:
        request.session["skool_user_id"] = account.user_id
        request.session.set_expiry(60 * 60 * 24 * 30)


@never_cache
@sensitive_variables()
@sensitive_post_parameters("password")
@require_http_methods(["GET", "POST"])
def guest_login(request):
    if pending_guest(request):
        return redirect("skool:guest_password_change")
    if session_user(request):
        return redirect("skool:onboarding")
    form = GuestLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]
        with transaction.atomic():
            account = SkoolGuestAccount.objects.select_for_update().select_related("user__invitation").filter(email__iexact=email).first()
            now = timezone.now()
            if account is None:
                check_password(password, DUMMY_PASSWORD)
            elif account.is_active and account.user.invitation.status == "claimed" and not (account.locked_until and account.locked_until > now):
                if account.check_password(password):
                    account.failed_attempts = 0
                    account.locked_until = None
                    account.last_login_at = now
                    account.save(update_fields=("failed_attempts", "locked_until", "last_login_at"))
                    _start_session(request, account)
                    return redirect("skool:guest_password_change" if account.must_change_password else "skool:onboarding")
                account.failed_attempts = (0 if account.locked_until else account.failed_attempts) + 1
                account.locked_until = now + timedelta(minutes=15) if account.failed_attempts >= 5 else None
                account.save(update_fields=("failed_attempts", "locked_until"))
            form.add_error(None, LOGIN_ERROR)
    return render(request, "skool/guest_auth.html", {"form": form, "password_change": False})


@never_cache
@sensitive_variables()
@sensitive_post_parameters("new_password1", "new_password2")
@require_http_methods(["GET", "POST"])
def guest_password_change(request):
    account = pending_guest(request)
    if account is None:
        return redirect("skool:guest_login")
    form = GuestPasswordForm(request.POST or None, account=account)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked = SkoolGuestAccount.objects.select_for_update().select_related("user__invitation").get(pk=account.pk)
            from django.utils.crypto import constant_time_compare
            if (not locked.is_active or not locked.must_change_password or locked.user.invitation.status != "claimed"
                    or not constant_time_compare(request.session.get("skool_guest_auth", ""), locked.session_hash())):
                clear_guest_session(request)
                return redirect("skool:guest_login")
            locked.set_password(form.cleaned_data["new_password1"])
            locked.must_change_password = False
            locked.password_changed_at = timezone.now()
            locked.save(update_fields=("password", "must_change_password", "password_changed_at"))
            locked.user.full_name = " ".join(form.cleaned_data["full_name"].split())
            locked.user.save(update_fields=("full_name", "updated_at"))
            OnboardingEvent.objects.create(user=locked.user, event_type="guest_password_changed")
            _start_session(request, locked)
        return redirect("skool:onboarding")
    return render(request, "skool/guest_auth.html", {"form": form, "password_change": True})
