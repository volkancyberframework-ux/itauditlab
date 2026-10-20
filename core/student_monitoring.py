"""Evidence-based CORE monitoring. No mail delivery or enrollment mutation here."""
from collections import defaultdict
from datetime import datetime, time, timedelta
from urllib.parse import urlencode, quote
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Max, Prefetch, Count
from django.forms.models import model_to_dict
from django.utils import timezone
from .models import (ProgramEnrollment, ProgramRelease, Enrollment, CustomUser,
    LearningProgramStep, PageVisit, MonitoringSettings, LessonEvidence,
    StudentIntervention, MonitoringAudit, DailyMonitoringSnapshot)

STATUS_LABELS = {'on_track': 'Takviminde', 'behind': 'Geride', 'critical': 'Kritik', 'unknown': 'Bilinmiyor'}

def settings_data(config):
    return {k: v for k, v in model_to_dict(config).items() if k != 'id'}


def audit(actor, action, before=None, after=None, student=None, intervention=None, reason=''):
    return MonitoringAudit.objects.create(actor=actor, actor_email=actor.email if actor else '', action=action,
        before=before or {}, after=after or {}, student=student, intervention=intervention, reason=reason)


def configuration():
    return MonitoringSettings.objects.get_or_create(pk=1)[0]


def _paused_duration(start, end, pauses):
    # Union overlapping pause intervals instead of counting their overlap twice.
    intervals = sorted((max(start, p.started_at), min(end, p.ended_at or end)) for p in pauses
        if p.started_at < end and (p.ended_at is None or p.ended_at > start))
    total = timedelta()
    cursor = start
    for a, b in intervals:
        a = max(a, cursor)
        if b > a:
            total += b - a
            cursor = b
    return total


def _deadline(access, span, pauses, now):
    if not access:
        return None
    result = access + span
    # Include pause intervals that become relevant after extending the deadline.
    for _ in range(len(pauses) + 2):
        adjusted = access + span + _paused_duration(access, min(result, now), pauses)
        if adjusted == result:
            break
        result = adjusted
    return result


def aggregate_programs(programs, config):
    lessons = {}
    for program in programs:
        for lesson in program['lessons']:
            if lesson['exempt'] or not lesson['required']:
                continue
            key = lesson['course_id']
            current = lessons.get(key)
            if current is None or lesson['delay_days'] > current['delay_days']:
                lessons[key] = lesson
    values = list(lessons.values())
    overdue = [x for x in values if x['overdue']]
    unknown = sum(x['state'] == 'unknown' for x in values)
    average = round(sum(x['delay_days'] for x in overdue) / len(overdue), 2) if overdue else 0
    status = ('critical' if len(overdue) >= config.critical_lessons or average >= config.critical_days
              else 'behind' if overdue else 'unknown' if unknown else 'on_track')
    return {'total': len(values), 'completed': sum(x['state'] == 'completed' for x in values),
        'available': sum(x['available'] for x in values), 'upcoming': sum(x['state'] == 'upcoming' for x in values),
        'unknown': unknown, 'overdue': len(overdue), 'average_delay': average,
        'completion': round(100 * sum(x['state'] == 'completed' for x in values) / len(values), 1) if values else None,
        'status': status, 'status_label': STATUS_LABELS[status]}


