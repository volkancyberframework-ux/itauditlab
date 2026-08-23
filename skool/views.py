import hmac
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .decorators import skool_user_required
from .models import (
    CareerTestAnswer, MeetingBooking, MeetingSlot, OnboardingEvent, SkoolInvitation,
    SkoolSettings, SkoolUser, TravelAvailability, normalize_name,
)
from .questions import FOUNDATION_POSITIVE, QUESTIONS, question_dicts
from .services import (
    admin_user_url, booking_notification, ensure_upcoming_slots, finalize_expired_bookings, local_booking_lines,
    reserve_slot, reschedule_booking, send_telegram,
)


def youtube_video_id(url):
    """Yaygın YouTube bağlantılarından güvenli video kimliğini ayıklar."""
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.casefold().split(":", 1)[0]
    candidate = ""
    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/", 1)[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
            candidate = parsed.path.strip("/").split("/", 1)[1].split("/", 1)[0]
    return candidate if candidate.replace("-", "").replace("_", "").isalnum() else ""


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def onboarding(request):
    current_id = request.session.get("skool_user_id")
    if current_id and SkoolUser.objects.filter(pk=current_id).exists():
        return redirect("skool:journey")
    raw_token = request.GET.get("invite", "")
    if raw_token:
        request.session["skool_invite_hash"] = SkoolInvitation.hash_token(raw_token)
    error = ""
    if request.method == "POST":
        attempts = request.session.get("skool_claim_attempts", 0)
        if attempts >= 8:
            error = "Çok fazla deneme yapıldı. Lütfen daha sonra tekrar deneyin."
        else:
            request.session["skool_claim_attempts"] = attempts + 1
            invitation = SkoolInvitation.objects.filter(
                token_hash=request.session.get("skool_invite_hash", ""), status="invited"
            ).first()
            supplied = normalize_name(request.POST.get("full_name", ""))
            if invitation and hmac.compare_digest(invitation.normalized_name.encode("utf-8"), supplied.encode("utf-8")):
                with transaction.atomic():
                    invitation = SkoolInvitation.objects.select_for_update().get(pk=invitation.pk)
                    if invitation.status != "invited":
                        error = "Bu davet daha önce kullanılmış veya iptal edilmiş."
                    else:
                        invitation.status = "claimed"
                        invitation.claimed_at = timezone.now()
                        invitation.save(update_fields=("status", "claimed_at"))
                        user = SkoolUser.objects.create(invitation=invitation, full_name=invitation.full_name)
                        OnboardingEvent.objects.create(user=user, event_type="identity_verified")
                        request.session.flush()
                        request.session["skool_user_id"] = user.pk
                        request.session.set_expiry(60 * 60 * 24 * 180)
                        return redirect("skool:journey")
            else:
                error = "Bu isim için aktif bir Skool birebir görüşme daveti bulunamadı."
    return render(request, "skool/onboarding.html", {"error": error})


@skool_user_required
def journey(request):
    user = request.skool_user
    finalize_expired_bookings(user)
    user.refresh_from_db()
    answers = {a.question_id: a.selected_option for a in user.answers.all()}
    config = SkoolSettings.load()
    booking = user.bookings.filter(status="active").select_related("slot__availability").first()
    if booking:
        tr_start, tr_end, host_start, host_end = local_booking_lines(booking)
        can_reschedule = booking.slot.start_at_utc > timezone.now() + timedelta(hours=24)
    else:
        tr_start = tr_end = host_start = host_end = None
        can_reschedule = False
    return render(request, "skool/journey.html", {
        "skool_user": user, "questions_json": json.dumps(question_dicts(), ensure_ascii=False),
        "answers_json": json.dumps(answers, ensure_ascii=False), "config": config,
        "booking": booking, "tr_start": tr_start, "tr_end": tr_end,
        "can_reschedule": can_reschedule,
        "youtube_video_id": youtube_video_id(config.video_url) if not config.audio_url else "",
    })


@require_POST
@skool_user_required
def mark_intro(request):
    user = request.skool_user
    user.intro_seen = True
    if user.state == "IDENTITY_VERIFIED":
        user.state = "TEST_IN_PROGRESS"
        user.test_started_at = timezone.now()
        OnboardingEvent.objects.create(user=user, event_type="test_started")
    user.save(update_fields=("intro_seen", "state", "test_started_at", "updated_at"))
    return JsonResponse({"ok": True})


