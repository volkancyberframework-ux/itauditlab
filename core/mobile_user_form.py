import hashlib
from datetime import datetime, time, timedelta
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import CustomUser


class MobileUserCreateForm(forms.Form):
    name = forms.CharField(label='Ad soyad', max_length=150)
    email = forms.EmailField(label='E-posta')
    password = forms.CharField(label='Şifre', widget=forms.PasswordInput, min_length=8, max_length=256)
    paid = forms.BooleanField(label='Ücretli / tam erişim', required=False)
    last_date = forms.DateField(label='Ücretli erişimin son günü', required=False, widget=forms.DateInput(attrs={'type':'date'}), help_text='Ücretli hesabın son erişim günü. Boşsa sınırsız. Ücretsiz hesaplara yalnızca başlangıç yolu açılır.')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().casefold()
        if CustomUser.objects.filter(email__iexact=email, is_mobile=True).exists():
            raise ValidationError('Bu e-posta için mobil hesap zaten var.')
        return email

    def clean(self):
        data = super().clean()
        if data.get('last_date') and not data.get('paid'):
            self.add_error('last_date', 'Ücretsiz hesap için bitiş tarihi girmeyin.')
        if data.get('last_date') and data['last_date'] < timezone.localdate():
            self.add_error('last_date', 'Bitiş tarihi geçmişte olamaz.')
        if data.get('password'):
            user = CustomUser(email=data.get('email',''), first_name=data.get('name',''))
            try:
                validate_password(data['password'], user)
            except ValidationError as error:
                self.add_error('password', error)
        return data

    def save(self):
        data = self.cleaned_data
        first, _, last = data['name'].strip().partition(' ')
        user = CustomUser(username='mobile_' + hashlib.sha256(data['email'].encode()).hexdigest()[:40], email=data['email'], first_name=first, last_name=last, is_mobile=True, mobile_full_access=data['paid'] and not data['last_date'])
        if data['paid'] and data['last_date']:
            user.mobile_paid_until = timezone.make_aware(datetime.combine(data['last_date'] + timedelta(days=1), time.min))
        user.set_password(data['password'])
        user.save(force_insert=True)
        return user
