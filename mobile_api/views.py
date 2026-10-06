from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .access import (
    MobileAccessPermission, MobileTokenRefreshSerializer,
    MobilePasswordResetForm, check_mobile_access,
)
from .levels import level_data
from .models import (
    LearningPath,
    Question,
    LearningSession,
    QuestionAttempt,
    UserPathProgress,
    XPTransaction,
    Subscription,
    BillingIdentity,
)


class MobileThrottle(UserRateThrottle):
    scope = "mobile"


class LoginThrottle(AnonRateThrottle):
    scope = "mobile_login"


class MobileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, MobileAccessPermission]
    throttle_classes = [MobileThrottle]


class Login(MobileView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        password = request.data.get("password", "")
        users = list(get_user_model().objects.filter(email__iexact=email, is_mobile=True)[:2])
        # Legacy emails are not unique. Fail closed until the administrator resolves duplicates.
        username = users[0].get_username() if len(users) == 1 else "__mobile_invalid__"
        user = authenticate(request=request, username=username, password=password)
        if not user or len(users) != 1:
            return Response(
                {"detail": "E-posta veya şifreyi kontrol eder misin?"}, status=401
            )
        check_mobile_access(user)
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class Refresh(TokenRefreshView):
    throttle_classes = [LoginThrottle]
    serializer_class = MobileTokenRefreshSerializer


class Logout(MobileView):
    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh", ""))
            if str(token["user_id"]) != str(request.user.pk):
                raise ValueError()
            token.blacklist()
        except Exception:
            raise ValidationError("Oturum anahtarı geçersiz.")
        return Response(status=204)


def xp(user):
    return (
        XPTransaction.objects.filter(user=user).aggregate(total=Sum("amount"))["total"]
        or 0
    )


def premium(user):
    return Subscription.objects.filter(
        user=user,
        status__in=["active", "trial", "grace_period"],
        expires_at__gt=timezone.now(),
    ).exists()


def integer_id(value):
    if (
        isinstance(value, str)
        and value.isascii()
        and value.isdigit()
        and len(value) < 12
    ):
        value = int(value)
    if type(value) is not int or value <= 0:
        raise ValidationError("Geçerli bir yol seç.")
    return value


def options(q):
    rows = list(q.answer_options.all())
    return (
        (
            [{"id": r.key, "text": r.text} for r in rows],
            [r.key for r in rows if r.correct],
        )
        if rows
        else (q.options, q.answer)
    )


def paths(user):
    return LearningPath.objects.filter(published=True).filter(
        Q(owner=None) | Q(owner=user)
    )


def accessible_questions(path, user):
    qs = path.questions.filter(published=True)
    if not premium(user):
        if path.premium:
            raise PermissionDenied("Bu yol Premium üyeliğe açık.")
        qs = qs.filter(premium=False)
    return qs


def path_data(path, user):
    total = path.questions.filter(published=True).count()
    progress = UserPathProgress.objects.filter(user=user, path=path).first()
    done = (
        progress.completed.filter(published=True, paths=path).count() if progress else 0
    )
    return {
        "id": path.pk,
        "title": path.title,
        "description": path.description,
        "icon": path.icon,
        "color": path.color,
        "difficulty": path.difficulty,
        "minutes": path.minutes,
        "premium": path.premium,
        "question_count": total,
        "completed": done,
        "progress": round(done / total * 100) if total else 0,
    }


class Profile(MobileView):
    def get(self, request):
        total_xp = xp(request.user)
        return Response(
            {
                "id": request.user.pk,
                "billing_id": str(
                    BillingIdentity.objects.get_or_create(user=request.user)[0].pk
                ),
                "first_name": request.user.first_name or request.user.username,
                "full_name": request.user.get_full_name(),
                "xp": total_xp,
                **level_data(total_xp, request.user),
                "premium": premium(request.user),
                "completed": QuestionAttempt.objects.filter(
                    session__user=request.user, is_correct=True
                )
                .values("question")
                .distinct()
                .count(),
            }
        )


class Paths(MobileView):
    def get(self, request):
        return Response([path_data(p, request.user) for p in paths(request.user)])


class Personalize(MobileView):
    def post(self, request):
        if not premium(request.user):
            raise PermissionDenied("Kişisel yollar Premium üyeliğe açık.")
        level = request.data.get("level")
        minutes = request.data.get("minutes")
        source = (
            paths(request.user)
            .filter(pk=integer_id(request.data.get("path_id")), owner=None)
            .first()
        )
        if (
            not source
            or level not in ["beginner", "intermediate", "advanced"]
            or minutes not in [5, 10, 20]
        ):
            raise ValidationError("Yol, seviye ve süre seçimini kontrol et.")
        from .recommendations import RuleRecommendationProvider

        ids = RuleRecommendationProvider().recommend(
            accessible_questions(source, request.user),
            level=level,
            minutes=minutes,
            goal=str(request.data.get("goal", ""))[:120],
        )
        if not ids:
            raise ValidationError(
                "Bu seviyede henüz içerik yok. Başka bir seviye deneyebilirsin."
            )
        with transaction.atomic():
            p = LearningPath.objects.create(
                title=f"{source.title} • Bana özel",
                owner=request.user,
                published=True,
                premium=True,
                minutes=minutes,
                difficulty=level,
                preferences={
                    "source": source.pk,
                    "goal": str(request.data.get("goal", ""))[:120],
                },
            )
            p.questions.set(ids)
        return Response(path_data(p, request.user), status=201)


def render_text(text, user, path):
    values = {
        "first_name": user.first_name or user.username,
        "full_name": user.get_full_name(),
        "current_path": path.title,
        "xp": str(xp(user)),
        "level": str(level_data(xp(user))["level"]),
    }
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def question_data(q, session, request):
    audio = []
    if q.intro:
        audio.append(request.build_absolute_uri(f"/api/mobile/v1/audio/{q.intro_id}/"))
        name = (
            q.intro.__class__.objects.filter(
                name_key=request.user.first_name.casefold()
            ).first()
            if request.user.first_name
            else None
        )
        if name:
            audio.append(request.build_absolute_uri(f"/api/mobile/v1/audio/{name.pk}/"))
    if q.audio:
        audio.append(request.build_absolute_uri(f"/api/mobile/v1/audio/{q.audio_id}/"))
    return {
        "id": q.pk,
        "kind": q.kind,
        "prompt": render_text(q.prompt, request.user, session.path),
        "context": render_text(q.context, request.user, session.path),
        "options": options(q)[0],
        "image": (
            request.build_absolute_uri(f"/api/mobile/v1/questions/{q.pk}/image/")
            if q.image
            else None
        ),
        "audio": audio,
        "base_xp": q.base_xp,
    }


def session_data(session, request):
    answered = set(session.attempts.values_list("question_id", flat=True))
    remaining = [pk for pk in session.questions if pk not in answered]
    q = (
        Question.objects.filter(pk=remaining[0], published=True).first()
        if remaining
        else None
    )
    if remaining and not q:
        raise ValidationError(
            "Bu görev güncellendi. Ana sayfadan yeni bir oturum başlatabilirsin."
        )
    if q and q.pk not in accessible_questions(session.path, request.user).values_list(
        "pk", flat=True
    ):
        raise PermissionDenied("Bu içerik için üyelik gerekli.")
    return {
        "id": str(session.pk),
        "total": len(session.questions),
        "answered": len(answered),
        "question": question_data(q, session, request) if q else None,
        "complete": not remaining,
        "correct": session.attempts.filter(is_correct=True).count(),
        "xp_earned": session.attempts.aggregate(total=Sum("xp_change"))["total"] or 0,
        "path": path_data(session.path, request.user),
    }


class Sessions(MobileView):
    def post(self, request):
        p = (
            paths(request.user)
            .filter(pk=integer_id(request.data.get("path_id")))
            .first()
        )
        if not p:
            raise ValidationError("Öğrenme yolu bulunamadı.")
        qs = accessible_questions(p, request.user)
        progress = UserPathProgress.objects.filter(user=request.user, path=p).first()
        if progress:
            qs = qs.exclude(pk__in=progress.completed.values("pk"))
        ids = list(qs.values_list("pk", flat=True)[:8])
        if not ids:
            raise ValidationError("Bu yoldaki erişilebilir görevleri tamamladın.")
        s = LearningSession.objects.create(user=request.user, path=p, questions=ids)
        return Response(session_data(s, request), status=201)


class SessionDetail(MobileView):
    def get(self, request, pk):
        s = LearningSession.objects.filter(pk=pk, user=request.user).first()
        if not s:
            return Response(status=404)
        return Response(session_data(s, request))


class Answer(MobileView):
    def post(self, request, pk):
        with transaction.atomic():
            # Lock user as well as session: XP remains consistent across simultaneous sessions.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            s = (
                LearningSession.objects.select_for_update()
                .filter(pk=pk, user=request.user)
                .first()
            )
            if not s:
                return Response(status=404)
            qid = request.data.get("question_id")
            if type(qid) is not int or qid not in s.questions:
                raise ValidationError("Soru bu oturuma ait değil.")
            q = accessible_questions(s.path, request.user).filter(pk=qid).first()
            if not q:
                raise PermissionDenied("İçeriğe erişilemiyor.")
            previous = s.attempts.filter(question=q).first()
            if previous:
                return Response(
                    {
                        "correct": previous.is_correct,
                        "xp_change": previous.xp_change,
                        "explanation": q.explanation,
                        "hint": q.hint,
                        "session": session_data(s, request),
                    }
                )
            answered = set(s.attempts.values_list("question_id", flat=True))
            if qid != next((i for i in s.questions if i not in answered), None):
                raise ValidationError("Önce mevcut görevi tamamla.")
            answer = request.data.get("answer")
            if q.kind == "voice":
                raise ValidationError("Sesli yanıt yükleme henüz etkin değil.")
            if q.kind in ["text", "fill_blank"]:
                if not isinstance(answer, str) or len(answer) > 4000:
                    raise ValidationError("Geçerli bir metin gir.")
                correct = answer.strip().casefold() in [
                    str(a).strip().casefold() for a in q.answer
                ]
            elif q.kind in ["sentence_order", "drag_select"]:
                keys = {option["id"] for option in options(q)[0]}
                if (
                    not isinstance(answer, list)
                    or not answer
                    or len(answer) > 30
                    or any(not isinstance(a, str) or a not in keys for a in answer)
                    or len(set(answer)) != len(answer)
                    or (q.kind == "drag_select" and len(answer) != 1)
                ):
                    raise ValidationError("Cümle parçalarını veya risk kartını seç.")
                correct = answer == q.answer if q.kind == "sentence_order" else set(answer) == set(options(q)[1])
            else:
                if (
                    not isinstance(answer, list)
                    or any(not isinstance(a, str) for a in answer)
                    or len(answer) > 30
                ):
                    raise ValidationError("Bir yanıt seç.")
                correct = bool(answer) and set(answer) == set(options(q)[1])
            duration = request.data.get("duration_seconds", 0)
            if type(duration) is not int or not 0 <= duration <= 86400:
                raise ValidationError("Süre geçersiz.")
            already_rewarded = QuestionAttempt.objects.filter(
                session__user=request.user, question=q, is_correct=True
            ).exists()
            delta = (
                (0 if already_rewarded else q.base_xp)
                if correct
                else -min(5, xp(request.user))
            )
            a = QuestionAttempt.objects.create(
                session=s,
                question=q,
                answer=answer,
                is_correct=correct,
                xp_change=delta,
                duration_seconds=duration,
            )
            XPTransaction.objects.create(
                user=request.user,
                attempt=a,
                amount=delta,
                reason="correct" if correct else "practice",
            )
            level_data(xp(request.user), request.user)
            progress, _ = UserPathProgress.objects.get_or_create(
                user=request.user, path=s.path
            )
            if correct:
                progress.completed.add(q)
            progress.save()
            if s.attempts.count() == len(s.questions):
                s.completed_at = timezone.now()
                s.save(update_fields=["completed_at"])
            return Response(
                {
                    "correct": correct,
                    "xp_change": delta,
                    "explanation": render_text(q.explanation, request.user, s.path),
                    "hint": q.hint,
                    "session": session_data(s, request),
                }
            )


