from datetime import timedelta
from functools import wraps
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import (CustomUser, LearningProgram, LearningProgramStep, ProgramEnrollment,
    MonitoringSettings, LessonEvidence, EnrollmentMonitoringPolicy, MonitoringPause,
    MonitoringLessonOverride, StudentIntervention, DailyMonitoringSnapshot, MonitoringAudit)
from .student_monitoring import (configuration, current_students, filter_students, metrics,
    settings_data, audit, capture_snapshot, create_draft, prepare_all_drafts, mailto)


def authorized(write=False):
    def decorator(view):
        @wraps(view)
        def inner(request, *args, **kwargs):
            perm = 'core.change_monitoringsettings' if write else 'core.view_monitoringsettings'
            if not request.user.is_active or not request.user.is_staff or not request.user.has_perm(perm):
                raise PermissionDenied
            config = configuration()
            with timezone.override(ZoneInfo(config.administrative_timezone)):
                return view(request, *args, **kwargs)
        return inner
    return decorator


def context(request, **kwargs):
    return {**admin.site.each_context(request), 'title': 'Öğrenci İlerlemesi ve Müdahale', **kwargs}


class MonitoringSettingsForm(forms.ModelForm):
    class Meta:
        model = MonitoringSettings
        exclude = ['id']


class FilterForm(forms.Form):
    program = forms.ModelChoiceField(queryset=LearningProgram.objects.all(), required=False, label='Program')
    enrollment_status = forms.ChoiceField(required=False, initial='active', label='Kayıt durumu', choices=[('', 'Tümü'), ('active', 'Aktif'), ('paused', 'Duraklatıldı'), ('archived', 'Arşivlendi'), ('completed', 'Tamamlandı')])
    warning_status = forms.ChoiceField(required=False, label='Uyarı durumu', choices=[('', 'Tümü')] + StudentIntervention.STATUSES)
    search = forms.CharField(required=False, label='Öğrenci ara', max_length=200)
    start = forms.DateField(required=False, label='Başlangıç', widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(required=False, label='Bitiş', widget=forms.DateInput(attrs={'type': 'date'}))
    sort = forms.ChoiceField(required=False, label='Sıralama', choices=[('-overdue','Gecikmiş ders (çoktan aza)'), ('overdue','Gecikmiş ders (azdan çoğa)'), ('-average_delay','Ortalama gecikme (çoktan aza)'), ('average_delay','Ortalama gecikme (azdan çoğa)'), ('-last_activity','Son etkinlik (yeni)'), ('last_activity','Son etkinlik (eski)'), ('completion','Tamamlanma (artan)'), ('-completion','Tamamlanma (azalan)'), ('name','Ad soyad')])

    def clean(self):
        data = super().clean()
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError('Başlangıç, bitişten sonra olamaz.')
        return data


@authorized()
def dashboard(request):
    config = configuration()
    params = request.GET.copy()
    if 'enrollment_status' not in params:
        params['enrollment_status'] = 'active'
    form = FilterForm(params)
    valid = form.is_valid()
    data = form.cleaned_data if valid else {}
    program_id = data['program'].pk if data.get('program') else ''
    filters = dict(program_id=program_id, enrollment_status=data.get('enrollment_status', 'active'), warning_status=data.get('warning_status', ''), search=data.get('search', ''))
    rows = filter_students([r for r in current_students(config) if r.get('console_pending', True)], config, **filters)
    totals = metrics(rows)
    key = data.get('sort') or '-overdue'
    known_rows = [r for r in rows if r[key.lstrip('-')] is not None]
    unknown_rows = [r for r in rows if r[key.lstrip('-')] is None]
    known_rows.sort(key=lambda r: r[key.lstrip('-')], reverse=key.startswith('-'))
    rows = known_rows + unknown_rows
    today = timezone.localdate()
    start, end = data.get('start') or today - timedelta(days=29), data.get('end') or today
    snapshots = DailyMonitoringSnapshot.objects.filter(reporting_date__range=(start, end))
    history = []
    for snap in snapshots:
        saved_config = SimpleNamespace(**snap.settings_snapshot)
        selected = filter_students(snap.students, saved_config, **filters)
        daily = metrics(selected)
        daily['warnings_today'] = sum(r.get('warnings_today', 0) for r in selected)
        daily['resolved_today'] = sum(r.get('resolved_today', 0) for r in selected)
        history.append({'date': snap.reporting_date.isoformat(), **daily})
    comparisons = []
    for days, label in [(0, 'Bugün'), (1, 'Dün'), (7, '7 gün önce'), (30, '30 gün önce')]:
        snap = DailyMonitoringSnapshot.objects.filter(reporting_date=today-timedelta(days=days)).first()
        comparisons.append({'label': label, 'date': today-timedelta(days=days), 'metrics': metrics(filter_students(snap.students, SimpleNamespace(**snap.settings_snapshot), **filters)) if snap else None})
    page = Paginator(rows, 30).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'admin/monitoring/dashboard.html', context(request, filter_form=form, settings_form=MonitoringSettingsForm(instance=config), page=page, query=query.urlencode(), totals=totals, history=history, comparisons=comparisons, can_change=request.user.has_perm('core.change_monitoringsettings'), filter_invalid=not valid))


