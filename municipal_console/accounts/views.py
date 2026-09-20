from django.conf import settings
from django.urls import reverse
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.http import Http404
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .forms import SignInForm

class SignIn(LoginView):
    template_name = 'accounts/signin.html'
    authentication_form = SignInForm
    redirect_authenticated_user = True
    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(60 * 60 * 12 if form.cleaned_data['remember'] else 0)
        return response
    def get_success_url(self):
        if self.request.user.must_change_password:
            return reverse('change_password')
        return reverse('console')

@never_cache
def root(request):
    if not settings.ROOT_SIGNIN_ENABLED:
        raise Http404
    return SignIn.as_view()(request)

@login_required
@never_cache
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        update_session_auth_hash(request, user)
        return redirect('console')
    for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control'})
    return render(request, 'accounts/password.html', {'form':form})

@require_POST
@login_required
def signout(request):
    logout(request)
    return redirect('signin')


@login_required
@never_cache
def privacy(request):
    from django import forms
    from django.utils import timezone
    from .privacy import PRIVACY_VERSION, accepted

    class PrivacyForm(forms.Form):
        consent = forms.BooleanField(label='Gizlilik sözleşmesini okudum ve kabul ediyorum.')
        acknowledgement = forms.CharField(label='Aşağıya “okudum, anladım” yazın', max_length=100)

        def clean_acknowledgement(self):
            value = self.cleaned_data['acknowledgement'].strip().translate(str.maketrans('Iİ', 'ıi')).lower()
            if value != 'okudum, anladım':
                raise forms.ValidationError('Lütfen “okudum, anladım” yazın.')
            return value

    if accepted(request.user):
        return redirect('console')
    form = PrivacyForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        request.user.privacy_accepted_at = timezone.now()
        request.user.privacy_version = PRIVACY_VERSION
        request.user.save(update_fields=['privacy_accepted_at', 'privacy_version'])
        return redirect('console')
    return render(request, 'accounts/privacy.html', {'form': form, 'privacy_version': PRIVACY_VERSION})
