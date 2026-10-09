import hashlib
from django import forms
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from .models import MobileWaitlist


class EmailForm(forms.Form):
    email = forms.EmailField(max_length=254)


@never_cache
@ensure_csrf_cookie
@require_http_methods(['GET', 'POST'])
def page(request):
    error = None
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().casefold()
            key = 'mobile-waitlist:' + hashlib.sha256(email.encode()).hexdigest()
            count = cache.get(key, 0)
            if count >= 10:
                return render(request, 'landing/mobile_waitlist.html', {'error': 'Çok fazla deneme yaptın. Bir süre sonra yeniden deneyebilirsin.'}, status=429)
            cache.set(key, count + 1, 3600)
            MobileWaitlist.objects.get_or_create(email=form.cleaned_data['email'].strip().casefold())
            request.session['mobile_waitlist_joined'] = True
            return redirect('landing:mobile_waitlist')
        error = 'Geçerli bir e-posta adresi gir.'
    return render(request, 'landing/mobile_waitlist.html', {
        'error': error, 'joined': request.session.pop('mobile_waitlist_joined', False),
        'email': request.POST.get('email', '') if error else '',
    }, status=400 if error else 200)