@require_POST
@authorized(True)
def save_settings(request):
    with transaction.atomic():
        config = MonitoringSettings.objects.select_for_update().get(pk=1)
        before = settings_data(config)
        form = MonitoringSettingsForm(request.POST, instance=config)
        if not form.is_valid():
            return HttpResponseBadRequest(form.errors.as_text())
        form.save()
        audit(request.user, 'settings_changed', before, settings_data(config))
    messages.success(request, 'Ayarlar kaydedildi. Güncel durum yeniden hesaplandı; geçmiş özetler değiştirilmedi.')
    return redirect('admin:core_student_monitoring')


@require_POST
@authorized(True)
def refresh(request):
    if request.POST.get('snapshot') == '1':
        obj, created = capture_snapshot(request.user)
        messages.success(request, 'Bugünün özeti kaydedildi.' if created else 'Bugünün özeti zaten kayıtlı; geçmiş değiştirilmedi.')
    audit(request.user, 'monitoring_refreshed')
    return redirect('admin:core_student_monitoring')


@authorized()
def student_detail(request, student_id):
    student = get_object_or_404(CustomUser, pk=student_id)
    row = next((r for r in current_students() if r['id'] == student_id), None)
    if not row:
        return HttpResponseBadRequest('Öğrencinin program kaydı bulunmuyor.')
    return render(request, 'admin/monitoring/student.html', context(request, student=student, row=row,
        interventions=StudentIntervention.objects.filter(student=student).select_related('created_by', 'marked_sent_by'),
        audit_history=MonitoringAudit.objects.filter(student=student).select_related('actor')[:100], can_change=request.user.has_perm('core.change_monitoringsettings')))


@require_POST
@authorized(True)
def draft(request, student_id):
    student = get_object_or_404(CustomUser, pk=student_id)
    try:
        obj = create_draft(student, request.user, request.POST.get('confirm_duplicate') == 'on')
    except ValueError as exc:
        messages.info(request, str(exc))
        return redirect('admin:core_monitoring_student', student_id=student_id)
    return redirect('admin:core_monitoring_intervention', intervention_id=obj.pk)


class InterventionForm(forms.ModelForm):
    class Meta:
        model = StudentIntervention
        fields = ['subject', 'body', 'notes']
        labels = {'subject': 'Konu', 'body': 'Düzenlenebilir e-posta metni', 'notes': 'Yönetici notları'}
        widgets = {'body': forms.Textarea(attrs={'rows': 20}), 'notes': forms.Textarea(attrs={'rows': 3})}


@authorized()
def intervention(request, intervention_id):
    obj = get_object_or_404(StudentIntervention.objects.select_related('student', 'marked_sent_by'), pk=intervention_id)
    return render(request, 'admin/monitoring/intervention.html', context(request, item=obj, form=InterventionForm(instance=obj),
        status_choices=StudentIntervention.STATUSES, events=MonitoringAudit.objects.filter(intervention=obj).select_related('actor'),
        can_change=request.user.has_perm('core.change_monitoringsettings')))