class Voice(MobileView):
    def post(self, request, pk):
        import uuid
        from .models import VoiceSubmission

        if not premium(request.user):
            raise PermissionDenied("Sesli yanıtlar Premium üyeliğe açık.")
        upload = request.FILES.get("file")
        try:
            duration = int(request.data.get("duration", 0))
            qid = int(request.data.get("question_id", 0))
        except (TypeError, ValueError):
            raise ValidationError("Kayıt bilgileri geçersiz.")
        if (
            not upload
            or not 0 < upload.size <= 10 * 1024 * 1024
            or not 1 <= duration <= 180
        ):
            raise ValidationError("En fazla 3 dakika ve 10 MB ses gönderebilirsin.")
        # Inspect the container signature rather than trusting a filename or MIME header.
        head = upload.read(16)
        upload.seek(0)
        if len(head) < 12 or head[4:8] != b"ftyp":
            raise ValidationError("M4A ses kaydı gerekli.")
        upload.name = f"{uuid.uuid4()}.m4a"
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            s = (
                LearningSession.objects.select_for_update()
                .filter(pk=pk, user=request.user)
                .first()
            )
            if not s:
                return Response(status=404)
            q = (
                accessible_questions(s.path, request.user)
                .filter(pk=qid, kind="voice")
                .first()
            )
            if not q or qid not in s.questions:
                raise ValidationError("Sesli soru bulunamadı.")
            previous = s.attempts.filter(question=q).first()
            if not previous:
                answered = set(s.attempts.values_list("question_id", flat=True))
                if qid != next((i for i in s.questions if i not in answered), None):
                    raise ValidationError("Önce mevcut görevi tamamla.")
                a = QuestionAttempt.objects.create(
                    session=s,
                    question=q,
                    answer={"review": "pending"},
                    is_correct=False,
                    duration_seconds=duration,
                )
                VoiceSubmission.objects.create(
                    attempt=a, file=upload, duration=duration
                )
                if s.attempts.count() == len(s.questions):
                    s.completed_at = timezone.now()
                    s.save(update_fields=["completed_at"])
        return Response(
            {
                "detail": "Yanıtın bize ulaştı 🎙️ İnceledikten sonra geri bildirimini e-posta adresine göndereceğiz.",
                "session": session_data(s, request),
            }
        )


