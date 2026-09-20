from django import forms
from .models import STATUSES, ASSESSMENTS, Suggestion
class ResponseForm(forms.Form):
    status=forms.ChoiceField(choices=STATUSES[:-1],label='Uygulama durumu')
    explanation=forms.CharField(label='Açıklama / mevcut durum',required=False,max_length=4000,help_text='Yapılıyor ve uygulanamaz seçimlerinde açıklama zorunludur.',widget=forms.Textarea(attrs={'rows':3,'data-response-guide':'true','placeholder':'Hangi süreç uygulanıyor? Kim yürütüyor, ne sıklıkta ve hangi kanıtla doğrulanabilir?'}))
    def clean(self):
        data=super().clean()
        if data.get('status') in ('implemented','na') and not data.get('explanation','').strip():
            self.add_error('explanation','Bu durum için kısa bir açıklama yazın.')
        return data
    declaration=forms.BooleanField(label='Bilgilerin doğru, eksiksiz ve mevcut durumu yansıttığını onaylıyorum.')
class EvaluationForm(forms.Form):
    assessment=forms.ChoiceField(choices=ASSESSMENTS[:-1],label='Denetçi görüşü')
    rationale=forms.CharField(label='Değerlendirme gerekçesi (yalnızca yöneticiye açık)',max_length=4000,widget=forms.Textarea(attrs={'rows':3}))
    recommendation=forms.CharField(label='Bulgu / giderim önerisi (BT sorumlusuyla paylaşılır)',required=False,max_length=4000,widget=forms.Textarea(attrs={'rows':3}))
    private_note=forms.CharField(label='Denetim ekibi özel notu',required=False,max_length=4000,widget=forms.Textarea(attrs={'rows':2}))
    verified=forms.BooleanField(label='Kontrolü test ettim; bu değerlendirmeye son onayımı veriyorum.',required=False)
    due_date=forms.DateField(label='Bulgu giderilme son tarihi',required=False,widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}),help_text='Yeni bulguda boş bırakılırsa 30 gün sonrası atanır.')
    def clean(self):
        data=super().clean()
        if data.get('assessment') in ['partial','noncompliant'] and not data.get('recommendation'):self.add_error('recommendation','Bulgu için giderim önerisi gereklidir.')
        return data
class SuggestionForm(forms.ModelForm):
    class Meta:
        model=Suggestion
        fields=['title','framework','description','test_steps']
        labels={'title':'Önerilen kontrol','framework':'Çerçeve / referans','description':'Neyi ve neden kontrol etmeliyiz?','test_steps':'Nasıl test edilir? Adımları ve beklenen kanıtları yazın.'}
        widgets={'description':forms.Textarea(attrs={'rows':3}),'test_steps':forms.Textarea(attrs={'rows':5})}
    def clean_test_steps(self):
        value=self.cleaned_data['test_steps']
        if len(value.strip())<30:raise forms.ValidationError('En az 30 karakterle somut test adımlarını açıklayın.')
        return value
class AppointmentForm(forms.Form):
    when=forms.DateTimeField(label='Gün ve saat (İstanbul)',widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    note=forms.CharField(label='İletişim / görüşme notu',max_length=2000,widget=forms.Textarea(attrs={'rows':2}))
    def clean_when(self):
        from django.utils import timezone
        value=self.cleaned_data['when']
        if value<=timezone.now():raise forms.ValidationError('Gelecekte bir gün ve saat seçin.')
        return value
class FindingForm(forms.Form):
    action=forms.ChoiceField(choices=[('remediate','Giderim bildir'),('dispute','İtiraz et'),('close','Onayla ve kapat'),('reject','Reddet / açık tut'),('reopen','Yeniden aç'),('acknowledge','Bulguyu kabul et'),('plan','Risk giderilecek'),('request_risk','Risk kabulü iste'),('accept_risk','Risk kabulünü onayla'),('set_due','Son tarihi değiştir')])
    due_date=forms.DateField(label='Giderilme son tarihi',required=False,widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}))
    explanation=forms.CharField(label='Açıklama ve kanıt özeti',max_length=4000,widget=forms.Textarea(attrs={'rows':3}))
    def clean(self):
        data=super().clean()
        if data.get('action') in ('plan','set_due') and not data.get('due_date'):
            self.add_error('due_date','Bu işlem için son tarih girin.')
        if data.get('action') in ('plan','set_due') and data.get('due_date'):
            from django.utils import timezone
            if data['due_date']<timezone.localdate():self.add_error('due_date','Geçmiş bir son tarih seçilemez.')
        return data
