"""Legal reference import and audit-scoped compliance summaries."""
import csv
import io
from collections import defaultdict
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from .models import Legislation, LegalArticle, Evaluation
from .views import ready, scope, visible_controls

HEADERS = ['kanun_kodu', 'kanun_adi', 'madde', 'metin', 'kaynak_url']

class LegislationImportForm(forms.Form):
    file = forms.FileField(label='UTF-8 CSV dosyası', help_text='En fazla 5 MB / 5.000 madde. Virgül veya noktalı virgül ayracı kullanılabilir.')
    def clean_file(self):
        upload = self.cleaned_data['file']
        if upload.size > 5 * 1024 * 1024:raise forms.ValidationError('Dosya en fazla 5 MB olabilir.')
        try:
            text = upload.read().decode('utf-8-sig')
            delimiter = ';' if text.splitlines()[0].count(';') > text.splitlines()[0].count(',') else ','
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            if reader.fieldnames != HEADERS:raise ValueError('Sütun başlıkları örnek dosyayla aynı olmalıdır.')
            rows = []
            seen = set()
            laws = {}
            for index, raw in enumerate(reader, 2):
                if index > 5001:raise ValueError('En fazla 5.000 madde yüklenebilir.')
                if None in raw or any(v is None for v in raw.values()):raise ValueError(f'Satır {index}: sütun sayısı hatalı.')
                row = {k: v.strip() for k, v in raw.items()}
                key = (row['kanun_kodu'], row['madde'])
                if key in seen:raise ValueError(f'Satır {index}: aynı kanun ve madde dosyada tekrarlanıyor.')
                seen.add(key)
                law = Legislation(code=row['kanun_kodu'], title=row['kanun_adi'], source_url=row['kaynak_url'])
                law.full_clean(validate_unique=False, validate_constraints=False)
                article = LegalArticle(number=row['madde'], text=row['metin'])
                article.full_clean(exclude=['legislation'], validate_unique=False, validate_constraints=False)
                metadata = (law.title, law.source_url)
                if law.code in laws and laws[law.code] != metadata:raise ValueError(f'Satır {index}: aynı kanunun adı/kaynağı tutarsız.')
                laws[law.code] = metadata
                rows.append(row)
            if not rows:raise ValueError('Dosyada en az bir madde bulunmalıdır.')
        except (UnicodeError, ValueError, IndexError, csv.Error, ValidationError) as error:
            raise forms.ValidationError(f'Dosya yüklenemedi: {error}') from error
        self.rows = rows
        return upload

@ready
def import_legislation(request):
    if not request.user.is_superuser:return HttpResponseForbidden()
    if request.GET.get('sample') == '1':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="mevzuat-ornek.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(HEADERS)
        writer.writerow(['ORNEK-01', 'Örnek düzenleme (gerçek mevzuat değildir)', '1/2-a', 'Buraya madde metnini yazın.', 'https://example.com/'])
        return response
    form = LegislationImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            for row in form.rows:
                law, _ = Legislation.objects.update_or_create(code=row['kanun_kodu'], defaults={'title': row['kanun_adi'], 'source_url': row['kaynak_url']})
                LegalArticle.objects.update_or_create(legislation=law, number=row['madde'], defaults={'text': row['metin']})
        messages.success(request, f'{len(form.rows)} madde yüklendi. Mevcut kontrol eşleştirmeleri korundu.')
    return render(request, 'admin/import_legislation.html', {**admin.site.each_context(request), 'title': 'Kanunları ve maddeleri yükle', 'form': form})

def compliance_context(audit, role):
    controls = list(visible_controls(audit, role).prefetch_related('legal_articles__legislation'))
    mapped_ids = [c.pk for c in controls if c.legal_articles.all()]
    evaluations = {e.control_id: e for e in Evaluation.objects.filter(control_id__in=mapped_ids).only('control_id', 'assessment', 'verified')}
    laws = {}
    unmapped = 0
    for control in controls:
        references = {article.legislation_id: article.legislation for article in control.legal_articles.all()}
        if not references:unmapped += 1
        ev = evaluations.get(control.pk)
        status = ev.assessment if ev and ev.verified and ev.assessment in ('compliant', 'partial', 'noncompliant') else 'pending'
        for pk, law in references.items():
            row = laws.setdefault(pk, {'code': law.code, 'title': law.title, 'counts': defaultdict(int)})
            row['counts'][status] += 1
    rows = []
    labels = [('compliant', 'Uygun'), ('partial', 'Kısmen uygun'), ('noncompliant', 'Uygun değil'), ('pending', 'İnceleme / son onay bekliyor')]
    for row in sorted(laws.values(), key=lambda r: r['code']):
        total = sum(row['counts'].values())
        rows.append({**row, 'total': total, 'percent': round(100 * row['counts']['compliant'] / total), 'segments': [{'key': key, 'label': label, 'count': row['counts'][key], 'width': format(100 * row['counts'][key] / total, '.4f')} for key, label in labels]})
    return {'law_rows': rows, 'law_unmapped': unmapped, 'law_updated_at': timezone.now(), 'law_intern_scope': role == 'intern'}

@ready
def compliance_panel(request, audit_id):
    audit, role, _ = scope(request, audit_id)
    if role not in ('admin', 'executive', 'auditor', 'intern'):return HttpResponseForbidden()
    return render(request, 'workspace/legal_compliance.html', compliance_context(audit, role))
