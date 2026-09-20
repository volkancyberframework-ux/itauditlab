from django import forms
from django.contrib.auth.forms import AuthenticationForm
class SignInForm(AuthenticationForm):
    username = forms.EmailField(label='Kurumsal e-posta', widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'adiniz@kurumunuz.com','autocomplete':'username','autocapitalize':'none','spellcheck':'false','id':'email'}))
    password = forms.CharField(label='Parola', strip=False, widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Parolanızı girin','autocomplete':'current-password','id':'password'}))
    remember = forms.BooleanField(required=False)
    error_messages = {'invalid_login':'E-posta veya parola hatalı. Lütfen bilgilerinizi kontrol edin.', 'inactive':'Bu hesaba erişim kapalı. Destek ekibiyle iletişime geçin.'}
    def clean_username(self):
        return self.cleaned_data['username'].lower()