def current_students(config=None, now=None):
    config = config or configuration()
    now = now or timezone.now()
    tz = ZoneInfo(config.administrative_timezone)
    enrollments = list(ProgramEnrollment.objects.select_related('user', 'program', 'monitoring_policy').prefetch_related(
        Prefetch('program__steps', queryset=LearningProgramStep.objects.select_related('course').defer('course__description').order_by('day_offset', 'order', 'pk')),
        'releases', 'monitoring_overrides', 'monitoring_pauses').order_by('user_id', 'pk'))
    user_ids = {e.user_id for e in enrollments}
    evidence = {(x.user_id, x.course_id): x for x in LessonEvidence.objects.filter(user_id__in=user_ids)}
    videos = {(x.user_id, x.course_id): x.enrolled_at for x in Enrollment.objects.filter(user_id__in=user_ids)}
    test_access = set(CustomUser.allowed_tests.through.objects.filter(customuser_id__in=user_ids).values_list('customuser_id', 'course_id'))
    access_dates = {}
    for r in ProgramRelease.objects.filter(enrollment__user_id__in=user_ids, access_granted_at__isnull=False).select_related('enrollment', 'step'):
        key = (r.enrollment.user_id, r.step.course_id)
        access_dates[key] = min(access_dates.get(key, r.access_granted_at), r.access_granted_at)
    visits = {v['user_id']: max(filter(None, [v['latest'], v['seen']])) for v in
        PageVisit.objects.filter(user_id__in=user_ids).values('user_id').annotate(latest=Max('created_at'), seen=Max('last_seen'))}
    interventions = defaultdict(list)
    for w in StudentIntervention.objects.filter(student_id__in=user_ids).only('id', 'student_id', 'status', 'created_at', 'marked_sent_at').order_by('-created_at', '-pk'):
        interventions[w.student_id].append(w)
    activities = defaultdict(list)
    for (uid, _), ev in evidence.items():
        if ev.last_accessed_at:
            activities[uid].append(ev.last_accessed_at)
    rows = {}
    for e in enrollments:
        policy = getattr(e, 'monitoring_policy', None)
        enrollment_status = policy.status if policy else ('active' if e.is_active else 'archived')
        active = e.is_active and e.program.is_active and e.user.is_active and enrollment_status == 'active'
        if (not e.is_active or not e.program.is_active or not e.user.is_active) and enrollment_status == 'active':
            enrollment_status = 'archived'
        overrides = {x.step_id: x for x in e.monitoring_overrides.all()}
        releases = {x.step_id: x for x in e.releases.all()}
        pauses = list(e.monitoring_pauses.all())
        lessons = []
        for step in e.program.steps.all():
            key = (e.user_id, step.course_id)
            ev = evidence.get(key)
            ov = overrides.get(step.pk)
            release = releases.get(step.pk)
            scheduled = timezone.make_aware(datetime.combine(e.start_date + timedelta(days=step.day_offset), time.min), tz)
            actual_permission = key in test_access if step.course.is_test else key in videos
            access = (ov.access_granted_at if ov and ov.access_granted_at else None) or (release.access_granted_at if release else None)
            access = access or access_dates.get(key) or videos.get(key) or (ev.first_accessed_at if ev else None)
            available = actual_permission and (access is None or access <= now)
            exempt = bool(ov and ov.exempt)
            required = ov.required if ov else True
            completed_at = ev.completed_at if ev and ev.completion_known else None
            if exempt or not required:
                state = 'exempt'
            elif completed_at and completed_at <= now:
                state = 'completed'
            elif not actual_permission:
                state = 'upcoming' if scheduled > now else 'unknown'
            elif access and access > now:
                state = 'upcoming'
            elif ev and ev.completion_known:
                state = ('accessed' if ev.first_accessed_at else 'incomplete') if access else 'unknown'
            else:
                state = 'unknown'
            lessons.append({'step_id': step.pk, 'course_id': step.course_id, 'title': str(step.course),
                'scheduled_at': scheduled.isoformat(), 'access_at': access.isoformat() if access else None,
                'completed_at': completed_at.isoformat() if completed_at else None,
                'accessed': bool(ev and ev.first_accessed_at), 'completion_known': bool(ev and ev.completion_known),
                'state': state, 'available': available, 'required': required, 'exempt': exempt,
                'deadline': None, 'overdue': False, 'late_completed': False, 'delay_days': 0})
        required_lessons = [x for x in lessons if x['required'] and not x['exempt']]
        for pos, lesson in enumerate(required_lessons):
            access = datetime.fromisoformat(lesson['access_at']) if lesson['access_at'] else None
            deadline = None
            if config.mode == 'days':
                deadline = _deadline(access, timedelta(days=config.days), pauses, now)
            elif pos + 1 < len(required_lessons):
                nxt = required_lessons[pos + 1]
                # Never treat a planned release as actual access evidence.
                if nxt['access_at']:
                    deadline = datetime.fromisoformat(nxt['access_at'])
                    if access:
                        deadline = _deadline(access, max(timedelta(), deadline - access), pauses, now)
            elif config.last_lesson_days:
                deadline = _deadline(access, timedelta(days=config.last_lesson_days), pauses, now)
            if deadline:
                lesson['deadline'] = deadline.isoformat()
                lesson['late_completed'] = bool(lesson['completed_at'] and datetime.fromisoformat(lesson['completed_at']) > deadline)
                lesson['overdue'] = bool(active and lesson['available'] and lesson['state'] in ('accessed', 'incomplete') and now > deadline)
                if lesson['overdue']:
                    lesson['delay_days'] = round((now - deadline).total_seconds() / 86400, 2)
        summary = aggregate_programs([{'lessons': lessons}], config)
        program = {'enrollment_id': e.pk, 'program_id': e.program_id, 'name': e.program.name,
            'active': active, 'enrollment_status': enrollment_status, 'lessons': lessons, **summary}
        row = rows.setdefault(e.user_id, {'id': e.user_id, 'name': e.user.get_full_name() or e.user.username,
            'email': e.user.email, 'programs': [], 'last_activity': None, 'last_warning': None,
            'warning_status': '', 'warning_status_label': 'Uyarı yok', 'open_intervention': False})
        row['programs'].append(program)
        activity = [x for x in [visits.get(e.user_id), e.user.last_login] if x]
        activity += activities[e.user_id]
        if activity:
            row['last_activity'] = max(activity).isoformat()
    for row in rows.values():
        row.update(aggregate_programs([p for p in row['programs'] if p['active']], config))
        history = interventions[row['id']]
        sent = [w for w in history if w.marked_sent_at]
        row['last_warning'] = max(w.marked_sent_at for w in sent).isoformat() if sent else None
        if history:
            latest_unresolved = next((w for w in history if w.status in ('sent', 'awaiting', 'responded', 'meeting')), history[0])
            row['warning_status'], row['warning_status_label'] = latest_unresolved.status, latest_unresolved.get_status_display()
        row['open_intervention'] = any(w.status != 'resolved' for w in history)
    return list(rows.values())