@require_POST
@skool_user_required
def save_answer(request):
    user = request.skool_user
    if user.test_completed_at:
        return JsonResponse({"ok": False, "error": "Tamamlanan testin cevapları değiştirilemez."}, status=409)
    data = _json_body(request)
    try:
        number = int(data.get("question_id"))
        question = next(q for q in QUESTIONS if q[0] == number)
    except (TypeError, ValueError, StopIteration):
        return JsonResponse({"ok": False, "error": "Geçersiz soru."}, status=400)
    selected = str(data.get("selected_option", ""))
    if selected not in question[3]:
        return JsonResponse({"ok": False, "error": "Bir cevap seçin."}, status=400)
    if number > user.current_question:
        return JsonResponse({"ok": False, "error": "Soruları sırayla yanıtlayın."}, status=409)
    CareerTestAnswer.objects.update_or_create(
        user=user, question_id=number,
        defaults={"question_text": question[1], "selected_option": selected},
    )
    answered = user.answers.count()
    user.state = "TEST_IN_PROGRESS"
    user.current_question = min(24, max(user.current_question, number + 1))
    completed = answered == 24
    if completed:
        foundation_answers = {a.question_id: a.selected_option for a in user.answers.filter(question_id__lte=9)}
        positive_count = sum(foundation_answers.get(number) == expected for number, expected in FOUNDATION_POSITIVE.items())
        user.foundation_result = "strong" if positive_count >= 7 else "develop" if positive_count >= 4 else "foundation"
        user.state = "TEST_COMPLETED"
        user.test_completed_at = timezone.now()
        OnboardingEvent.objects.create(user=user, event_type="test_completed")
    user.save(update_fields=("state", "current_question", "foundation_result", "test_completed_at", "updated_at"))
    if completed:
        send_telegram(
            "🧠 Yeni GRC Ustası Kariyer Testi Tamamlandı\n\n"
            f"👤 {user.full_name}\n📅 {timezone.localdate():%d %B %Y}\n✅ 24 / 24 soru tamamlandı\n\n"
            f"Sonuçları görüntüle:\n{admin_user_url(user)}",
            idempotency_key=f"test-completed:{user.pk}",
        )
    return JsonResponse({"ok": True, "completed": completed, "next_question": user.current_question})


@require_POST
@skool_user_required
def audio_progress(request):
    user = request.skool_user
    if not user.test_completed_at:
        return JsonResponse({"ok": False, "error": "Önce kariyer testini tamamlayın."}, status=403)
    data = _json_body(request)
    try:
        position, duration = max(0, int(float(data.get("position", 0)))), max(1, int(float(data.get("duration", 0))))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Geçersiz ilerleme."}, status=400)
    now = timezone.now()
    if not user.audio_started_at:
        user.audio_started_at = now
        user.state = "AUDIO_IN_PROGRESS"
        OnboardingEvent.objects.create(user=user, event_type="audio_started")
    if user.audio_progress_updated_at:
        wall_delta = max(0, int((now - user.audio_progress_updated_at).total_seconds()))
        media_delta = max(0, position - user.audio_last_position)
        user.audio_listened_seconds += min(media_delta, wall_delta + 5, 30)
    user.audio_last_position = position
    user.audio_duration_seconds = max(user.audio_duration_seconds, duration)
    user.audio_progress_updated_at = now
    eligible = user.audio_listened_seconds >= duration * 0.8
    user.save(update_fields=("audio_started_at", "state", "audio_listened_seconds", "audio_last_position", "audio_duration_seconds", "audio_progress_updated_at", "updated_at"))
    return JsonResponse({"ok": True, "eligible": eligible, "percent": min(100, round(user.audio_listened_seconds / duration * 100))})


@require_POST
@skool_user_required
def complete_audio(request):
    user = request.skool_user
    if not user.test_completed_at:
        return JsonResponse({"ok": False}, status=403)
    if not user.audio_duration_seconds or user.audio_listened_seconds < user.audio_duration_seconds * 0.8:
        return JsonResponse({"ok": False, "error": "Kaydın en az %80'ini dinlemelisiniz."}, status=409)
    if not user.audio_completed_at:
        user.audio_completed_at = timezone.now()
        user.state = "READY_TO_BOOK"
        user.save(update_fields=("audio_completed_at", "state", "updated_at"))
        OnboardingEvent.objects.create(user=user, event_type="audio_completed")
    return JsonResponse({"ok": True})


@require_GET
@skool_user_required
def slots(request):
    user = request.skool_user
    if not user.audio_completed_at:
        return JsonResponse({"ok": False, "error": "Önce ses kaydını tamamlayın."}, status=403)
    ensure_upcoming_slots()
    display_zone = ZoneInfo(SkoolSettings.load().display_timezone)
    tomorrow = timezone.localdate(timezone=display_zone) + timedelta(days=1)
    result = []
    for slot in MeetingSlot.objects.filter(local_date__gte=tomorrow).select_related("availability").order_by("start_at_utc")[:180]:
        start, end = slot.start_at_utc.astimezone(display_zone), slot.end_at_utc.astimezone(display_zone)
        result.append({"id": slot.pk, "date": start.date().isoformat(), "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"), "status": slot.status})
    return JsonResponse({"ok": True, "timezone": "Europe/Istanbul", "slots": result})