class VoiceDownload(MobileView):
    def get(self, request, pk):
        from django.http import FileResponse
        from .models import VoiceSubmission

        qs = VoiceSubmission.objects.all()
        if not request.user.is_staff:
            qs = qs.filter(attempt__session__user=request.user)
        voice = qs.filter(pk=pk).first()
        if not voice:
            return Response(status=404)
        try:
            return FileResponse(voice.file.open("rb"), content_type="audio/mp4")
        except FileNotFoundError:
            return Response(status=404)


class SubscriptionSync(MobileView):
    def post(self, request):
        # Never trust a client purchase flag. RevenueCat validates StoreKit/Play transactions.
        from django.conf import settings
        from django.utils.dateparse import parse_datetime
        import requests

        if not settings.REVENUECAT_SECRET_KEY:
            return Response(
                {"detail": "Mağaza üyeliği henüz yapılandırılmadı."}, status=503
            )
        try:
            response = requests.get(
                f"https://api.revenuecat.com/v1/subscribers/{BillingIdentity.objects.get_or_create(user=request.user)[0].pk}",
                headers={"Authorization": f"Bearer {settings.REVENUECAT_SECRET_KEY}"},
                timeout=10,
            )
            response.raise_for_status()
            subscriber = response.json()["subscriber"]
        except (requests.RequestException, KeyError, ValueError):
            return Response(
                {"detail": "Üyeliğin doğrulanamadı. Tekrar deneyebilirsin."}, status=503
            )
        entitlement = subscriber.get("entitlements", {}).get("premium")
        if not entitlement:
            Subscription.objects.filter(user=request.user).update(status="expired")
            return Response({"premium": False})
        expiry = parse_datetime(entitlement.get("expires_date") or "")
        product = entitlement.get("product_identifier")
        if not expiry or product != "grcustasi_premium_monthly":
            raise ValidationError("Üyelik ürünü doğrulanamadı.")
        detail = subscriber.get("subscriptions", {}).get(product, {})
        grace = parse_datetime(detail.get("grace_period_expires_date") or "")
        if grace and grace > expiry:
            expiry = grace
        state = "expired"
        if expiry > timezone.now():
            state = (
                "grace_period"
                if grace and grace > timezone.now()
                else ("trial" if detail.get("period_type") == "trial" else "active")
            )
        # Stable owner binding is enforced in RevenueCat's transfer configuration.
        with transaction.atomic():
            Subscription.objects.update_or_create(
                user=request.user,
                transaction_id=f"rc:grc_{request.user.pk}:{product}",
                defaults={
                    "provider": detail.get("store", "revenuecat"),
                    "product_id": product,
                    "status": state,
                    "expires_at": expiry,
                    "verified_at": timezone.now(),
                },
            )
        return Response({"premium": premium(request.user)})


