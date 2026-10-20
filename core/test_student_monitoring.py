from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import (CustomUser, Course, LearningProgram, LearningProgramStep,
    ProgramEnrollment, ProgramRelease, LessonEvidence, Enrollment,
    EnrollmentMonitoringPolicy, MonitoringPause, MonitoringLessonOverride,
    StudentIntervention, MonitoringAudit, DailyMonitoringSnapshot)
from .student_monitoring import current_students, configuration, capture_snapshot, create_draft, mailto


class MonitoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.now = datetime(2026, 10, 20, 12, tzinfo=dt_timezone.utc)
        cls.user = CustomUser.objects.create_user(username='izlenen', email='ogrenci@example.com', first_name='Öğrenci', last_name='Yılmaz')
        cls.admin = CustomUser.objects.create_superuser(username='yonetici', email='yonetici@example.com', password='test')
        cls.program = LearningProgram.objects.create(name='Program A', slug='monitor-test-a')
        cls.courses = [Course.objects.create(turkish_name=f'Ders {i}', duration=timedelta(hours=1), difficulty='Beginner', description='Ders', course_type='test') for i in range(3)]
        cls.steps = [LearningProgramStep.objects.create(program=cls.program, course=c, day_offset=i*3) for i, c in enumerate(cls.courses)]
        cls.enrollment = ProgramEnrollment.objects.create(user=cls.user, program=cls.program, start_date=date(2026, 10, 10))
        for i, step in enumerate(cls.steps):
            ProgramRelease.objects.create(enrollment=cls.enrollment, step=step, access_granted_at=cls.now-timedelta(days=10-i*3))
            cls.user.allowed_tests.add(step.course)
            LessonEvidence.objects.create(user=cls.user, course=step.course, completion_known=True, evidence='Tamamlanmadığı doğrulandı.')

    def row(self, **kwargs):
        return next(r for r in current_students(now=self.now, **kwargs) if r['id'] == self.user.pk)

    def test_next_rule_uses_actual_next_access_and_excludes_last_lesson(self):
        row = self.row()
        self.assertEqual(row['overdue'], 2)
        lessons = row['programs'][0]['lessons']
        self.assertFalse(lessons[-1]['overdue'])
        self.assertIsNone(lessons[-1]['deadline'])
        self.assertEqual(row['average_delay'], 5.5)

    def test_day_rule_and_last_lesson_threshold(self):
        config = configuration()
        config.mode, config.days = 'days', 3
        self.assertEqual(self.row(config=config)['overdue'], 3)
        config.mode, config.last_lesson_days = 'next', 2
        self.assertEqual(self.row(config=config)['overdue'], 3)

    def test_access_grant_without_student_enrollment_is_incomplete(self):
        LessonEvidence.objects.filter(user=self.user).update(completion_known=False, completed_at=None)
        row = self.row()
        self.assertEqual(row['overdue'], 2)
        self.assertEqual(row['unknown'], 0)
        self.assertEqual(row['completed'], 0)
        self.assertIsNone(row['last_activity'])

    def test_future_releases_and_missing_access_never_overdue(self):
        ProgramRelease.objects.filter(step=self.steps[1]).update(access_granted_at=self.now+timedelta(days=2))
        row = self.row()
        self.assertFalse(row['programs'][0]['lessons'][0]['overdue'])
        self.assertFalse(row['programs'][0]['lessons'][1]['overdue'])
        self.user.allowed_tests.clear()
        self.assertEqual(self.row()['overdue'], 0)

    def test_late_completion_not_currently_overdue(self):
        item = Enrollment.objects.create(user=self.user, course=self.courses[0])
        Enrollment.objects.filter(pk=item.pk).update(enrolled_at=self.now-timedelta(days=1))
        row = self.row()
        self.assertEqual(row['overdue'], 1)
        self.assertTrue(row['programs'][0]['lessons'][0]['late_completed'])
        self.assertEqual(row['completed'], 1)

    def test_shared_course_multiple_programs_is_counted_once(self):
        p = LearningProgram.objects.create(name='Program B', slug='monitor-test-b')
        step = LearningProgramStep.objects.create(program=p, course=self.courses[0], day_offset=0)
        e = ProgramEnrollment.objects.create(user=self.user, program=p, start_date=self.enrollment.start_date)
        ProgramRelease.objects.create(enrollment=e, step=step, access_granted_at=self.now-timedelta(days=10))
        config = configuration()
        config.mode = 'days'
        row = self.row(config=config)
        self.assertEqual(len(row['programs']), 2)
        self.assertEqual(row['total'], 3)
        self.assertEqual(row['overdue'], 3)
        self.assertEqual(len([r for r in current_students(config, now=self.now) if r['id'] == self.user.pk]), 1)

    def test_paused_archived_completed_and_exempt_lessons(self):
        policy = EnrollmentMonitoringPolicy.objects.create(enrollment=self.enrollment, status='paused')
        self.assertEqual(self.row()['overdue'], 0)
        self.assertFalse(self.row()['programs'][0]['active'])
        for status in ['archived', 'completed']:
            policy.status = status
            policy.save()
            self.assertEqual(self.row()['overdue'], 0)
        policy.status='active'
        policy.save()
        MonitoringLessonOverride.objects.create(enrollment=self.enrollment, step=self.steps[0], exempt=True, reason='Muafiyet kanıtı')
        self.assertEqual(self.row()['total'], 2)
        self.assertEqual(self.row()['overdue'], 1)

    def test_pause_intervals_extend_days_deadline_without_double_counting(self):
        config = configuration()
        config.mode, config.days = 'days', 3
        MonitoringPause.objects.create(enrollment=self.enrollment, started_at=self.now-timedelta(days=9), ended_at=self.now-timedelta(days=2), reason='Duraklatma')
        MonitoringPause.objects.create(enrollment=self.enrollment, started_at=self.now-timedelta(days=8), ended_at=self.now-timedelta(days=3), reason='Çakışan kayıt')
        lessons = self.row(config=config)['programs'][0]['lessons']
        self.assertFalse(lessons[0]['overdue'])
        self.assertEqual(datetime.fromisoformat(lessons[0]['deadline']), self.now)

    def test_legacy_access_uses_program_schedule(self):
        ProgramRelease.objects.filter(enrollment=self.enrollment).delete()
        config = configuration()
        config.mode='days'
        self.assertEqual(self.row(config=config)['overdue'], 3)
        self.assertIsNotNone(self.row(config=config)['programs'][0]['lessons'][0]['access_at'])

    def test_manual_access_override_uses_evidence_not_planned_date(self):
        ProgramRelease.objects.filter(enrollment=self.enrollment).delete()
        MonitoringLessonOverride.objects.create(enrollment=self.enrollment, step=self.steps[0], access_granted_at=self.now-timedelta(days=5), reason='Erişim logu')
        config=configuration()
        config.mode='days'
        self.assertEqual(self.row(config=config)['overdue'], 3)

    def test_snapshots_are_idempotent_and_settings_do_not_rewrite_history(self):
        with patch('core.student_monitoring.timezone.now', return_value=self.now):
            first, created = capture_snapshot()
            self.assertTrue(created)
            before = first.students
            Enrollment.objects.bulk_create([Enrollment(user=self.user, course=c) for c in self.courses])
            Enrollment.objects.filter(user=self.user).update(enrolled_at=self.now)
            second, created = capture_snapshot()
            self.assertFalse(created)
            self.assertEqual(second.students, before)
            self.assertEqual(DailyMonitoringSnapshot.objects.count(), 1)
            corrected, _ = capture_snapshot(self.admin, 'Tamamlanma kanıtı düzeltildi')
            self.assertNotEqual(corrected.students, before)
            self.assertTrue(MonitoringAudit.objects.filter(action='snapshot_correction').exists())

    def test_current_calculation_query_count_does_not_grow_per_student(self):
        config = configuration()
        with self.assertNumQueries(11):
            current_students(config, self.now)
        for i in range(8):
            u = CustomUser.objects.create_user(username=f'scale-{i}')
            ProgramEnrollment.objects.create(user=u, program=self.program, start_date=self.enrollment.start_date)
        with self.assertNumQueries(11):
            current_students(config, self.now)

    def test_dashboard_and_all_mutations_require_server_permissions(self):
        self.client.force_login(self.user)
        url=reverse('admin:core_student_monitoring')
        self.assertIn(self.client.get(url).status_code, [302,403])
        staff=CustomUser.objects.create_user(username='limited', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(reverse('admin:core_monitoring_settings'), {'days':0}).status_code,403)
        staff.user_permissions.add(Permission.objects.get(codename='view_monitoringsettings'))
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(self.client.post(reverse('admin:core_monitoring_refresh')).status_code,403)

    def test_draft_preview_edit_mailto_and_explicit_sent_confirmation(self):
        self.client.force_login(self.admin)
        with patch('core.student_monitoring.timezone.now',return_value=self.now):
            obj=create_draft(self.user,self.admin)
        with self.assertRaises(ValueError):create_draft(self.user,self.admin)
        url=reverse('admin:core_monitoring_intervention_action',args=[obj.pk])
        payload={'subject':'Türkçe konu & deneme','body':'Merhaba Öğrenci\nGeri bildirim? &','notes':'Özel not','action':'open'}
        self.assertEqual(self.client.post(url,payload).status_code,200)
        obj.refresh_from_db()
        self.assertEqual(obj.status,'opened')
        self.assertIsNone(obj.marked_sent_at)
        self.assertEqual(obj.body,payload['body'])
        payload['action']='sent'
        self.assertEqual(self.client.post(url,payload).status_code,400)
        payload['confirm_sent']='on'
        self.assertEqual(self.client.post(url,payload).status_code,302)
        obj.refresh_from_db()
        self.assertEqual(obj.status,'sent')
        self.assertEqual(obj.marked_sent_by,self.admin)
        self.assertEqual(len(mail.outbox),0)
        self.assertEqual(MonitoringAudit.objects.filter(intervention=obj,action='intervention_sent').count(),1)
        encoded=mailto(self.user.email,payload['subject'],payload['body'])
        self.assertEqual(parse_qs(urlparse(encoded).query)['body'][0],payload['body'])
        self.assertEqual(self.client.post(url,{'action':'status','status':'draft','reason':'Yanlış işaret düzeltmesi'}).status_code,400)
        self.assertEqual(self.client.post(url,{'action':'status','status':'draft','reason':'Yanlış işaret düzeltmesi','confirm_correction':'on'}).status_code,302)
        obj.refresh_from_db()
        self.assertIsNone(obj.marked_sent_at)
        self.assertTrue(MonitoringAudit.objects.filter(intervention=obj,action='intervention_status').exists())

    def test_history_retained_after_catching_up_and_completion_is_audited(self):
        self.client.force_login(self.admin)
        obj=create_draft(self.user,self.admin)
        response=self.client.post(reverse('admin:core_monitoring_evidence',args=[self.user.pk]),{
            'course':self.courses[0].pk,'state':'completed','completed_at':timezone.now().isoformat(),'evidence':'Ödev incelemesi doğrulandı'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(StudentIntervention.objects.filter(pk=obj.pk).exists())
        self.assertTrue(MonitoringAudit.objects.filter(action='completion_evidence').exists())

    def test_authorized_course_visit_counts_as_completion(self):
        self.client.force_login(self.user)
        ev=LessonEvidence.objects.get(user=self.user,course=self.courses[0])
        ev.completion_known=False
        ev.save()
        self.assertEqual(self.client.get(reverse('course_single',args=[self.courses[0].pk])).status_code,200)
        ev.refresh_from_db()
        self.assertIsNotNone(ev.first_accessed_at)
        self.assertFalse(ev.completion_known)
        self.assertIsNone(ev.completed_at)
        self.assertEqual(next(r for r in current_students() if r['id'] == self.user.pk)['completed'], 1)

    def test_turkish_dashboard_student_preview_and_invalid_settings(self):
        self.client.force_login(self.admin)
        for url in [reverse('admin:core_student_monitoring'),reverse('admin:core_monitoring_student',args=[self.user.pk])]:
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            self.assertContains(response,'Öğrenci')
        config=configuration()
        from .student_monitoring import settings_data
        data=settings_data(config)
        data['days']=0
        self.assertEqual(self.client.post(reverse('admin:core_monitoring_settings'),data).status_code,400)
        data['days']=3
        data['administrative_timezone']='invalid/timezone'
        self.assertEqual(self.client.post(reverse('admin:core_monitoring_settings'),data).status_code,400)

    def test_students_without_accessible_lessons_are_not_overdue(self):
        other=CustomUser.objects.create_user(username='new-student')
        ProgramEnrollment.objects.create(user=other,program=self.program,start_date=date(2027,1,1))
        row=next(r for r in current_students(now=self.now) if r['id']==other.pk)
        self.assertEqual(row['available'],0)
        self.assertEqual(row['overdue'],0)
        self.assertEqual(row['upcoming'],3)

    def test_csrf_and_invalid_sent_actions_do_not_mutate_records(self):
        obj = create_draft(self.user, self.admin)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.admin)
        url = reverse('admin:core_monitoring_intervention_action', args=[obj.pk])
        self.assertEqual(secure.post(url, {'action':'sent','confirm_sent':'on','subject':'Konu','body':'Metin'}).status_code,403)
        obj.refresh_from_db()
        self.assertEqual(obj.status,'draft')
        self.assertIsNone(obj.marked_sent_at)

    def test_saved_history_keeps_settings_and_only_records_current_day(self):
        with patch('core.student_monitoring.timezone.now', return_value=self.now):
            first, _ = capture_snapshot()
        old_students = first.students
        config = configuration()
        config.mode = 'days'
        config.save()
        with patch('core.student_monitoring.timezone.now', return_value=self.now+timedelta(days=1)):
            second, _ = capture_snapshot()
        first.refresh_from_db()
        self.assertEqual(first.students, old_students)
        self.assertEqual(first.settings_snapshot['mode'],'next')
        self.assertEqual(second.settings_snapshot['mode'],'days')
        self.assertEqual(DailyMonitoringSnapshot.objects.count(),2)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:core_student_monitoring'), {'start':'2026-10-01','end':'2026-10-31'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['history']),2)

    def test_duplicate_draft_does_not_hide_awaiting_warning(self):
        obj = create_draft(self.user,self.admin)
        obj.status, obj.marked_sent_at = 'awaiting', self.now
        obj.save()
        create_draft(self.user,self.admin,confirm_duplicate=True)
        self.assertEqual(self.row()['warning_status'],'awaiting')

    def test_automatic_enrollment_is_not_student_completion(self):
        course = self.courses[0]
        course.course_type = 'video'
        course.save()
        item = Enrollment.objects.create(user=self.user, course=course, is_automatic=True)
        self.assertEqual(self.row()['completed'], 0)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('course_single', args=[course.pk])).status_code, 200)
        item.refresh_from_db()
        self.assertFalse(item.is_automatic)
        self.assertEqual(next(r for r in current_students() if r['id'] == self.user.pk)['completed'], 1)

    def test_completed_program_has_no_warning_even_with_previous_draft(self):
        create_draft(self.user, self.admin)
        for course in self.courses:
            Enrollment.objects.create(user=self.user, course=course)
        row = next(r for r in current_students() if r['id'] == self.user.pk)
        self.assertTrue(row['is_complete'])
        self.assertEqual(row['overdue'], 0)
        with self.assertRaisesMessage(ValueError, 'uyarı e-postası gerekmiyor'):
            create_draft(self.user, self.admin)

    def test_email_omits_completed_program(self):
        p = LearningProgram.objects.create(name='Tamamlanan Bootcamp', slug='finished')
        course = Course.objects.create(turkish_name='Tamamlanan ders', duration=timedelta(hours=1), difficulty='Beginner', course_type='test')
        LearningProgramStep.objects.create(program=p, course=course, day_offset=0)
        ProgramEnrollment.objects.create(user=self.user, program=p, start_date=self.enrollment.start_date)
        Enrollment.objects.create(user=self.user, course=course)
        obj = create_draft(self.user, self.admin)
        self.assertNotIn('Tamamlanan Bootcamp', obj.body)
        self.assertIn('Program A', obj.body)
        self.assertIn('toplam 3 farklı ders', obj.body)
        self.assertIn('2 tanesine', obj.body)

    def test_bulk_button_prepares_once_and_reuses_edited_draft(self):
        self.client.force_login(self.admin)
        url = reverse('admin:core_monitoring_bulk_drafts')
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['created_count'], 1)
        item = StudentIntervention.objects.get(student=self.user)
        self.assertTrue(item.body.startswith('Merhaba Öğrenci Yılmaz,'))
        item.body += '\nYönetici tarafından eklenen not.'
        item.save()
        response = self.client.post(url)
        self.assertEqual(response.context['created_count'], 0)
        self.assertEqual(response.context['reused_count'], 1)
        self.assertEqual(StudentIntervention.objects.count(), 1)
        item.refresh_from_db()
        self.assertTrue(item.body.endswith('Yönetici tarafından eklenen not.'))
        self.assertEqual(item.status, 'draft')
        self.assertIsNone(item.marked_sent_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_bulk_skips_completed_and_already_sent_students(self):
        self.client.force_login(self.admin)
        item = create_draft(self.user, self.admin)
        item.status, item.marked_sent_at = 'sent', timezone.now()
        item.save()
        url = reverse('admin:core_monitoring_bulk_drafts')
        response = self.client.post(url)
        self.assertEqual(response.context['skipped_count'], 1)
        self.assertEqual(len(response.context['prepared']), 0)
        for course in self.courses:
            Enrollment.objects.create(user=self.user, course=course)
        response = self.client.post(url)
        self.assertEqual(response.context['created_count'], 0)
        self.assertEqual(response.context['skipped_count'], 0)
        self.assertEqual(StudentIntervention.objects.count(), 1)

    def test_bulk_fixes_legacy_email_greeting_without_overwriting_body(self):
        item = create_draft(self.user, self.admin)
        item.body = f'Merhaba {self.user.email},\nÖzel düzenlenmiş metin.'
        item.save()
        self.client.force_login(self.admin)
        self.client.post(reverse('admin:core_monitoring_bulk_drafts'))
        item.refresh_from_db()
        self.assertEqual(item.body, 'Merhaba Öğrenci Yılmaz,\nÖzel düzenlenmiş metin.')
        self.assertTrue(MonitoringAudit.objects.filter(action='draft_greeting_updated').exists())

    def test_missing_name_never_uses_email_as_greeting(self):
        self.user.first_name, self.user.last_name = self.user.email, ''
        self.user.save()
        item = create_draft(self.user, self.admin)
        self.assertTrue(item.body.startswith('Merhaba,\n'))
        self.assertNotIn(self.user.email, item.body.split('\n')[0])

    def test_bulk_requires_write_permission_and_csrf(self):
        url = reverse('admin:core_monitoring_bulk_drafts')
        self.client.force_login(self.user)
        self.assertIn(self.client.post(url).status_code, [302, 403])
        staff = CustomUser.objects.create_user(username='bulk-viewer', is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename='view_monitoringsettings'))
        self.client.force_login(staff)
        self.assertEqual(self.client.post(url).status_code, 403)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.admin)
        self.assertEqual(secure.post(url).status_code, 403)
        self.assertEqual(StudentIntervention.objects.count(), 0)