@require_POST
@authorized(True)
@transaction.atomic
def intervention_action(request, intervention_id):
    obj = get_object_or_404(StudentIntervention.objects.select_for_update().select_related('student'), pk=intervention_id)
    action = request.POST.get('action')
    before = {'status': obj.status, 'subject': obj.subject, 'body': obj.body, 'notes': obj.notes,
        'marked_sent_at': obj.marked_sent_at.isoformat() if obj.marked_sent_at else None}
    if action in ('save', 'open', 'sent'):
        if obj.marked_sent_at:
            return HttpResponseBadRequest('Gönderildi olarak işaretlenen metin değiştirilemez; durum düzeltmesi yapabilirsiniz.')
        form = InterventionForm(request.POST, instance=obj)
        if not form.is_valid():
            return HttpResponseBadRequest(form.errors.as_text())
        obj = form.save(commit=False)
        if action == 'open':
            if not obj.student.email:
                return HttpResponseBadRequest('Öğrencinin e-posta adresi eksik.')
            obj.status = 'opened'
        if action == 'sent':
            if request.POST.get('confirm_sent') != 'on':
                return HttpResponseBadRequest('Elle gönderildi olarak işaretlemek için açık onay gereklidir.')
            obj.progress_snapshot['marked_sent'] = next((r for r in current_students() if r['id'] == obj.student_id), {})
            obj.monitoring_settings['marked_sent'] = settings_data(configuration())
            obj.status = 'sent'
            obj.marked_sent_at = timezone.now()
            obj.marked_sent_by = request.user
        obj.save()
    elif action == 'status':
        status = request.POST.get('status')
        reason = request.POST.get('reason', '').strip()
        if status not in dict(StudentIntervention.STATUSES) or len(reason) < 5:
            return HttpResponseBadRequest('Geçerli bir durum ve en az 5 karakterlik açıklama gerekli.')
        if status in ('sent', 'awaiting', 'responded', 'meeting') and not obj.marked_sent_at:
            return HttpResponseBadRequest('Önce açık onayla elle gönderildi işaretleyin.')
        if status in ('draft', 'opened') and obj.marked_sent_at:
            # A correction is explicit and fully auditable; no delivery is ever asserted.
            if request.POST.get('confirm_correction') != 'on':
                return HttpResponseBadRequest('Gönderim işaretini geri almak için düzeltmeyi onaylayın.')
            obj.marked_sent_at = None
            obj.marked_sent_by = None
        obj.status = status
        obj.notes = request.POST.get('notes', obj.notes)
        obj.save()
    else:
        return HttpResponseBadRequest('Geçersiz işlem.')
    after = {'status': obj.status, 'subject': obj.subject, 'body': obj.body, 'notes': obj.notes,
        'marked_sent_at': obj.marked_sent_at.isoformat() if obj.marked_sent_at else None}
    audit(request.user, 'intervention_status' if action == 'status' else 'intervention_'+action,
          before, after, student=obj.student, intervention=obj, reason=request.POST.get('reason', ''))
    if action == 'open':
        # Only open the external mail app on an explicit click from this page.
        return render(request, 'admin/monitoring/mailto.html', context(request, item=obj, mailto_url=mailto(obj.student.email, obj.subject, obj.body)))
    messages.success(request, 'İşlem kaydedildi. Harici teslimat doğrulandığı iddia edilmez.')
    return redirect('admin:core_monitoring_intervention', intervention_id=obj.pk)


class EvidenceForm(forms.Form):
    course = forms.IntegerField(min_value=1)
    state = forms.ChoiceField(choices=[('unknown','Bilinmiyor'),('incomplete','Tamamlanmadığı doğrulandı'),('completed','Tamamlandı')])
    completed_at = forms.DateTimeField(required=False)
    evidence = forms.CharField(min_length=5, max_length=10000)
    def clean(self):
        data = super().clean()
        if data.get('state') == 'completed' and (not data.get('completed_at') or data['completed_at'] > timezone.now()):
            raise forms.ValidationError('Tamamlanma için geçmişte veya şimdi olan bir zaman girin.')
        return data