class Analytics(MobileView):
    def post(self, request):
        from .models import AnalyticsEvent

        allowed = {
            "app_opened",
            "login_completed",
            "path_opened",
            "session_started",
            "question_viewed",
            "question_answered",
            "question_correct",
            "question_wrong",
            "audio_played",
            "voice_submitted",
            "session_completed",
            "paywall_viewed",
            "purchase_started",
            "purchase_completed",
            "purchase_failed",
        }
        name = request.data.get("name")
        if not isinstance(name, str) or name not in allowed:
            raise ValidationError("Geçersiz etkinlik.")
        AnalyticsEvent.objects.create(user=request.user, name=name)
        return Response(status=204)


class PasswordReset(MobileView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        form = MobilePasswordResetForm({"email": request.data.get("email", "")})
        if not form.is_valid():
            raise ValidationError("Geçerli bir e-posta adresi gir.")
        form.save(
            request=request,
            use_https=True,
            email_template_name="mobile_api/reset_email.txt",
            subject_template_name="mobile_api/reset_subject.txt",
        )
        return Response(
            {
                "detail": "Hesabın varsa şifre yenileme bağlantısını e-posta adresine gönderdik."
            }
        )


class BillingWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        import secrets
        from django.conf import settings

        if not settings.REVENUECAT_WEBHOOK_TOKEN or not secrets.compare_digest(
            request.headers.get("Authorization", ""),
            "Bearer " + settings.REVENUECAT_WEBHOOK_TOKEN,
        ):
            raise PermissionDenied("Yetkisiz istek.")
        event = request.data.get("event", {})
        if not isinstance(event, dict):
            raise ValidationError("Geçersiz etkinlik.")
        try:
            identity = (
                BillingIdentity.objects.filter(pk=event.get("app_user_id")).first()
                if event.get("app_user_id")
                else None
            )
        except (ValueError, TypeError, DjangoValidationError):
            identity = None
        if not identity:
            return Response(status=204)
        # Re-query the provider; replayed or out-of-order notifications cannot grant stale access.
        request.user = identity.user
        return SubscriptionSync().post(request)


def visible_questions(user):
    qs = Question.objects.filter(published=True, paths__in=paths(user))
    if not premium(user):
        qs = qs.filter(premium=False, paths__premium=False)
    return qs.distinct()


def private_file(file, content_type):
    from django.http import FileResponse

    try:
        response = FileResponse(file.open("rb"), content_type=content_type)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    except FileNotFoundError:
        return Response(status=404)


class AudioDownload(MobileView):
    def get(self, request, pk):
        from .models import AudioAsset

        asset = AudioAsset.objects.filter(pk=pk).first()
        if not asset:
            return Response(status=404)
        available = (
            visible_questions(request.user)
            .filter(Q(audio_id=pk) | Q(intro_id=pk))
            .exists()
        )
        name_match = (
            bool(request.user.first_name)
            and asset.name_key == request.user.first_name.casefold()
        )
        if not available and not name_match:
            return Response(status=404)
        import mimetypes

        return private_file(
            asset.file,
            mimetypes.guess_type(asset.file.name)[0] or "application/octet-stream",
        )


class ImageDownload(MobileView):
    def get(self, request, pk):
        question = visible_questions(request.user).filter(pk=pk).first()
        if not question or not question.image:
            return Response(status=404)
        import mimetypes

        return private_file(
            question.image,
            mimetypes.guess_type(question.image.name)[0] or "application/octet-stream",
        )
