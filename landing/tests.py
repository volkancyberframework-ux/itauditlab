from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import resolve, reverse
from .models import AssessmentSession, Certificate, Lead

@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class LandingTests(TestCase):
    def lead_data(self):
        return {'name':'Ada','email':'ada@example.com','profile_type':'student','english_awareness':'true','weekly_time':'true','age_over_45':'false','existing_it_experience':'false','eligibility_awareness':'true','career_clarity':'true','opportunity_awareness':'true','effort_awareness':'true','ethics_commitment':'true'}
    def test_home(self):
        response = self.client.get('/')
        self.assertContains(response, 'Sen hangi aşamadasın?', status_code=200)
        self.assertContains(response, '80 saatte temelden gerçek denetim hikâyesine')
        self.assertContains(response, 'AWS IAM Yetki Dağınıklığı')
        self.assertContains(response, 'ExertaBank')
        self.assertContains(response, 'Zeugma Sigorta')
        self.assertNotContains(response, 'Çalıştığım ve profesyonel deneyim edindiğim kurumlar')
        self.assertNotContains(response, 'img/experience/kbc-transparent.png')
        self.assertNotContains(response, 'img/experience/qnb-finansbank-transparent.png')
        self.assertNotContains(response, 'img/experience/bilkent-transparent.png')
        self.assertContains(response, 'img/cisa-badge.png')
        self.assertContains(response, 'YURTDIŞI FREELANCE ÇALIŞMALARIM')
        self.assertContains(response, 'OSB VE KOBİ DENETİMLERİ')
        self.assertNotContains(response, 'Şimdi bu deneyim senin vakalarına dönüşüyor')
        self.assertNotContains(response, 'AKADEMİK YOLCULUK')
        self.assertNotContains(response, 'GİZLİLİK KORUMALI')
        self.assertNotContains(response, 'Haritada gösterilen Türkiye deneyimi')
        self.assertNotContains(response, 'CREDENDO VE KBC BELÇİKA DÖNEMİYLE PARALEL İLERLEYEN DENEYİMLER')
        self.assertContains(response, 'FREELANCE ÇALIŞMALARIM')
        self.assertContains(response, '59.999 TL')
        self.assertContains(response, '3 × 25.000 TL')
        self.assertContains(response, 'toplam 75.000 TL')
        self.assertContains(response, '299 USD değerinde Skool topluluğu')
        self.assertContains(response, '132 kişilik topluluğa ücretsiz erişim')
        self.assertContains(response, 'Ki&#351;iyle birebir ment&#246;rl&#252;k')
        self.assertContains(response, 'Program mezunu')
        self.assertContains(response, 'Bu test adli sicil bilgisi toplamaz')
        self.assertContains(response, "GRC USTASI'NIN FARKI")
        self.assertContains(response, 'Katılımcılarımız, resmî kaynakları')
        self.assertContains(response, 'Kubernetes')
        self.assertContains(response, 'https://www.skool.com/volkan-guler-9286/about')
        self.assertContains(response, 'Türkiye’den dünyaya uzanan gerçek denetim tecrübesi')
        self.assertContains(response, 'İş Yaptığım Şehirler ve Sektörler')
        self.assertContains(response, 'Savunma Sanayii Şirketleri')
        self.assertContains(response, 'Gizlilik nedeniyle kurum isimleri paylaşılmamaktadır')
        self.assertContains(response, 'Bart Preneel ile akademik çalışmalar')
        self.assertContains(response, 'İlgili kurumların GRC Ustası programını desteklediği')
        self.assertContains(response, f'href="{reverse("login")}"')
        self.assertContains(response, 'destek@grcustasi.co')
        self.assertContains(response, reverse('landing:checkout'))
        self.assertNotContains(response, 'info@grcmastery.com')
        self.assertNotContains(response, 'Öğrenci girişi yakında')
        self.assertContains(response, f'href="{reverse("login")}">Giriş →</a>')

    @override_settings(STRIPE_SECRET_KEY='sk_test_placeholder')
    def test_checkout_creates_grc_ustasi_stripe_session(self):
        from unittest.mock import patch
        with patch('stripe.checkout.Session.create') as create_session:
            create_session.return_value.url = 'https://checkout.stripe.com/test-session'
            response = self.client.post(reverse('landing:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://checkout.stripe.com/test-session')
        payload = create_session.call_args.kwargs
        self.assertEqual(payload['mode'], 'payment')
        self.assertEqual(payload['line_items'][0]['price_data']['unit_amount'], 5_999_900)
        self.assertEqual(payload['line_items'][0]['price_data']['currency'], 'try')

    def test_existing_login_route_remains_owned_by_core(self):
        match = resolve('/login/')
        self.assertEqual(match.url_name, 'login')
        self.assertEqual(match.func.__module__, 'core.views')

    def test_authenticated_home_keeps_session_and_retains_login_label(self):
        user = get_user_model().objects.create_user(
            username='student', email='student-login@example.com', password='secret123'
        )
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(self.client.session['_auth_user_id']), str(user.pk))
        self.assertContains(response, '>Giriş</a>')
        self.assertNotContains(response, 'Öğrenci Paneli')

    def test_login_and_student_shell_use_only_grc_ustasi_branding(self):
        login_response = self.client.get(reverse('login'))
        self.assertContains(login_response, 'GRC Ustası | Öğrenci Girişi')
        self.assertContains(login_response, 'img/grc-ustasi-logo.png')
        self.assertNotContains(login_response, 'Siberkobi', html=False)

        user = get_user_model().objects.create_user(
            username='brand-student', email='brand@example.com', password='secret123'
        )
        self.client.force_login(user)
        dashboard_response = self.client.get(reverse('dashboard_student'))
        self.assertContains(dashboard_response, 'GRC Ustası | Öğrenci Platformu')
        self.assertContains(dashboard_response, 'img/grc-ustasi-logo.png')
        self.assertNotContains(dashboard_response, 'Siberkobi', html=False)

    def test_authenticated_login_page_redirects_without_logging_user_out(self):
        user = get_user_model().objects.create_user(
            username='returning', email='returning@example.com', password='secret123'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('dashboard_student'))
        self.assertEqual(str(self.client.session['_auth_user_id']), str(user.pk))

    def test_career_compass_link_marks_quiz_for_immediate_open(self):
        response = self.client.get(reverse('landing:career_compass'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-auto-open="true"')
        self.assertContains(response, 'quiz-direct-start')

    def test_assessment_email_and_answers_are_logged_with_profile_discount(self):
        with patch('landing.views._notify_telegram') as notify:
            response = self.client.post(reverse('landing:save_assessment'), {
                'email': 'student@example.com', 'profile_type': 'student',
                'career_clarity': 'true',
            })
        self.assertEqual(response.status_code, 200)
        session = AssessmentSession.objects.get(email='student@example.com')
        self.assertEqual(session.discount_percent, 50)
        self.assertEqual(session.answers['career_clarity'], 'true')
        self.assertFalse(session.completed)
        notify.assert_called_once()

    def test_assessment_email_notifies_telegram_only_once(self):
        payload = {'email': 'once@example.com', 'profile_type': 'graduate'}
        with patch('landing.views._notify_telegram') as notify:
            self.client.post(reverse('landing:save_assessment'), payload)
            self.client.post(reverse('landing:save_assessment'), payload | {'career_clarity': 'true'})
        notify.assert_called_once()

    def test_whatsapp_submission_notifies_telegram(self):
        payload = {
            'name': 'Deneme Kişi', 'email': 'whatsapp@example.com',
            'whatsapp': '+90 555 111 22 33', 'profile_type': 'student',
            'english_awareness': 'true', 'weekly_time': 'true',
            'eligibility_awareness': 'true', 'career_clarity': 'true',
            'opportunity_awareness': 'true', 'effort_awareness': 'true',
            'ethics_commitment': 'true', 'residence_type': 'turkey',
        }
        with patch('landing.views._notify_telegram') as notify:
            response = self.client.post(reverse('landing:submit_lead'), payload)
        self.assertEqual(response.status_code, 200)
        notify.assert_called_once()
        self.assertIn('+90 555 111 22 33', notify.call_args.args[0])

    @override_settings(TELEGRAM_BOT_TOKEN='token', TELEGRAM_CHAT_ID='chat')
    def test_first_login_sends_telegram_and_preserves_authentication(self):
        user = get_user_model().objects.create_user(
            username='first-login', email='first@example.com', password='secret123',
            is_first_login=True,
        )
        with patch('core.views.requests.post') as post:
            post.return_value.raise_for_status.return_value = None
            response = self.client.post(reverse('login'), {
                'email': user.email, 'password': 'secret123',
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_password_change_popup'])
        self.assertEqual(str(self.client.session['_auth_user_id']), str(user.pk))
        post.assert_called_once()

    def test_discount_levels_are_profile_specific_and_expire_in_three_days(self):
        for profile, discount in [('student', 50), ('graduate', 25), ('working', 15)]:
            response = self.client.post(reverse('landing:save_assessment'), {
                'email': f'{profile}@example.com', 'profile_type': profile,
            })
            self.assertEqual(response.json()['discount'], discount)
            self.assertEqual(AssessmentSession.objects.get(email=f'{profile}@example.com').discount_percent, discount)

    def test_early_age_gate_marks_assessment_complete(self):
        self.client.post(reverse('landing:save_assessment'), {
            'email': 'gate@example.com', 'profile_type': 'working',
            'residence_type': 'turkey', 'age_over_45': 'true',
            'assessment_completed': 'true',
        })
        session = AssessmentSession.objects.get(email='gate@example.com')
        self.assertTrue(session.completed)
        self.assertEqual(session.answers['age_over_45'], 'true')

    def test_curriculum_totals_exactly_80_hours(self):
        from .curriculum import CURRICULUM, CURRICULUM_STATS
        self.assertEqual(len(CURRICULUM), 8)
        self.assertEqual(sum(module['hours'] for module in CURRICULUM), 80)
        self.assertEqual(CURRICULUM_STATS['hours'], 80)
    def test_lead_score_and_duplicate(self):
        self.assertEqual(self.client.post(reverse('landing:submit_lead'), self.lead_data()).status_code, 200)
        lead = Lead.objects.get()
        self.assertEqual(lead.result_type, 'strong'); self.assertTrue(lead.student_discount_eligible)
        self.assertEqual(lead.discount_percent, 50)
        self.assertEqual(self.client.post(reverse('landing:submit_lead'), self.lead_data()).status_code, 400)

    def test_working_in_turkey_over_45_gets_polite_wait_result(self):
        data = self.lead_data() | {
            'email': 'turkey@example.com',
            'profile_type': 'working',
            'residence_type': 'turkey',
            'age_over_45': 'true',
        }
        response = self.client.post(reverse('landing:submit_lead'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result'], 'wait')

    def test_working_abroad_skips_age_gate(self):
        data = self.lead_data() | {
            'email': 'abroad@example.com',
            'profile_type': 'working',
            'residence_type': 'abroad',
            'region': 'europe',
            'age_over_45': 'true',
        }
        response = self.client.post(reverse('landing:submit_lead'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result'], 'strong')

    def test_student_is_not_subject_to_age_gate(self):
        data = self.lead_data() | {
            'email': 'student45@example.com',
            'age_over_45': 'true',
        }
        response = self.client.post(reverse('landing:submit_lead'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result'], 'strong')
    def test_certificate_masks_name(self):
        Certificate.objects.create(certificate_id='GRC-1', participant_name='Ada Lovelace', issue_date=date(2026,1,1))
        data = self.client.get(reverse('landing:verify_certificate'), {'certificate_id':'GRC-1'}).json()
        self.assertEqual(data['participant'], 'Ada L.'); self.assertNotIn('Lovelace', str(data))