def filter_students(rows, config, program_id='', enrollment_status='active', warning_status='', search=''):
    result = []
    for original in rows:
        selected = [p for p in original['programs'] if (not program_id or str(p['program_id']) == str(program_id)) and
                    (not enrollment_status or p['enrollment_status'] == enrollment_status)]
        if not selected or (warning_status and original['warning_status'] != warning_status):
            continue
        if search and search.casefold() not in (original['name'] + ' ' + original['email']).casefold():
            continue
        row = dict(original, programs=selected)
        row.update(aggregate_programs(selected, config))
        result.append(row)
    return result


def metrics(rows):
    active = [r for r in rows if any(p['active'] for p in r['programs'])]
    known = [r['completion'] for r in active if r['completion'] is not None]
    overdue = sum(r['overdue'] for r in active)
    return {'students': len(active), 'enrollments': sum(p['active'] for r in active for p in r['programs']),
        'on_track': sum(r['status'] == 'on_track' for r in active), 'behind': sum(r['status'] in ('behind', 'critical') for r in active),
        'critical': sum(r['status'] == 'critical' for r in active), 'unknown': sum(r['unknown'] > 0 for r in active),
        'warned': sum(bool(r['last_warning']) for r in active),
        'awaiting': sum(r['warning_status'] in ('sent', 'awaiting') for r in active),
        'completion': round(sum(known) / len(known), 1) if known else None,
        'average_overdue': round(overdue / len(active), 2) if active else 0,
        'average_delay': round(sum(r['average_delay'] * r['overdue'] for r in active) / overdue, 2) if overdue else 0}


@transaction.atomic
def capture_snapshot(actor=None, correction_reason=''):
    if correction_reason and (not actor or not actor.has_perm('core.change_monitoringsettings') or len(correction_reason.strip()) < 5):
        raise ValueError('Özet düzeltmesi için yetkili yönetici ve gerekçe gereklidir.')
    config = configuration()
    day = timezone.now().astimezone(ZoneInfo(config.administrative_timezone)).date()
    previous = DailyMonitoringSnapshot.objects.select_for_update().filter(reporting_date=day).first()
    if previous and not correction_reason:
        return previous, False
    rows = current_students(config)
    values = metrics(rows)
    start = timezone.make_aware(datetime.combine(day, time.min), ZoneInfo(config.administrative_timezone))
    end = start + timedelta(days=1)
    warning_counts = dict(StudentIntervention.objects.filter(marked_sent_at__gte=start, marked_sent_at__lt=end).values('student_id').annotate(n=Count('pk')).values_list('student_id', 'n'))
    resolved_counts = dict(MonitoringAudit.objects.filter(action='intervention_status', after__status='resolved', created_at__gte=start, created_at__lt=end).values('student_id').annotate(n=Count('intervention_id', distinct=True)).values_list('student_id', 'n'))
    for row in rows:
        row['warnings_today'] = warning_counts.get(row['id'], 0)
        row['resolved_today'] = resolved_counts.get(row['id'], 0)
    values['warnings_today'] = sum(warning_counts.values())
    values['resolved_today'] = MonitoringAudit.objects.filter(action='intervention_status', after__status='resolved', created_at__gte=start, created_at__lt=end).values('intervention_id').distinct().count()
    payload = {'settings_snapshot': settings_data(config), 'students': rows, 'metrics': values}
    if previous:
        before = {'settings': previous.settings_snapshot, 'students': previous.students, 'metrics': previous.metrics}
        audit(actor, 'snapshot_correction', before, payload, reason=correction_reason)
        for key, value in payload.items():
            setattr(previous, key, value)
        previous.save(update_fields=list(payload))
        return previous, True
    obj, created = DailyMonitoringSnapshot.objects.get_or_create(reporting_date=day, defaults=payload)
    return obj, created


