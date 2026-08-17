from django import forms
from .models import Lead, WaitingList


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name','email','whatsapp','profile_type','english_awareness','weekly_time','age_over_45','existing_it_experience','eligibility_awareness','career_clarity','opportunity_awareness','effort_awareness','ethics_commitment','residence_type','region','consent']

    def clean_email(self): return self.cleaned_data['email'].strip().lower()


class WaitingListForm(forms.ModelForm):
    class Meta:
        model = WaitingList
        fields = ['name','email','whatsapp','consent']
    def clean_email(self): return self.cleaned_data['email'].strip().lower()