@require_POST
@skool_user_required
def book(request):
    user = request.skool_user
    if not user.audio_completed_at:
        return JsonResponse({"ok": False, "error": "Rezervasyon aşaması henüz açık değil."}, status=403)
    try:
        booking = reserve_slot(user, int(_json_body(request).get("slot_id")))
    except (ValueError, TypeError, MeetingSlot.DoesNotExist) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=409)
    transaction.on_commit(lambda: booking_notification(booking))
    return JsonResponse({"ok": True, "redirect": reverse("skool:journey")})


@require_POST
@skool_user_required
def reschedule(request):
    try:
        booking, old_slot = reschedule_booking(request.skool_user, int(_json_body(request).get("slot_id")))
    except (ValueError, TypeError, MeetingBooking.DoesNotExist, MeetingSlot.DoesNotExist) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=409)
    send_telegram(f"🔄 Skool Görüşmesi Değiştirildi\n\n👤 {booking.user.full_name}\nEski: {old_slot.start_at_utc}\nYeni: {booking.slot.start_at_utc}\n\nProfil: {admin_user_url(booking.user)}")
    return JsonResponse({"ok": True, "redirect": reverse("skool:journey")})


@staff_member_required
def admin_dashboard(request):
    users = SkoolUser.objects.select_related("invitation").prefetch_related("bookings")
    today = timezone.localdate()
    return render(request, "skool/admin/dashboard.html", {
        "users": users[:100], "active_invites": SkoolInvitation.objects.filter(status="invited").count(),
        "started": users.exclude(state="IDENTITY_VERIFIED").count(),
        "tests": users.filter(test_completed_at__isnull=False).count(),
        "audio": users.filter(audio_completed_at__isnull=False).count(),
        "upcoming": MeetingBooking.objects.filter(status="active", slot__start_at_utc__gte=timezone.now()).count(),
        "today": MeetingBooking.objects.filter(status="active", slot__local_date=today).count(),
    })


@staff_member_required
def admin_user(request, pk):
    user = get_object_or_404(SkoolUser.objects.select_related("invitation").prefetch_related("answers", "events", "bookings__slot"), pk=pk)
    summary = [(q[1], next((a.selected_option for a in user.answers.all() if a.question_id == q[0]), "—")) for q in QUESTIONS]
    return render(request, "skool/admin/user.html", {"skool_user": user, "summary": summary})


@staff_member_required
def admin_availability(request):
    return redirect("admin:skool_travelavailability_changelist")


@staff_member_required
def admin_bookings(request):
    return redirect("admin:skool_meetingbooking_changelist")


@csrf_exempt
@require_POST
def telegram_webhook(request):
    secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if secret and not hmac.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), secret):
        return JsonResponse({"ok": False}, status=403)
    payload = _json_body(request)
    message = payload.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    admin_chat = str(getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", "") or getattr(settings, "TELEGRAM_CHAT_ID", ""))
    if not admin_chat or not hmac.compare_digest(chat_id, admin_chat):
        return JsonResponse({"ok": True})
    text = (message.get("text") or "").strip()
    command, _, argument = text.lstrip("/").partition(" ")
    command, argument = command.casefold(), argument.strip()
    if command == "create" and argument:
        invitation, raw = SkoolInvitation.create_invitation(argument)
        base = getattr(settings, "PUBLIC_BASE_URL", "https://grcustasi.com").rstrip("/")
        send_telegram(f"✅ {invitation.full_name} için erişim oluşturuldu.\n\nOnboarding linki:\n{base}{reverse('skool:onboarding')}?invite={raw}\n\nDurum: Kullanılmadı")
    elif command == "status" and argument:
        invitations = SkoolInvitation.objects.filter(normalized_name=normalize_name(argument))[:5]
        send_telegram("\n".join(f"{obj.full_name}: {obj.get_status_display()} ({obj.created_at:%d.%m.%Y})" for obj in invitations) or "Kayıt bulunamadı.")
    elif command == "revoke" and argument:
        count = SkoolInvitation.objects.filter(normalized_name=normalize_name(argument), status="invited").update(status="revoked", revoked_at=timezone.now())
        send_telegram(f"⛔ {argument}: {count} aktif davet iptal edildi.")
    else:
        send_telegram("Komutlar: /create Ad Soyad, /status Ad Soyad, /revoke Ad Soyad")
    return JsonResponse({"ok": True})
