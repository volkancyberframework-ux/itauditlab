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

    def test_voice_upload_requires_premium_and_container(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        s = self.session()
        self.q.kind = "voice"
        self.q.save()
        url = f"/api/mobile/v1/sessions/{s['id']}/voice/"
        self.assertEqual(
            self.client.post(
                url,
                {
                    "question_id": self.q.pk,
                    "duration": 2,
                    "file": SimpleUploadedFile("x.m4a", b"fake"),
                },
            ).status_code,
            403,
        )
        Subscription.objects.create(
            user=self.user,
            provider="test",
            transaction_id="voice",
            status="active",
            expires_at=timezone.now() + timedelta(days=1),
            verified_at=timezone.now(),
        )
        self.assertEqual(
            self.client.post(
                url,
                {
                    "question_id": self.q.pk,
                    "duration": 2,
                    "file": SimpleUploadedFile("x.m4a", b"fake"),
                },
            ).status_code,
            400,
        )

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