@require_POST
@authorized(True)
@transaction.atomic
def save_evidence(request, student_id):
    student = get_object_or_404(CustomUser, pk=student_id)
    form = EvidenceForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_text())
    data = form.cleaned_data
    if not LearningProgramStep.objects.filter(program__enrollments__user=student, course_id=data['course']).exists():
        return HttpResponseBadRequest('Ders bu öğrencinin programlarına atanmamış.')
    # Serialize get-or-create and preserve already recorded access evidence.
    CustomUser.objects.select_for_update().get(pk=student.pk)
    obj, _ = LessonEvidence.objects.get_or_create(user=student, course_id=data['course'])
    before = {'completion_known': obj.completion_known, 'completed_at': obj.completed_at.isoformat() if obj.completed_at else None, 'evidence': obj.evidence}
    obj.completion_known = data['state'] != 'unknown'
    obj.completed_at = data.get('completed_at') if data['state'] == 'completed' else None
    obj.evidence = data['evidence']
    obj.verified_by = request.user
    obj.save()
    audit(request.user, 'completion_evidence', before, {'completion_known': obj.completion_known, 'completed_at': obj.completed_at.isoformat() if obj.completed_at else None, 'evidence': obj.evidence, 'course_id': obj.course_id}, student=student)
    return redirect('admin:core_monitoring_student', student_id=student.pk)


@require_POST
@authorized(True)
@transaction.atomic
def enrollment_policy(request, enrollment_id):
    enrollment = get_object_or_404(ProgramEnrollment.objects.select_for_update(), pk=enrollment_id)
    reason = request.POST.get('reason', '').strip()
    if len(reason) < 5:
        return HttpResponseBadRequest('İşlemin gerekçesini girin (en az 5 karakter).')
    action = request.POST.get('action')
    if action == 'status':
        status = request.POST.get('status')
        if status not in {'active', 'paused', 'archived', 'completed'}:
            return HttpResponseBadRequest('Geçersiz kayıt durumu.')
        policy, _ = EnrollmentMonitoringPolicy.objects.get_or_create(enrollment=enrollment)
        before = {'status': policy.status}
        if status == 'paused' and policy.status != 'paused':
            MonitoringPause.objects.create(enrollment=enrollment, started_at=timezone.now(), reason=reason)
        if policy.status == 'paused' and status != 'paused':
            for pause in MonitoringPause.objects.filter(enrollment=enrollment, ended_at__isnull=True):
                pause.ended_at = timezone.now()
                pause.save(update_fields=['ended_at'])
        policy.status = status
        policy.save()
        after = {'status': status}
    elif action == 'lesson':
        step = get_object_or_404(LearningProgramStep, pk=request.POST.get('step'), program_id=enrollment.program_id)
        override, _ = MonitoringLessonOverride.objects.get_or_create(enrollment=enrollment, step=step, defaults={'reason': reason})
        before = {'step': step.pk, 'exempt': override.exempt, 'required': override.required, 'access_granted_at': override.access_granted_at.isoformat() if override.access_granted_at else None}
        raw_access = request.POST.get('access_granted_at', '').strip()
        if raw_access:
            try:
                access_time = forms.DateTimeField().clean(raw_access)
            except forms.ValidationError:
                return HttpResponseBadRequest('Geçersiz erişim kanıtı zamanı.')
            if access_time > timezone.now():
                return HttpResponseBadRequest('Erişim kanıtı gelecekte olamaz.')
            override.access_granted_at = access_time
        override.exempt = request.POST.get('exempt') == 'on'
        override.required = request.POST.get('required') == 'on'
        override.reason = reason
        override.save()
        after = {'step': step.pk, 'exempt': override.exempt, 'required': override.required, 'access_granted_at': override.access_granted_at.isoformat() if override.access_granted_at else None}
    else:
        return HttpResponseBadRequest('Geçersiz işlem.')
    audit(request.user, 'enrollment_monitoring_'+action, before, after, student=enrollment.user, reason=reason)
    return redirect('admin:core_monitoring_student', student_id=enrollment.user_id)


@require_POST
@authorized(True)
def bulk_drafts(request):
    prepared, created, reused, skipped = prepare_all_drafts(request.user, dispatch=request.POST.get('dispatch') == '1')
    return render(request, 'admin/monitoring/bulk_drafts.html', context(request,
        prepared=prepared, created_count=created, reused_count=reused, skipped_count=skipped,
        dispatch=request.POST.get('dispatch') == '1', mail_queue=[{'id': item.pk, 'url': mailto(item.student.email, item.subject, item.body)} for item in prepared] if request.POST.get('dispatch') == '1' else []))
