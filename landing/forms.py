from django import forms
from .models import CorporateInquiry, Lead, PartnerApplication, WaitingList


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name','email','whatsapp','profile_type','english_awareness','weekly_time','age_over_45','existing_it_experience','eligibility_awareness','career_clarity','opportunity_awareness','effort_awareness','ethics_commitment','residence_type','region','consent']

    def clean_email(self): return self.cleaned_data['email'].strip().lower()
    def clean_whatsapp(self):
        value = self.cleaned_data.get('whatsapp', '').strip()
        if not value:
            raise forms.ValidationError('Sonucunu görmek için WhatsApp kullandığın telefon numaranı yaz.')
        return value


class WaitingListForm(forms.ModelForm):
    class Meta:
        model = WaitingList
        fields = ['name','email','whatsapp','consent']
    def clean_email(self): return self.cleaned_data['email'].strip().lower()


class CorporateInquiryForm(forms.ModelForm):
    class Meta:
        model = CorporateInquiry
        fields = ['name', 'email', 'phone', 'company', 'employee_count', 'service', 'message', 'consent']

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_consent(self):
        if not self.cleaned_data.get('consent'):
            raise forms.ValidationError('İletişim kurulabilmesi için onay vermelisiniz.')
        return True


class PartnerApplicationForm(forms.ModelForm):
    class Meta:
        model = PartnerApplication
        fields = ['name', 'email', 'phone', 'linkedin', 'company_role', 'partnership_type', 'message', 'consent']

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_consent(self):
        if not self.cleaned_data.get('consent'):
            raise forms.ValidationError('Başvurunun iletilebilmesi için onay vermelisiniz.')
        return True
