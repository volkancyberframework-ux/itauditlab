from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import LearningPath, Question, XPTransaction, Subscription


class LearningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="volkan",
            email="volkan@example.com",
            password="test-pass",
            first_name="Volkan",
            is_mobile=True,
            mobile_full_access=True,
        )
        self.other = get_user_model().objects.create_user(
            username="other", password="test-pass", is_mobile=True
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.path = LearningPath.objects.create(title="GRC", published=True)
        self.q = Question.objects.create(
            kind="choice",
            prompt="{first_name}, risk?",
            options=[{"id": "a", "text": "Risk"}],
            answer=["a"],
            published=True,
            base_xp=20,
        )
        self.q.paths.add(self.path)

    def session(self):
        response = self.client.post(
            "/api/mobile/v1/sessions/", {"path_id": self.path.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def answer(self, session, value):
        return self.client.post(
            f"/api/mobile/v1/sessions/{session['id']}/answer/",
            {"question_id": self.q.pk, "answer": value},
            format="json",
        )

    def test_answer_hidden_and_personalization(self):
        data = self.session()
        self.assertNotIn("answer", data["question"])
        self.assertEqual(data["question"]["prompt"], "Volkan, risk?")

    def test_retry_is_idempotent_and_server_progress(self):
        data = self.session()
        first = self.answer(data, ["a"])
        second = self.answer(data, ["a"])
        self.assertEqual(first.data["xp_change"], 20)
        self.assertEqual(second.data["xp_change"], 20)
        self.assertEqual(XPTransaction.objects.count(), 1)
        self.assertEqual(first.data["session"]["path"]["progress"], 100)

    def test_wrong_answer_never_negative(self):
        result = self.answer(self.session(), ["b"])
        self.assertEqual(result.data["xp_change"], 0)
        self.assertEqual(result.data["session"]["path"]["progress"], 0)

    def test_no_reward_twice_across_sessions(self):
        s1, s2 = self.session(), self.session()
        self.answer(s1, ["a"])
        self.assertEqual(self.answer(s2, ["a"]).data["xp_change"], 0)

    def test_session_owner_isolation(self):
        data = self.session()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.answer(data, ["a"]).status_code, 404)

    def test_premium_gate(self):
        self.user.mobile_full_access = False
        self.user.save()
        self.path.premium = True
        self.path.save()
        self.assertEqual(
            self.client.post(
                "/api/mobile/v1/sessions/", {"path_id": self.path.pk}
            ).status_code,
            403,
        )
        Subscription.objects.create(
            user=self.user,
            provider="test",
            transaction_id="test",
            status="active",
            expires_at=timezone.now() + timedelta(days=1),
            verified_at=timezone.now(),
        )
        self.session()

    def test_expired_subscription_denied(self):
        self.user.mobile_full_access = False
        self.user.save()
        self.path.premium = True
        self.path.save()
        Subscription.objects.create(
            user=self.user,
            provider="test",
            transaction_id="test",
            status="active",
            expires_at=timezone.now() - timedelta(seconds=1),
            verified_at=timezone.now(),
        )
        self.assertEqual(
            self.client.post(
                "/api/mobile/v1/sessions/", {"path_id": self.path.pk}
            ).status_code,
            403,
        )

    def test_login_uses_existing_account_and_refresh(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/mobile/v1/auth/login/",
            {"email": self.user.email, "password": "test-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(self.client.get("/api/mobile/v1/profile/").status_code, 200)
        refresh = self.client.post(
            "/api/mobile/v1/auth/refresh/",
            {"refresh": response.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh.status_code, 200)
        reused = self.client.post(
            "/api/mobile/v1/auth/refresh/",
            {"refresh": response.data["refresh"]},
            format="json",
        )
        self.assertEqual(reused.status_code, 401)

    def test_no_store_configuration_fails_closed(self):
        self.assertEqual(
            self.client.post(
                "/api/mobile/v1/subscriptions/sync/", {}, format="json"
            ).status_code,
            503,
        )

    def test_bad_path_id_returns_validation_error(self):
        self.assertEqual(
            self.client.post(
                "/api/mobile/v1/sessions/", {"path_id": "broken"}, format="json"
            ).status_code,
            400,
        )

    def test_unpublished_question_excluded(self):
        self.q.published = False
        self.q.save()
        self.assertEqual(
            self.client.post(
                "/api/mobile/v1/sessions/", {"path_id": self.path.pk}, format="json"
            ).status_code,
            400,
        )

    def test_relational_options_do_not_leak_correctness(self):
        from .models import QuestionOption

        QuestionOption.objects.create(
            question=self.q, key="b", text="New answer", correct=True
        )
        data = self.session()
        self.assertEqual(
            data["question"]["options"], [{"id": "b", "text": "New answer"}]
        )
        self.assertTrue(self.answer(data, ["b"]).data["correct"])

    def test_question_order_enforced(self):
        q2 = Question.objects.create(
            kind="choice",
            prompt="Later",
            options=[],
            answer=["a"],
            published=True,
            order=2,
        )
        q2.paths.add(self.path)
        data = self.session()
        response = self.client.post(
            f"/api/mobile/v1/sessions/{data['id']}/answer/",
            {"question_id": q2.pk, "answer": ["a"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_private_recording_owner_isolation(self):
        from .models import VoiceSubmission, QuestionAttempt, LearningSession

        session = LearningSession.objects.create(
            user=self.user, path=self.path, questions=[self.q.pk]
        )
        attempt = QuestionAttempt.objects.create(
            session=session, question=self.q, answer={}, is_correct=False
        )
        voice = VoiceSubmission.objects.create(
            attempt=attempt, file="recordings/missing.m4a", duration=3
        )
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.get(
                f"/api/mobile/v1/submissions/{voice.pk}/audio/"
            ).status_code,
            404,
        )

    def test_analytics_drops_unnecessary_attributes(self):
        from .models import AnalyticsEvent

        response = self.client.post(
            "/api/mobile/v1/events/",
            {"name": "question_answered", "email": "private@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(AnalyticsEvent.objects.get().name, "question_answered")

    def test_reset_email_contains_working_route(self):
        from django.core import mail

        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/mobile/v1/auth/password-reset/",
            {"email": self.user.email},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/mobile/v1/auth/reset/", mail.outbox[0].body)

    def test_free_voice_upload_validates_container_without_upsell(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import MobileSettings, VoiceSubmission
        MobileSettings.objects.update_or_create(pk=1, defaults={'free_path': self.path})
        self.user.mobile_full_access = False
        self.user.save()
        self.q.kind = "voice"
        self.q.answer = ['veri kaybı']
        self.q.premium = True  # The old feature flag must not gate free-path tasks.
        self.q.save()
        s = self.session()
        url = f"/api/mobile/v1/sessions/{s['id']}/voice/"
        self.assertEqual(self.client.post(url, {
            'question_id': self.q.pk, 'duration': 2,
            'file': SimpleUploadedFile('x.m4a', b'fake'),
        }).status_code, 400)
        audio = (__import__('pathlib').Path(__file__).parent / 'demo_assets' / 'mfa.m4a').read_bytes()
        result = self.client.post(url, {'question_id': self.q.pk, 'duration': 2,
            'file': SimpleUploadedFile('x.m4a', audio, content_type='audio/mp4')})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertIn('24 saat', result.data['detail'])
        self.assertTrue(result.data['session']['complete'])
        self.assertEqual(result.data['session']['pending_reviews'], 1)
        self.assertEqual(result.data['session']['path']['progress'], 100)
        retry = self.client.post(url, {'question_id': self.q.pk, 'duration': 2,
            'file': SimpleUploadedFile('x.m4a', audio)})
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(VoiceSubmission.objects.count(), 1)
        self.assertEqual(XPTransaction.objects.count(), 0)
        voice = VoiceSubmission.objects.get()
        voice.file.delete()

    def test_store_sync_uses_backend_identity_and_expiry(self):
        from unittest.mock import patch, Mock
        from django.test import override_settings

        response = Mock()
        response.json.return_value = {
            "subscriber": {
                "entitlements": {
                    "premium": {
                        "expires_date": (
                            timezone.now() + timedelta(days=1)
                        ).isoformat(),
                        "product_identifier": "grcustasi_premium_monthly",
                    }
                },
                "subscriptions": {"grcustasi_premium_monthly": {"store": "app_store"}},
            }
        }
        with override_settings(REVENUECAT_SECRET_KEY="server-only"), patch(
            "requests.get", return_value=response
        ) as get:
            result = self.client.post(
                "/api/mobile/v1/subscriptions/sync/", {"premium": True}, format="json"
            )
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.data["premium"])
            self.assertIn("Authorization", get.call_args.kwargs["headers"])

    def test_webhook_denies_unsigned_requests(self):
        self.assertEqual(
            self.client.post(
                "/api/mobile/v1/subscriptions/webhook/", {"event": {}}, format="json"
            ).status_code,
            403,
        )

    def test_premium_media_is_not_public(self):
        from .models import AudioAsset

        asset = AudioAsset.objects.create(
            title="private audio", file="audio/missing.mp3"
        )
        self.q.audio = asset
        self.q.premium = True
        self.q.save()
        self.assertEqual(
            self.client.get(f"/api/mobile/v1/audio/{asset.pk}/").status_code, 404
        )
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(f"/api/mobile/v1/audio/{asset.pk}/").status_code, 401
        )
        with self.assertRaises(ValueError):
            _ = asset.file.url

    def test_audio_manifest_uses_authorized_route(self):
        from .models import AudioAsset

        asset = AudioAsset.objects.create(title="intro", file="audio/missing.mp3")
        self.q.intro = asset
        self.q.save()
        data = self.session()
        self.assertIn(f"/api/mobile/v1/audio/{asset.pk}/", data["question"]["audio"][0])
        self.assertNotIn("/media/", data["question"]["audio"][0])

    def test_sentence_order_preserves_order_and_hides_solution(self):
        self.q.kind = 'sentence_order'
        self.q.options = [{'id': 'cause', 'text': 'Neden'}, {'id': 'event', 'text': 'Olay'}, {'id': 'impact', 'text': 'Etki'}]
        self.q.answer = ['cause', 'event', 'impact']
        self.q.save()
        session = self.session()
        self.assertNotIn('answer', session['question'])
        wrong = self.answer(session, ['impact', 'event', 'cause'])
        self.assertEqual(wrong.status_code, 200)
        self.assertFalse(wrong.data['correct'])
        correct = self.answer(self.session(), ['cause', 'event', 'impact'])
        self.assertTrue(correct.data['correct'])
        self.assertEqual(correct.data['xp_change'], 20)

    def test_interactive_answer_rejects_unknown_duplicate_and_empty_pieces(self):
        self.q.kind = 'sentence_order'
        self.q.save()
        session = self.session()
        for answer in [[], ['unknown'], ['a', 'a'], 'a', [1]]:
            self.assertEqual(self.answer(session, answer).status_code, 400)
        self.assertEqual(XPTransaction.objects.filter(user=self.user).count(), 0)

    def test_drag_select_requires_exactly_one_valid_card(self):
        self.q.kind = 'drag_select'
        self.q.options.append({'id': 'b', 'text': 'Distractor'})
        self.q.save()
        session = self.session()
        self.assertEqual(self.answer(session, ['a', 'b']).status_code, 400)
        self.assertTrue(self.answer(session, ['a']).data['correct'])

    def test_profile_starts_at_level_zero_and_admin_settings_change_thresholds(self):
        from .models import LevelSettings, LevelReward
        profile = self.client.get('/api/mobile/v1/profile/').data
        self.assertEqual(profile['level'], 0)
        self.assertEqual(profile['next_level_xp'], 100)
        settings = LevelSettings.objects.get(pk=1)
        settings.xp_per_level = 20
        settings.save()
        reward = LevelReward.objects.create(level=2, title='Özel hediye', kind='gift', published=True)
        self.answer(self.session(), ['a'])
        profile = self.client.get('/api/mobile/v1/profile/').data
        self.assertEqual(profile['level'], 1)
        gift = next(r for r in profile['rewards'] if r['id'] == reward.pk)
        self.assertEqual(gift['required_xp'], 40)
        self.assertEqual(gift['remaining_xp'], 20)
        self.assertFalse(gift['unlocked'])

    def test_reward_is_earned_once_and_survives_later_xp_deduction(self):
        from .models import UserLevelReward, LevelReward
        from .levels import level_data
        self.q.base_xp = 100
        self.q.save()
        result = self.answer(self.session(), ['a'])
        reward = LevelReward.objects.get(level=1)
        self.assertTrue(result.data['correct'])
        self.assertTrue(UserLevelReward.objects.filter(user=self.user, reward=reward).exists())
        level_data(100, self.user)
        self.assertEqual(UserLevelReward.objects.filter(user=self.user, reward=reward).count(), 1)
        data = level_data(95, self.user)
        self.assertEqual(data['level'], 0)
        self.assertTrue(next(r for r in data['rewards'] if r['id'] == reward.pk)['unlocked'])

    def test_unpublished_rewards_hidden_and_gift_delivery_visible(self):
        from .models import LevelReward, UserLevelReward
        hidden = LevelReward.objects.create(level=8, title='Taslak hediye', published=False)
        gift = LevelReward.objects.create(level=0, title='Karşılama hediyesi', kind='gift', published=True)
        profile = self.client.get('/api/mobile/v1/profile/').data
        self.assertNotIn(hidden.pk, [r['id'] for r in profile['rewards']])
        claim = UserLevelReward.objects.get(user=self.user, reward=gift)
        claim.delivered_at = timezone.now()
        claim.save()
        profile = self.client.get('/api/mobile/v1/profile/').data
        self.assertTrue(next(r for r in profile['rewards'] if r['id'] == gift.pk)['delivered'])


class MobileAccessTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="mobile_access", email="access@example.com",
            password="test-pass", is_mobile=True,
        )
        self.client = APIClient()

    def login(self):
        return self.client.post("/api/mobile/v1/auth/login/", {
            "email": self.user.email, "password": "test-pass",
        }, format="json")

    def test_website_only_account_cannot_login(self):
        self.user.is_mobile = False
        self.user.save()
        self.assertEqual(self.login().status_code, 401)

    def test_mobile_account_is_distinct_from_same_email_website_account(self):
        get_user_model().objects.create_user(
            username="website_access", email=self.user.email, password="web-pass",
        )
        self.assertEqual(self.login().status_code, 200)

    def test_blank_last_date_is_unlimited(self):
        self.assertIsNone(self.user.mobile_last_date)
        self.assertEqual(self.login().status_code, 200)

    def test_last_date_is_inclusive_in_istanbul_timezone(self):
        from unittest.mock import patch
        from datetime import datetime, timezone as dt_timezone
        self.user.mobile_last_date = timezone.localdate()
        self.user.save()
        # UTC 21:00 is already the next day in Turkey.
        boundary = datetime.combine(self.user.mobile_last_date, datetime.min.time()).replace(
            hour=21, tzinfo=dt_timezone.utc
        )
        with timezone.override("Europe/Istanbul"):
            with patch("django.utils.timezone.now", return_value=boundary - timedelta(seconds=1)):
                self.assertEqual(self.login().status_code, 200)
            with patch("django.utils.timezone.now", return_value=boundary):
                self.assertEqual(self.login().status_code, 403)

    def test_expired_account_cannot_login(self):
        self.user.mobile_last_date = timezone.localdate() - timedelta(days=1)
        self.user.save()
        self.assertEqual(self.login().status_code, 403)

    def test_existing_tokens_stop_working_after_access_is_removed_or_expired(self):
        tokens = self.login().data
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        self.assertEqual(self.client.get("/api/mobile/v1/profile/").status_code, 200)
        for attrs in [
            {"is_mobile": False},
            {"is_mobile": True, "mobile_last_date": timezone.localdate() - timedelta(days=1)},
            {"is_mobile": True, "mobile_last_date": None, "is_active": False},
        ]:
            get_user_model().objects.filter(pk=self.user.pk).update(**attrs)
            self.assertIn(self.client.get("/api/mobile/v1/profile/").status_code, [401, 403])
            self.assertIn(self.client.post("/api/mobile/v1/auth/refresh/", {
                "refresh": tokens["refresh"],
            }, format="json").status_code, [401, 403])

    def test_mobile_reset_does_not_send_to_website_only_account(self):
        from django.core import mail
        self.user.is_mobile = False
        self.user.save()
        response = self.client.post("/api/mobile/v1/auth/password-reset/", {
            "email": self.user.email,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)


class AllTypesDemoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='all-types', is_mobile=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.path = LearningPath.objects.get(title='Demo • Tüm Soru Tipleri', owner=None)

    def test_every_type_once_in_one_session_and_assets_authorized(self):
        self.assertCountEqual(self.path.questions.values_list('kind', flat=True), [k for k, _ in Question.TYPES])
        response = self.client.post('/api/mobile/v1/sessions/', {'path_id': self.path.pk}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['total'], 11)
        self.assertEqual(response.data['question_total'], 10)
        self.assertEqual(response.data['path']['session_size'], 10)
        from .storage import PrivateVoiceStorage
        storage = PrivateVoiceStorage()
        for name, signature in [('demo/access-review.png', b'\x89PNG'), ('demo/mfa.m4a', None)]:
            with storage.open(name) as file:
                data = file.read()
            self.assertGreater(len(data), 1000)
            if signature:
                self.assertTrue(data.startswith(signature))
            else:
                self.assertIn(b'ftyp', data[:32])
        with self.assertRaises(FileNotFoundError):
            storage.open('demo/../storage.py')
        image = self.path.questions.get(kind='image')
        audio = self.path.questions.get(kind='audio')
        for url in [f'/api/mobile/v1/questions/{image.pk}/image/', f'/api/mobile/v1/audio/{audio.audio_id}/']:
            result = self.client.get(url)
            self.assertEqual(result.status_code, 200)
            result.close()
            self.client.force_authenticate(None)
            self.assertIn(self.client.get(url).status_code, [401, 403])
            self.client.force_authenticate(self.user)

    def test_nine_automatic_questions_advance_to_voice(self):
        s = self.client.post('/api/mobile/v1/sessions/', {'path_id': self.path.pk}, format='json').data
        for q in self.path.questions.exclude(kind='voice'):
            if q.kind == 'info':
                s = self.client.post(f"/api/mobile/v1/sessions/{s['id']}/continue/", {'question_id': q.pk}, format='json').data
                continue
            self.assertEqual(s['question']['id'], q.pk)
            value = q.answer[0] if q.kind in ['text', 'fill_blank'] else q.answer
            result = self.client.post(f"/api/mobile/v1/sessions/{s['id']}/answer/", {'question_id': q.pk, 'answer': value}, format='json')
            self.assertEqual(result.status_code, 200, result.data)
            self.assertTrue(result.data['correct'])
            s = result.data['session']
        self.assertEqual(s['question']['kind'], 'voice')
        self.assertEqual(s['answered'], 10)
        self.assertEqual(s['information_read'], 1)


class MobileProductTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        from .models import MobileSettings
        cache.clear()
        self.user = get_user_model().objects.create_user(username='free', email='free@example.com', is_mobile=True)
        self.path = LearningPath.objects.create(title='Free', published=True, premium=True)
        self.other_path = LearningPath.objects.create(title='Full', published=True)
        MobileSettings.objects.update_or_create(pk=1, defaults={'free_path': self.path})
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_registration_creates_free_mobile_account_and_prevents_escalation(self):
        self.client.force_authenticate(None)
        result = self.client.post('/api/mobile/v1/auth/register/', {
            'name': 'Yeni Öğrenci', 'email': ' NEW@example.com ', 'password': 'StrongDemo!45823',
            'is_staff': True, 'is_superuser': True, 'mobile_full_access': True,
        }, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        user = get_user_model().objects.get(email='new@example.com')
        self.assertTrue(user.is_mobile)
        self.assertFalse(user.mobile_full_access or user.is_staff or user.is_superuser)
        self.assertIsNone(user.mobile_last_date)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+result.data['access'])
        self.assertEqual([p['id'] for p in self.client.get('/api/mobile/v1/paths/').data], [self.path.pk])
        self.assertFalse(self.client.get('/api/mobile/v1/profile/').data['premium'])
        self.assertEqual(self.client.post('/api/mobile/v1/auth/register/', {
            'name': 'Duplicate', 'email': 'NEW@example.com', 'password': 'StrongDemo!45823',
        }, format='json').status_code, 400)

    def test_registration_validates_email_password_and_keeps_website_accounts_separate(self):
        self.client.force_authenticate(None)
        for email, password in [('bad', 'StrongDemo!45823'), ('weak@example.com', '123')]:
            result = self.client.post('/api/mobile/v1/auth/register/', {'name': 'New', 'email': email, 'password': password}, format='json')
            self.assertEqual(result.status_code, 400)
        get_user_model().objects.create_user(username='web-only', email='separate@example.com')
        result = self.client.post('/api/mobile/v1/auth/register/', {'name': 'Mobile', 'email': 'separate@example.com', 'password': 'StrongDemo!45823'}, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(get_user_model().objects.filter(email='separate@example.com').count(), 2)

    def test_free_path_selection_controls_visibility_and_all_task_features(self):
        from .models import MobileSettings
        self.assertEqual([p['id'] for p in self.client.get('/api/mobile/v1/paths/').data], [self.path.pk])
        self.assertEqual(self.client.post('/api/mobile/v1/sessions/', {'path_id': self.other_path.pk}, format='json').status_code, 403)
        MobileSettings.objects.filter(pk=1).update(free_path=self.other_path)
        self.assertEqual([p['id'] for p in self.client.get('/api/mobile/v1/paths/').data], [self.other_path.pk])
        self.user.mobile_full_access = True
        self.user.save()
        self.assertIn(self.path.pk, [p['id'] for p in self.client.get('/api/mobile/v1/paths/').data])

    def test_long_path_batches_questions_and_inserts_cards_without_xp(self):
        for order in range(101):
            q = Question.objects.create(kind='choice', prompt=str(order), options=[{'id':'a','text':'A'}], answer=['a'], published=True, premium=True, order=order*2)
            q.paths.add(self.path)
        card = Question.objects.create(kind='info', prompt='Learn', card_pages=[{'title':'Risk','body':'**Neden** → *olay* → etki'}], published=True, order=5)
        card.paths.add(self.path)
        session = self.client.post('/api/mobile/v1/sessions/', {'path_id': self.path.pk}, format='json').data
        self.assertEqual(session['total'], 9)
        self.assertEqual(session['question_total'], 8)
        self.assertEqual(session['path']['question_count'], 101)
        self.assertEqual(session['path']['information_count'], 1)
        for _ in range(3):
            qid = session['question']['id']
            result = self.client.post(f"/api/mobile/v1/sessions/{session['id']}/answer/", {'question_id': qid, 'answer':['a']}, format='json')
            self.assertEqual(result.status_code, 200, result.data)
            session = result.data['session']
        self.assertEqual(session['question']['kind'], 'info')
        self.assertEqual(session['path']['completed'], 3)
        transactions = XPTransaction.objects.count()
        url = f"/api/mobile/v1/sessions/{session['id']}/continue/"
        for _ in range(2):
            result = self.client.post(url, {'question_id': card.pk}, format='json')
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data['answered'], 4)
            self.assertEqual(result.data['path']['completed'], 3)
        self.assertEqual(XPTransaction.objects.count(), transactions)
        self.assertEqual(result.data['correct'], 3)

    def test_voice_question_accepts_one_written_answer(self):
        q = Question.objects.create(kind='voice', prompt='Risk?', answer=['veri kaybı'], published=True, premium=True)
        q.paths.add(self.path)
        session = self.client.post('/api/mobile/v1/sessions/', {'path_id': self.path.pk}, format='json').data
        result = self.client.post(f"/api/mobile/v1/sessions/{session['id']}/answer/", {'question_id':q.pk, 'answer':' Veri Kaybı '}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertTrue(result.data['correct'])
        self.assertTrue(result.data['session']['complete'])

    def test_feedback_email_is_retryable_and_sent_once(self):
        from unittest.mock import patch
        from django.core import mail
        from .models import VoiceSubmission
        from .feedback import send_voice_feedback
        q = Question.objects.create(kind='voice', prompt='Risk?', answer=['veri kaybı'])
        session = __import__('mobile_api.models', fromlist=['LearningSession']).LearningSession.objects.create(user=self.user, path=self.path, questions=[q.pk])
        attempt = __import__('mobile_api.models', fromlist=['QuestionAttempt']).QuestionAttempt.objects.create(session=session, question=q, answer={'review':'pending'}, is_correct=False)
        voice = VoiceSubmission.objects.create(attempt=attempt, file='missing.m4a', duration=2, review_status='reviewed', feedback='Etkiyi daha somut anlatabilirsin.')
        self.assertEqual(voice.review_due_at - voice.created_at, timedelta(hours=24))
        with patch('mobile_api.feedback.send_mail', side_effect=RuntimeError('SMTP unavailable')):
            with self.assertRaises(RuntimeError):
                send_voice_feedback(voice.pk)
        voice.refresh_from_db()
        self.assertIsNone(voice.feedback_sent_at)
        self.assertTrue(send_voice_feedback(voice.pk))
        self.assertFalse(send_voice_feedback(voice.pk))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['free@example.com'])
        self.assertIn(voice.feedback, mail.outbox[0].body)

    def test_admin_requires_single_voice_answer_and_valid_information_pages(self):
        from .admin import QuestionForm
        form = QuestionForm(data={'kind':'voice', 'prompt':'Risk?', 'answer':'["a", "b"]', 'base_xp':10, 'order':0, 'difficulty':'beginner'})
        self.assertFalse(form.is_valid())
        self.assertIn('answer', form.errors)
        form = QuestionForm(data={'kind':'info', 'prompt':'Read', 'card_pages':'[{"body": 9}]', 'base_xp':0, 'order':0, 'difficulty':'beginner'})
        self.assertFalse(form.is_valid())
        self.assertIn('card_pages', form.errors)


class ProfileContactAndPasswordTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = get_user_model().objects.create_user(username='password-test', email='password@example.com', password='Original!Pass1357', is_mobile=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_admin_number_formats_normalize_and_profile_updates(self):
        from .contacts import whatsapp_number
        from .models import MobileSettings
        from django.core.exceptions import ValidationError
        for value in ['0032 476 073 171', '+32 476 073 171', '32476073171']:
            self.assertEqual(whatsapp_number(value), '32476073171')
        for value in ['0476 073 171', 'https://example.com', '123', '+32hello']:
            with self.assertRaises(ValidationError):
                whatsapp_number(value)
        MobileSettings.objects.filter(pk=1).update(whatsapp_phone='0032 476 073 171')
        contact = self.client.get('/api/mobile/v1/profile/').data['contact']
        self.assertEqual(contact['whatsapp_url'], 'https://wa.me/32476073171')
        MobileSettings.objects.filter(pk=1).update(whatsapp_phone='+90 532 123 45 67')
        self.assertEqual(self.client.get('/api/mobile/v1/profile/').data['contact']['phone'], '905321234567')
        MobileSettings.objects.filter(pk=1).update(whatsapp_phone='')
        self.assertIsNone(self.client.get('/api/mobile/v1/profile/').data['contact']['whatsapp_url'])

    def change(self, current, password, confirm=None):
        return self.client.post('/api/mobile/v1/auth/change-password/', {'current_password':current, 'new_password':password, 'confirm_password':password if confirm is None else confirm}, format='json')

    def test_wrong_current_mismatch_and_weak_password_do_not_change_credentials(self):
        for current, password, confirm in [('Wrong!Pass1357', 'New!Pass02468', None), ('Original!Pass1357','New!Pass02468','different'), ('Original!Pass1357','123',None), ('Original!Pass1357','Original!Pass1357',None)]:
            self.assertEqual(self.change(current,password,confirm).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Original!Pass1357'))

    def test_password_change_revokes_old_tokens_and_returns_a_working_new_session(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        old = RefreshToken.for_user(self.user)
        old_access = str(old.access_token)
        result = self.change('Original!Pass1357', 'New!Pass02468')
        self.assertEqual(result.status_code, 200, result.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('New!Pass02468'))
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+old_access)
        self.assertEqual(self.client.get('/api/mobile/v1/profile/').status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+result.data['access'])
        self.assertEqual(self.client.get('/api/mobile/v1/profile/').status_code, 200)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/mobile/v1/auth/refresh/', {'refresh':str(old)}, format='json').status_code, 401)
        self.assertEqual(self.client.post('/api/mobile/v1/auth/refresh/', {'refresh':result.data['refresh']}, format='json').status_code, 200)

    def test_password_change_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.change('Original!Pass1357','New!Pass02468').status_code, 401)
