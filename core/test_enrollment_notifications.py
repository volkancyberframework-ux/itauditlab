from unittest.mock import patch
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TransactionTestCase, override_settings
from .models import Course, Enrollment


@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_CHAT_ID='test-chat')
class EnrollmentNotificationTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='notification-student',email='student@example.com',is_first_login=False)
        self.course = Course.objects.create(turkish_name='GRC Ustası 05', course_type='test', duration=timedelta(hours=1), difficulty='Beginner', description='Test')

    @patch('core.enrollment_notifications.requests.post')
    def test_does_not_notify_before_commit_or_after_rollback(self, post):
        with self.assertRaises(ValueError):
            with transaction.atomic():
                Enrollment.objects.create(user=self.user,course=self.course)
                post.assert_not_called()
                raise ValueError('rollback')
        self.assertFalse(Enrollment.objects.exists())
        post.assert_not_called()

    @patch('core.enrollment_notifications.requests.post')
    def test_commit_sends_actual_identifiers_and_failure_cannot_remove_record(self, post):
        post.side_effect = RuntimeError('Telegram unavailable')
        with transaction.atomic():
            item=Enrollment.objects.create(user=self.user,course=self.course)
            post.assert_not_called()
        self.assertTrue(Enrollment.objects.filter(pk=item.pk).exists())
        text=post.call_args.kwargs['data']['text']
        self.assertIn(f'Enrollment ID: {item.pk}',text)
        self.assertIn(f'User ID: {self.user.pk}',text)
        self.assertIn(f'Course ID:\n{self.course.pk}',text)

    @patch('core.enrollment_notifications.requests.post')
    def test_automatic_access_notifies_only_when_student_enrolls(self, post):
        item=Enrollment.objects.create(user=self.user,course=self.course,is_automatic=True)
        post.assert_not_called()
        item.is_automatic=False
        item.save(update_fields=['is_automatic'])
        self.assertEqual(post.call_count,1)
        item.orientation_seen=True
        item.save(update_fields=['orientation_seen'])
        self.assertEqual(post.call_count,1)

    @patch('core.enrollment_notifications.requests.post')
    def test_delete_in_same_transaction_never_sends_false_notification(self, post):
        with transaction.atomic():
            item=Enrollment.objects.create(user=self.user,course=self.course)
            item.delete()
        post.assert_not_called()

    @patch('core.enrollment_notifications.requests.post')
    def test_get_or_create_existing_record_does_not_notify_again(self, post):
        Enrollment.objects.get_or_create(user=self.user,course=self.course)
        Enrollment.objects.get_or_create(user=self.user,course=self.course)
        self.assertEqual(post.call_count,1)

    @patch('core.enrollment_notifications.requests.post')
    def test_archived_history_does_not_send_until_reenrollment(self, post):
        item=Enrollment.objects.create(user=self.user,course=self.course,is_archived=True,restored_from_access=True)
        post.assert_not_called()
        item.is_archived=False;item.restored_from_access=False
        item.save(update_fields=['is_archived','restored_from_access'])
        self.assertEqual(post.call_count,1)

    @patch('core.enrollment_notifications.requests.post')
    def test_leaving_keeps_history_but_hides_active_card_and_can_reenroll(self, post):
        from django.urls import reverse
        item=Enrollment.objects.create(user=self.user,course=self.course)
        self.course.dashboard_activated=True;self.course.is_turkish=True;self.course.save()
        self.user.is_turkish=True;self.user.save();self.user.allowed_tests.add(self.course)
        self.client.force_login(self.user)
        response=self.client.post(reverse('unenroll_course'),{'course_id':self.course.pk})
        self.assertEqual(response.status_code,302)
        item.refresh_from_db();self.assertTrue(item.is_archived)
        response=self.client.get(reverse('dashboard_student'))
        self.assertNotIn(self.course.pk,response.context['enrolled_course_ids'])
        self.assertEqual(post.call_count,1)
        response=self.client.post(reverse('dashboard_student'),{'course_id':self.course.pk})
        self.assertEqual(response.status_code,302)
        item.refresh_from_db();self.assertFalse(item.is_archived)
        self.assertEqual(Enrollment.objects.filter(user=self.user,course=self.course).count(),1)
        self.assertEqual(post.call_count,2)

    @patch('core.enrollment_notifications.requests.post')
    def test_recovery_uses_only_real_access_and_is_idempotent(self, post):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        from django.utils import timezone
        from .models import LessonEvidence
        stamp=timezone.now()-timedelta(days=7)
        LessonEvidence.objects.create(user=self.user,course=self.course,first_accessed_at=stamp)
        from .enrollment_history import restore_access_history as recover
        recover(apps,SimpleNamespace(connection=connection))
        item=Enrollment.objects.get(user=self.user,course=self.course)
        self.assertTrue(item.is_archived);self.assertTrue(item.restored_from_access)
        self.assertEqual(item.enrolled_at,stamp)
        recover(apps,SimpleNamespace(connection=connection))
        self.assertEqual(Enrollment.objects.filter(user=self.user,course=self.course).count(),1)
        post.assert_not_called()

    @patch('core.enrollment_notifications.requests.post')
    def test_archived_video_does_not_grant_direct_access(self, post):
        from django.urls import reverse
        self.course.course_type='video';self.course.save()
        Enrollment.objects.create(user=self.user,course=self.course,is_archived=True)
        self.client.force_login(self.user)
        response=self.client.get(reverse('course_single',args=[self.course.pk]))
        self.assertEqual(response.status_code,302)
        post.assert_not_called()

    @patch('core.enrollment_notifications.requests.post')
    def test_no_history_is_invented_without_access_evidence(self, post):
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        from .models import LessonEvidence
        from .enrollment_history import restore_access_history
        LessonEvidence.objects.create(user=self.user,course=self.course)
        self.assertEqual(restore_access_history(apps,SimpleNamespace(connection=connection)),0)
        self.assertFalse(Enrollment.objects.filter(user=self.user,course=self.course).exists())
        post.assert_not_called()
