from datetime import date, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from .daily_kpis import build_payload, capture_report, delta, format_report
from .models import (AnalyticsEvent, LearningPath, LearningSession, MobileDailyKPI,
                     Question, QuestionAttempt, Subscription, UserPathProgress, VoiceSubmission)

ZONE=ZoneInfo('Europe/Istanbul')

@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='', GRCUSTASI_TELEGRAM_BOT_TOKEN='', GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID='')
class MobileDailyKPITests(TestCase):
    def setUp(self):
        get_user_model().objects.update(is_staff=True)
        self.report_date=date(2026,10,29);self.day=date(2026,10,28)
        self.now=datetime(2026,10,29,5,tzinfo=ZONE)
        self.a=self.user('a','Ada','Yılmaz',mobile_full_access=True)
        self.b=self.user('b','Bora','Kaya')
        self.c=self.user('c','Cem','',mobile_email_verified=False,date_joined=self.at(9))
        self.disabled=self.user('closed','Kapalı','Hesap',is_active=False)
        self.admin=self.user('admin','Yönetici','',is_staff=True,mobile_full_access=True)
        self.web=self.user('web','Web','',is_mobile=False)
        self.path=LearningPath.objects.create(title='Ağ Denetimi',published=True)
        self.q=Question.objects.create(kind='image',prompt='Q1',options=[{'id':'a','text':'A'}],answer=['a'])
        self.q2=Question.objects.create(kind='scenario',prompt='Q2',options=[{'id':'a','text':'A'}],answer=['a'])
        self.info=Question.objects.create(kind='info',prompt='Read')
        self.voice=Question.objects.create(kind='voice',prompt='Explain',answer=['manual'])

    def user(self,key,first,last,**kwargs):
        values=dict(username='kpi-'+key,email=key+'@example.test',first_name=first,last_name=last,
                    is_mobile=True,is_staff=False,is_superuser=False,is_active=True,mobile_email_verified=True,
                    date_joined=self.now-timedelta(days=60))
        values.update(kwargs)
        return get_user_model().objects.create_user(**values)

    def at(self,hour,day=None):
        return datetime.combine(day or self.day,datetime.min.time(),tzinfo=ZONE)+timedelta(hours=hour)

    def event(self,user,at,name='app_opened'):
        row=AnalyticsEvent.objects.create(user=user,name=name)
        AnalyticsEvent.objects.filter(pk=row.pk).update(created_at=at)

    def attempt(self,user,q,at,correct=True,seconds=60,xp=10,archived=False):
        session=LearningSession.objects.create(user=user,path=self.path,questions=[q.pk],is_archived=archived)
        LearningSession.objects.filter(pk=session.pk).update(created_at=at)
        row=QuestionAttempt.objects.create(session=session,question=q,answer=['a'],is_correct=correct,duration_seconds=seconds,xp_change=xp)
        QuestionAttempt.objects.filter(pk=row.pk).update(created_at=at)
        return row

    def add_activity(self):
        first=self.attempt(self.a,self.q,self.at(10),seconds=90)
        self.attempt(self.a,self.q,self.at(11),False,seconds=900,xp=-5,archived=True)
        self.attempt(self.a,self.q2,self.at(12),seconds=60)
        voice_attempt=self.attempt(self.b,self.voice,self.at(13),False,seconds=120,xp=0)
        voice=VoiceSubmission.objects.create(attempt=voice_attempt,file='recordings/fake.webm',duration=30)
        VoiceSubmission.objects.filter(pk=voice.pk).update(created_at=self.at(13))
        self.attempt(self.b,self.info,self.at(14),seconds=0,xp=0)
        self.event(self.c,self.at(10),'path_opened')
        for _ in range(5):self.event(self.a,self.at(10),'question_answered')
        self.attempt(self.admin,self.q,self.at(15),seconds=30)
        self.attempt(self.web,self.q,self.at(15),seconds=30)
        previous=self.day-timedelta(days=1)
        self.attempt(self.a,self.q,self.at(10,previous),seconds=60)
        self.event(self.b,self.at(15,previous))
        LearningSession.objects.filter(pk=first.session_id).update(completed_at=self.at(16),is_archived=True)

    def test_closed_day_metrics_ignore_admins_and_telemetry_duplicates(self):
        self.add_activity();data=build_payload(self.report_date,self.now)
        current=data['current'];previous=data['previous']
        self.assertEqual((current['active'],previous['active']),(3,2))
        self.assertEqual((current['learners'],current['answers'],current['cards'],current['voices']),(2,4,1,1))
        self.assertEqual((current['graded'],current['correct'],current['accuracy']),(3,2,66.7))
        self.assertEqual(current['seconds'],870)
        self.assertEqual(current['sessions_completed'],1)
        self.assertEqual(current['net_xp'],15)
        self.assertEqual(current['new_accounts'],1)
        self.assertEqual((data['returned'],data['return_base']),(2,2))
        self.assertEqual((data['newly_active'],data['lost_active']),(1,0))
        self.assertEqual(data['accounts']['total'],4)
        self.assertEqual((data['accounts']['enabled'],data['accounts']['disabled']),(3,1))
        self.assertEqual(data['accounts']['verification_pending'],1)
        self.assertEqual(data['leaders'][0]['user_id'],self.a.pk)
        self.assertEqual((data['leaders'][0]['unique_questions'],data['leaders'][0]['answers']),(2,3))
        self.assertEqual(data['popular_paths'][0]['students'],2)
        self.assertEqual(data['popular_paths'][0]['answers'],4)
        self.assertNotIn('Ada',str(data))
        report=format_report(data)
        self.assertIn('Ada Yılmaz',report);self.assertNotIn('@example.test',report)
        self.assertIn('28.10.2026 ↔ 27.10.2026',report)

    def test_assigned_paths_do_not_make_users_active(self):
        UserPathProgress.objects.create(user=self.a,path=self.path)
        UserPathProgress.objects.create(user=self.b,path=self.path)
        data=build_payload(self.report_date,self.now)
        self.assertEqual(data['current']['active'],0)
        self.assertEqual(data['current']['answers'],0)
        self.assertIsNone(data['current']['accuracy'])
        self.assertEqual(data['leaders'],[])
        self.assertIn('Rapor gününde kayıtlı soru yanıtı yok.',format_report(data))

    def test_local_midnight_and_current_partial_day_are_separate(self):
        midnight=self.at(0)
        self.event(self.a,midnight-timedelta(seconds=1))
        self.event(self.b,midnight)
        self.event(self.c,self.at(0,self.report_date))
        data=build_payload(self.report_date,self.now)
        self.assertEqual(data['current']['active'],1)
        self.assertEqual(data['previous']['active'],1)
        self.assertEqual(data['active_user_ids'],[self.b.pk])

    def test_weekly_activity_and_old_quiet_accounts(self):
        quiet=self.user('quiet','Sessiz','')
        self.user('recent','Yeni','',date_joined=self.at(8))
        self.event(self.a,self.at(10,self.day-timedelta(days=6)))
        self.event(self.b,self.at(10,self.day-timedelta(days=7)))
        data=build_payload(self.report_date,self.now)
        self.assertEqual(data['weekly_active'],1)
        self.assertEqual(data['quiet_7d'],2) # Bora + quiet, not disabled/recent/Cem.

    def test_full_access_includes_lifetime_monthly_and_store_but_not_expired(self):
        self.b.mobile_paid_until=self.now+timedelta(days=2);self.b.save()
        Subscription.objects.create(user=self.c,provider='apple',transaction_id='kpi-store',status='grace_period',expires_at=self.now+timedelta(days=1),verified_at=self.now)
        expired=self.user('expired','Süresi','Doldu',mobile_full_access=True,mobile_last_date=self.report_date-timedelta(days=1))
        data=build_payload(self.report_date,self.now)
        self.assertEqual(data['accounts']['full_access'],3)
        self.assertEqual(data['accounts']['expired_access'],1)
        self.assertEqual(data['accounts']['standard_access'],0)
        self.assertEqual(data['accounts']['total'],5)

    def test_first_snapshot_is_stable_and_account_delta_starts_from_real_baseline(self):
        self.add_activity()
        with patch('mobile_api.daily_kpis.timezone.now',return_value=self.now):
            first,created=capture_report(self.report_date)
            self.assertTrue(created);self.assertIsNone(first.payload['accounts']['previous_total'])
            self.user('new','Yeni','Öğrenci',date_joined=self.now)
            self.attempt(self.b,self.q2,self.at(18))
            again,created=capture_report(self.report_date)
        self.assertFalse(created);self.assertEqual(first.pk,again.pk)
        self.assertEqual(first.payload,again.payload)
        self.assertEqual(MobileDailyKPI.objects.count(),1)
        next_data=build_payload(self.report_date+timedelta(days=1),self.now+timedelta(days=1))
        self.assertEqual(next_data['accounts']['previous_total'],4)
        self.assertEqual(next_data['accounts']['total'],5)
        self.assertEqual(next_data['previous'],first.payload['current'])

    def test_rank_is_distinct_questions_not_repeated_answers(self):
        for i in range(4):self.attempt(self.a,self.q,self.at(10)+timedelta(minutes=i))
        self.attempt(self.b,self.q,self.at(11));self.attempt(self.b,self.q2,self.at(12))
        leaders=build_payload(self.report_date,self.now)['leaders']
        self.assertEqual([r['user_id'] for r in leaders],[self.b.pk,self.a.pk])

    def test_grading_and_zero_baseline_do_not_create_false_percentages(self):
        self.attempt(self.b,self.voice,self.at(13),False,xp=0)
        self.attempt(self.a,self.info,self.at(14),True,seconds=0,xp=0)
        data=build_payload(self.report_date,self.now)
        self.assertIsNone(data['current']['accuracy'])
        self.assertEqual(data['current']['answers'],1)
        self.assertEqual(delta(12,0),'↑12')
        self.assertEqual(delta(79.2,76.1),'↑3,1')
        self.assertNotIn('0/0',format_report(data))

    def test_existing_daily_telegram_contains_kpis_after_pdf_before_student_details(self):
        stats={'students':1,'courses':1,'emails':1,'failed':0,'pdf_checked':1,
               'pdf_missing':[{'course_id':742,'course':'Ders','reason':'Ek yok'}],
               'details':[{'email':'student@example.test','course':'Ders','mail':'gönderildi'}]}
        with patch('core.management.commands.run_daily_programs.run_daily_programs',return_value=stats), \
             patch('core.management.commands.run_daily_programs.notify_telegram') as notify, \
             patch('core.management.commands.run_daily_programs.send_daily_report_email'), \
             patch('core.management.commands.run_daily_programs.send_daily_traffic_report'), \
             patch('core.management.commands.run_daily_programs.send_daily_meeting_digest'), \
             patch('core.management.commands.run_daily_programs.send_weekly_telegram_note'), \
             patch('core.student_monitoring.capture_snapshot',return_value=(MagicMock(reporting_date=self.report_date),True)):
            call_command('run_daily_programs',stdout=StringIO())
        notify.assert_called_once();text=notify.call_args.args[0]
        self.assertLess(text.index('PDF EKSİĞİ'),text.index('MOBİL — GÜNLÜK KPI'))
        self.assertLess(text.index('MOBİL — GÜNLÜK KPI'),text.index('Açılan içerik detayları'))

    def test_kpi_failure_does_not_block_existing_report(self):
        stats={'students':0,'courses':0,'emails':0,'failed':0,'details':[]}
        with patch('core.management.commands.run_daily_programs.run_daily_programs',return_value=stats), \
             patch('mobile_api.daily_kpis.capture_report',side_effect=RuntimeError('failure')), \
             patch('core.management.commands.run_daily_programs.notify_telegram') as notify, \
             patch('core.management.commands.run_daily_programs.send_daily_report_email'), \
             patch('core.management.commands.run_daily_programs.send_daily_traffic_report'), \
             patch('core.management.commands.run_daily_programs.send_daily_meeting_digest'), \
             patch('core.management.commands.run_daily_programs.send_weekly_telegram_note'), \
             patch('core.student_monitoring.capture_snapshot',return_value=(MagicMock(reporting_date=self.report_date),True)):
            call_command('run_daily_programs',stdout=StringIO(),stderr=StringIO())
        notify.assert_called_once()
        self.assertIn('Mobil KPI raporu hazırlanamadı',notify.call_args.args[0])