def email_template(row):
    breakdown = '\n'.join(f"- {p['name']}: {p['completed']}/{p['total']} ders (%{p['completion'] or 0}); tamamlanma bilgisi bilinmeyen: {p['unknown']}" for p in row['programs'])
    body = f"""Merhaba {row['name']},

Bildiğiniz üzere GRC Ustası olarak interaktif ve takvime bağlı bir eğitim programı yürütüyoruz.

Şu anda kayıtlı olduğunuz {', '.join(p['name'] for p in row['programs'])} kapsamında toplam {row['available']} farklı ders erişiminize açılmış durumda.

Bunlardan {row['overdue']} tanesinde eğitim takviminin gerisinde olduğunuzu görüyoruz. Gecikmiş derslerinizde ortalama {row['average_delay']} günlük bir gecikme bulunmaktadır.

Programlarınızdaki mevcut tamamlanma durumunuz:
{breakdown}

Önümüzde ise henüz erişime açılmamış {row['upcoming']} farklı ders daha bulunuyor.

Tamamlanma veya erişim bilgisi doğrulanamayan {row['unknown']} ders gecikmiş kabul edilmemiştir. Rakamlar doğrulanmış kayıtlarla sınırlıdır.

Mevcut gecikmelerin birikmesi, programdan alacağınız verimi ve ilerleyen eğitim sürecinizi olumsuz etkileyebilir.

Amacımız sizi programdan uzaklaştırmak değil, gecikmenin nedenini anlamak ve birlikte bir çözüm bulmak.

Bu nedenle bu e-postaya iki gün içerisinde dönüş yapmanızı ve kısa bir birebir görüşme planlamamızı rica ediyoruz.

Belirtilen süre içerisinde dönüş alınmaması ve ilerleme sağlanmaması durumunda üyeliğinizin geçici olarak dondurulması değerlendirilebilir.

Ayrıca programın devamında sunulan 6 aylık iş bulma desteğinin planlanan takvimde yürütülebilmesi açısından bu mesajı son uyarı olarak değerlendirmenizi rica ediyoruz.

Birlikte uygun bir yol bulabileceğimize inanıyorum.

Saygılarımla,
Volkan Güler
GRC Ustası"""
    return 'GRC Ustası | Eğitim Programınız Hakkında Önemli Uyarı', body


def mailto(recipient, subject, body):
    return 'mailto:' + quote(recipient, safe='@') + '?' + urlencode({'subject': subject, 'body': body}, quote_via=quote)


@transaction.atomic
def create_draft(student, actor, confirm_duplicate=False):
    # Lock the shared student row to serialize duplicate drafts from concurrent tabs.
    CustomUser.objects.select_for_update().get(pk=student.pk)
    if StudentIntervention.objects.filter(student=student).exclude(status='resolved').exists() and not confirm_duplicate:
        raise ValueError('Çözülmemiş bir müdahale var. Yeniden taslak oluşturmayı ayrıca onaylayın.')
    config = configuration()
    row = next((r for r in current_students(config) if r['id'] == student.pk), None)
    if row is None or not any(p['active'] for p in row['programs']):
        raise ValueError('Öğrencinin aktif program kaydı bulunmuyor.')
    row = filter_students([row], config)[0]
    subject, body = email_template(row)
    obj = StudentIntervention.objects.create(student=student, created_by=actor,
        enrollment_ids=[p['enrollment_id'] for p in row['programs']], subject=subject, body=body,
        progress_snapshot=row, monitoring_settings=settings_data(config))
    audit(actor, 'draft_created', after={'subject': subject, 'body': body}, student=student, intervention=obj)
    return obj
