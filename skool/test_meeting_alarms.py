import json
from datetime import date, datetime, time, timedelta
from urllib.parse import urlparse, parse_qs, unquote
from zoneinfo import ZoneInfo
from unittest.mock import patch, Mock
from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.models import Course, MentorshipRequest, StudentMeetingBooking
from .models import TravelAvailability, MeetingSlot, SkoolInvitation, SkoolUser, MeetingBooking, NotificationLog
from .meeting_alarms import meeting_alarm_link, alarm_payload, SALT, SHORTCUT_NAME, PREFIX
from .digest import send_daily_meeting_digest
from .services import send_telegram

@override_settings(PUBLIC_BASE_URL='https://www.grcustasi.com',GRCUSTASI_TELEGRAM_BOT_TOKEN='test-token',GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID='test-chat',TELEGRAM_BOT_TOKEN='',TELEGRAM_CHAT_ID='')
class MeetingAlarmTests(TestCase):
    def setUp(self):
        self.day=date(2026,10,31);self.zone=ZoneInfo('Europe/Istanbul')
        self.now=datetime(2026,10,31,8,tzinfo=self.zone)
        clock=patch('django.utils.timezone.now',return_value=self.now);clock.start();self.addCleanup(clock.stop)
        availability=TravelAvailability.objects.create(location_name='Istanbul',timezone='Europe/Istanbul',start_date=self.day,end_date=self.day,local_available_start=time(9),local_available_end=time(23))
        def slot(hour,minute):
            start=datetime.combine(self.day,time(hour,minute),tzinfo=self.zone)
            return MeetingSlot.objects.create(availability=availability,local_date=self.day,start_at_utc=start,end_at_utc=start+timedelta(minutes=90),status='booked')
        invitation,_=SkoolInvitation.create_invitation('Ataberk Dinler')
        member=SkoolUser.objects.create(invitation=invitation,full_name='Ataberk Dinler')
        self.skool=MeetingBooking.objects.create(user=member,slot=slot(19,30),meeting_url='https://meet.example.test/one')
        user=get_user_model().objects.create_user('ilgaz',email='private@example.test',first_name='Ilgaz',last_name='Tümer')
        course=Course.objects.create(duration=timedelta(hours=1),turkish_name='Private course')
        request=MentorshipRequest.objects.create(user=user,course=course,request_type='meeting',reason='Private sensitive request')
        self.student=StudentMeetingBooking.objects.create(user=user,request=request,slot=slot(14,45),meeting_url='https://meet.example.test/two')
        self.link=meeting_alarm_link(self.day);self.path=urlparse(self.link).path
        self.data_path=self.path+'veri/'

    @patch('skool.digest.send_telegram',return_value=True)
    def test_morning_digest_keeps_text_and_adds_one_button_for_both_kinds(self,send):
        self.assertTrue(send_daily_meeting_digest(self.day))
        text=send.call_args.args[0];self.assertIn('Bugün 2 birebir görüşmen var.',text)
        self.assertIn('Ataberk Dinler',text);self.assertIn('Ilgaz Tümer',text)
        markup=send.call_args.kwargs['reply_markup']
        self.assertEqual(len(markup['inline_keyboard']),1)
        url=markup['inline_keyboard'][0][0]['url'];self.assertTrue(url.startswith('https://www.grcustasi.com/'))
        self.assertNotIn('private@example.test',url)
        self.assertEqual(send.call_args.kwargs['idempotency_key'],'meeting-digest:2026-10-31')

    def test_exact_five_minutes_chronological_and_timezone_offsets(self):
        payload=alarm_payload(self.day);self.assertEqual(payload['version'],1)
        self.assertEqual([a['display_alarm'] for a in payload['alarms']],['14:40','19:25'])
        self.assertEqual([a['display_meeting'] for a in payload['alarms']],['14:45','19:30'])
        for a in payload['alarms']:
            self.assertEqual(datetime.fromisoformat(a['meeting_at'])-datetime.fromisoformat(a['alarm_at']),timedelta(minutes=5))
        last=datetime.fromisoformat(payload['alarms'][-1]['alarm_at'])
        self.assertEqual(last.astimezone(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%H:%M'),'23:25')

    def test_opaque_token_landing_and_latest_json_without_private_fields(self):
        response=self.client.get(self.path);self.assertEqual(response.status_code,200)
        url=response.context['shortcut_url'];self.assertTrue(url.startswith('shortcuts://run-shortcut?'))
        query=parse_qs(urlparse(url).query);self.assertEqual(query['name'],[SHORTCUT_NAME])
        self.assertEqual(urlparse(query['text'][0]).path,self.data_path)
        response=self.client.get(self.data_path);self.assertEqual(response.status_code,200)
        text=response.content.decode();self.assertNotIn('private@example.test',text);self.assertNotIn('Private sensitive request',text)
        self.assertNotIn('meet.example.test',text);self.assertNotIn('Private course',text)
        self.assertIn('no-store',response['Cache-Control']);self.assertEqual(response['Referrer-Policy'],'no-referrer')
        self.assertIn('noindex',response['X-Robots-Tag'])

    def test_repeat_clicks_keep_same_keys_and_do_not_mutate_bookings(self):
        first=self.client.get(self.data_path).json();again=self.client.get(self.data_path).json()
        self.assertEqual(first,again);self.assertEqual(len({a['label'] for a in first['alarms']}),2)
        self.assertTrue(all(a['label'].startswith(PREFIX) for a in first['alarms']))
        self.assertEqual(MeetingBooking.objects.count(),1);self.assertEqual(StudentMeetingBooking.objects.count(),1)
        self.assertFalse(NotificationLog.objects.exists())

    def test_cancellation_and_reschedule_reflected_by_same_daily_link(self):
        old=self.client.get(self.data_path).json()['alarms'][-1]
        self.student.status='cancelled';self.student.save()
        self.skool.slot.start_at_utc+=timedelta(minutes=30);self.skool.slot.end_at_utc+=timedelta(minutes=30);self.skool.slot.save()
        current=self.client.get(self.data_path).json()['alarms'];self.assertEqual(len(current),1)
        self.assertEqual(current[0]['id'],old['id']);self.assertNotEqual(current[0]['label'],old['label'])
        self.assertEqual(current[0]['display_alarm'],'19:55')

    def test_past_alarm_and_completed_bookings_excluded(self):
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,31,14,41,tzinfo=self.zone)):
            rows=self.client.get(self.data_path).json()['alarms'];self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['id'],'S'+str(self.skool.pk))
        self.skool.status='completed';self.skool.save();self.student.status='completed';self.student.save()
        self.assertEqual(self.client.get(self.data_path).json()['alarms'],[])

    def test_old_message_cannot_create_tomorrow_alarm(self):
        with patch('django.utils.timezone.now',return_value=self.now+timedelta(days=1)):
            self.assertEqual(self.client.get(self.path).status_code,410)
            response=self.client.get(self.data_path);self.assertEqual(response.status_code,410)
            self.assertNotIn('version',response.json())

    def test_unsigned_wrong_purpose_and_expired_tokens_rejected(self):
        self.assertEqual(self.client.get(reverse('skool:meeting_alarms_data',args=['bad-token'])).status_code,404)
        token=signing.dumps({'date':self.day.isoformat(),'version':1,'purpose':'other'},salt=SALT)
        self.assertEqual(self.client.get(reverse('skool:meeting_alarms_data',args=[token])).status_code,404)
        with patch('django.core.signing.time.time',return_value=1):old=meeting_alarm_link(self.day)
        self.assertEqual(self.client.get(urlparse(old).path).status_code,404)

    @patch('skool.digest.send_telegram',return_value=True)
    def test_no_meetings_leaves_zero_digest_without_button(self,send):
        send_daily_meeting_digest(self.day+timedelta(days=1))
        self.assertNotIn('reply_markup',send.call_args.kwargs)
        self.assertIn('Bugün planlanmış birebir görüşmen yok',send.call_args.args[0])

    @patch('skool.services.requests.post')
    def test_telegram_serializes_keyboard_and_preserves_idempotency(self,post):
        post.return_value=Mock()
        markup={'inline_keyboard':[[{'text':'⏰ Alarm kur','url':self.link}]]}
        self.assertTrue(send_telegram('Test',idempotency_key='test-alarm',reply_markup=markup))
        self.assertEqual(json.loads(post.call_args.kwargs['data']['reply_markup']),markup)
        self.assertFalse(send_telegram('Test',idempotency_key='test-alarm',reply_markup=markup))
        self.assertEqual(post.call_count,1)

    def test_setup_contains_dedup_and_personal_alarm_boundary(self):
        response=self.client.get(reverse('skool:meeting_alarms_setup'))
        for value in (SHORTCUT_NAME,PREFIX,'BulunanAlarmlar','AlarmEtiketi','yyyy-MM-dd HH:mm','Yalnız GRC Ustası bağlantısını kullan'):
            self.assertContains(response,value)

    def test_today_link_only_for_owner_admin(self):
        url=reverse('skool:meeting_alarms_today')
        self.assertEqual(self.client.get(url).status_code,302)
        other=get_user_model().objects.create_user('other-admin',email='other@example.test',is_staff=True,is_superuser=True,is_first_login=False)
        self.client.force_login(other);self.assertEqual(self.client.get(url).status_code,403)
        owner=get_user_model().objects.create_user('owner',email='guler.volkan@yahoo.com',is_staff=True,is_superuser=True,is_first_login=False)
        self.client.force_login(owner);result=self.client.get(url)
        self.assertEqual(result.status_code,302);self.assertTrue(result['Location'].startswith('https://www.grcustasi.com/gorusme-alarmlari/'))

    def create_auto_link(self):
        from .models import MeetingAlarmDevice
        owner=get_user_model().objects.create_user('alarm-owner',email='guler.volkan@yahoo.com',is_staff=True,is_superuser=True,is_first_login=False)
        self.client.force_login(owner)
        setup=reverse('skool:meeting_alarms_automatic_setup')
        response=self.client.post(setup,{'action':'create'})
        self.assertEqual(response.status_code,200)
        return owner,setup,response.context['feed_url'],MeetingAlarmDevice.objects.get()

    def test_auto_feed_scoped_random_hashed_and_read_only(self):
        owner,setup,link,device=self.create_auto_link()
        from django.test import Client
        raw=urlparse(link).path.split('/')[-3]
        self.assertEqual(len(raw),43);self.assertNotEqual(raw,device.token_hash)
        response=Client().get(urlparse(link).path)
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()['alarms']),2)
        self.assertIn('no-store',response['Cache-Control'])
        self.assertNotIn('private@example.test',response.content.decode())
        self.assertEqual(MeetingBooking.objects.count(),1)
        self.assertEqual(Client().post(urlparse(link).path).status_code,405)

    def test_auto_feed_reads_todays_data_without_daily_telegram_input(self):
        owner,setup,link,device=self.create_auto_link()
        with patch('django.utils.timezone.now',return_value=self.now+timedelta(days=1)):
            response=self.client.get(urlparse(link).path)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['date'],'2026-11-01')
            self.assertEqual(response.json()['alarms'],[])

    def test_auto_feed_rotation_and_revoke(self):
        owner,setup,link,device=self.create_auto_link()
        replacement=self.client.post(setup,{'action':'create'}).context['feed_url']
        self.assertNotEqual(link,replacement)
        self.assertEqual(self.client.get(urlparse(link).path).status_code,404)
        self.assertEqual(self.client.get(urlparse(replacement).path).status_code,200)
        self.client.post(setup,{'action':'revoke'})
        self.assertEqual(self.client.get(urlparse(replacement).path).status_code,404)

    def test_auto_feed_expiry_and_owner_disable(self):
        owner,setup,link,device=self.create_auto_link()
        device.expires_at=self.now-timedelta(seconds=1);device.save()
        self.assertEqual(self.client.get(urlparse(link).path).status_code,404)
        device.expires_at=self.now+timedelta(days=10);device.save()
        owner.is_active=False;owner.save()
        self.assertEqual(self.client.get(urlparse(link).path).status_code,404)
        self.assertEqual(self.client.get(reverse('skool:meeting_alarms_automatic_data',args=['x'*43])).status_code,404)

    def test_auto_provisioning_only_owner_post_with_csrf(self):
        from .models import MeetingAlarmDevice
        from django.test import Client
        setup=reverse('skool:meeting_alarms_automatic_setup')
        self.assertEqual(self.client.get(setup).status_code,302)
        other=get_user_model().objects.create_user('otherauto',email='other@example.test',is_staff=True,is_superuser=True,is_first_login=False)
        self.client.force_login(other)
        self.assertEqual(self.client.post(setup,{'action':'create'}).status_code,403)
        self.assertFalse(MeetingAlarmDevice.objects.exists())
        other.email='volkancyberframework@gmail.com';other.save()
        guarded=Client(enforce_csrf_checks=True);guarded.force_login(other)
        self.assertEqual(guarded.post(setup,{'action':'create'}).status_code,403)
        self.assertEqual(self.client.get(setup).status_code,200)
        self.assertFalse(MeetingAlarmDevice.objects.exists())
        self.assertEqual(self.client.post(setup,{'action':'unknown'}).status_code,400)
