import hmac
import json
import logging
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST

from .decorators import skool_user_required
from .models import (
    CareerTestAnswer, MeetingBooking, MeetingSlot, OnboardingEvent, SkoolInvitation,
    SkoolLab, SkoolLabProgress, SkoolSettings, SkoolUser, TravelAvailability, normalize_name,
)

logger = logging.getLogger(__name__)


def safe_send_telegram(message):
    try:
        return send_telegram(message)
    except Exception:
        logger.exception("Telegram bildirimi gönderilemedi")
        return False
from .questions import FOUNDATION_POSITIVE, QUESTIONS, question_dicts
from .services import (
    admin_user_url, booking_notification, earliest_repeat_booking_date, ensure_upcoming_slots,
    finalize_expired_bookings, local_booking_lines, reserve_slot, reschedule_booking, send_telegram,
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


def bunny_embed_url(url):
    """Bunny Stream'in iframe/play bağlantılarını yalnızca güvenilir hosttan kabul eder."""
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.casefold().split(":", 1)[0]
    if parsed.scheme != "https" or host not in {"iframe.mediadelivery.net", "player.mediadelivery.net"}:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 3 or parts[0] not in {"play", "embed"}:
        return ""
    library_id, video_id = parts[1], parts[2]
    if not library_id.isdigit() or not video_id.replace("-", "").isalnum():
        return ""
    # `/play/` is Bunny's standalone player page. Embedding that page inside
    # another iframe causes the player to render as a tiny nested viewport on
    # mobile Safari. Always return Bunny's responsive iframe endpoint.
    return (
        f"https://iframe.mediadelivery.net/embed/{library_id}/{video_id}"
        "?autoplay=false&loop=false&muted=false&preload=true&responsive=true"
    )


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
            supplied = normalize_name(request.POST.get("full_name", ""))
            invitation = SkoolInvitation.objects.filter(
                token_hash=request.session.get("skool_invite_hash", ""), status__in=("invited", "claimed")
            ).first()
            # A previously opened invite link may remain in the browser session.
            # It must not shadow a later, valid name-only login.
            if not invitation or invitation.normalized_name != supplied:
                invitation = SkoolInvitation.objects.filter(
                    normalized_name=supplied, status__in=("invited", "claimed")
                ).order_by("-created_at").first()
            if invitation and hmac.compare_digest(invitation.normalized_name.encode("utf-8"), supplied.encode("utf-8")):
                if invitation.status == "claimed" and hasattr(invitation, "user"):
                    user = invitation.user
                    request.session.flush()
                    request.session["skool_user_id"] = user.pk
                    request.session.set_expiry(60 * 60 * 24 * 180)
                    return redirect("skool:journey")
                if invitation.status == "claimed":
                    # Repair manually-created/edited invitations which were marked
                    # claimed before their SkoolUser row was created.
                    user = SkoolUser.objects.create(invitation=invitation, full_name=invitation.full_name)
                    OnboardingEvent.objects.create(user=user, event_type="identity_verified", detail={"source": "manual_invitation_repair"})
                    request.session.flush()
                    request.session["skool_user_id"] = user.pk
                    request.session.set_expiry(60 * 60 * 24 * 180)
                    return redirect("skool:journey")
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


def skool_logout(request):
    request.session.pop("skool_user_id", None)
    request.session.pop("skool_invite_hash", None)
    return redirect("skool:onboarding")


def labs(request):
    from .lab_catalog import ensure_lab_records, lab_is_unlocked

    ensure_lab_records()
    user_id = request.session.get("skool_user_id")
    user = SkoolUser.objects.filter(pk=user_id, invitation__status="claimed").first()
    error = ""
    if not user and request.method == "POST":
        entered_name = " ".join(request.POST.get("full_name", "").strip().split())
        supplied = normalize_name(entered_name)
        invitation = SkoolInvitation.objects.filter(normalized_name=supplied, status__in=("invited", "claimed")).order_by("-created_at").first()
        if invitation:
            if invitation.status == "invited":
                invitation.status = "claimed"
                invitation.claimed_at = timezone.now()
                invitation.save(update_fields=("status", "claimed_at"))
            user, _ = SkoolUser.objects.get_or_create(invitation=invitation, defaults={"full_name": invitation.full_name})
            request.session["skool_user_id"] = user.pk
            request.session.set_expiry(60 * 60 * 24 * 180)
            safe_send_telegram(f"✅ Çalışmalar paneli girişi\n\n👤 {user.full_name}\nDurum: Başarılı")
            return redirect("skool:labs")
        safe_send_telegram(f"⚠️ Çalışmalar paneli giriş denemesi\n\n👤 {entered_name or '(isim girilmedi)'}\nDurum: Erişim bulunamadı")
        error = "Bu ad soyad için etkin bir GRC Ustası erişimi bulunamadı."
    if not user:
        return render(request, "skool/labs_login.html", {"error": error})
    show_labs_welcome = not user.labs_welcome_seen
    if show_labs_welcome:
        SkoolUser.objects.filter(pk=user.pk, labs_welcome_seen=False).update(labs_welcome_seen=True)
        user.labs_welcome_seen = True
    ordered_labs = list(SkoolLab.objects.filter(is_active=True).order_by("order", "title"))
    completed_ids = set(SkoolLabProgress.objects.filter(user=user).values_list("lab_id", flat=True))
    for lab in ordered_labs:
        lab.is_completed = lab.pk in completed_ids
        lab.is_unlocked = lab_is_unlocked(user, lab, ordered_labs)
    return render(request, "skool/labs.html", {
        "skool_user": user,
        "labs": ordered_labs,
        "show_labs_welcome": show_labs_welcome,
    })


@xframe_options_sameorigin
@skool_user_required
def lab_pdf(request, pk):
    from .lab_catalog import bundled_pdf_path, lab_is_unlocked

    lab = get_object_or_404(SkoolLab, pk=pk, is_active=True)
    if not lab_is_unlocked(request.skool_user, lab):
        raise Http404("Bu laboratuvar henüz açılmadı.")
    packaged_pdf = bundled_pdf_path(lab.pdf.name)
    if packaged_pdf.is_file():
        return FileResponse(packaged_pdf.open("rb"), content_type="application/pdf", filename=f"{lab.title}.pdf")
    return FileResponse(lab.pdf.open("rb"), content_type="application/pdf", filename=f"{lab.title}.pdf")


@require_POST
@skool_user_required
def complete_lab(request, pk):
    from .lab_catalog import lab_is_unlocked

    lab = get_object_or_404(SkoolLab, pk=pk, is_active=True)
    if not lab_is_unlocked(request.skool_user, lab):
        return JsonResponse({"ok": False, "error": "Önce bir önceki laboratuvarı tamamlayın."}, status=409)
    progress, created = SkoolLabProgress.objects.get_or_create(user=request.skool_user, lab=lab)
    if created:
        next_lab = SkoolLab.objects.filter(is_active=True, order__gt=lab.order).order_by("order", "title").first()
        transition = f"Sıradaki çalışma açıldı: {next_lab.title}" if next_lab else "Tüm çalışmalar tamamlandı."
        safe_send_telegram(
            f"🧪 Laboratuvar tamamlandı\n\n👤 {request.skool_user.full_name}\n"
            f"📘 {lab.title}\n✅ Kullanıcı cevabını Volkan'a gönderdiğini onayladı.\n{transition}"
        )
    return JsonResponse({"ok": True, "created": created})


@skool_user_required
def journey(request):
    user = request.skool_user
    finalize_expired_bookings(user)
    user.refresh_from_db()
    answers = {a.question_id: a.selected_option for a in user.answers.all()}
    config = SkoolSettings.load()
    booking = user.bookings.filter(status="active").select_related("slot__availability").first()
    previous_bookings = user.bookings.exclude(status="active").select_related("slot__availability").order_by("-slot__start_at_utc")[:10]
    repeat_booking_available_date = earliest_repeat_booking_date(user)
    if booking:
        tr_start, tr_end, host_start, host_end = local_booking_lines(booking)
        can_reschedule = booking.slot.start_at_utc > timezone.now() + timedelta(hours=24)
    else:
        tr_start = tr_end = host_start = host_end = None
        can_reschedule = False
    media_url = config.audio_url or config.video_url
    youtube_id = youtube_video_id(media_url)
    bunny_url = bunny_embed_url(media_url)
    return render(request, "skool/journey.html", {
        "skool_user": user, "questions_json": json.dumps(question_dicts(), ensure_ascii=False),
        "answers_json": json.dumps(answers, ensure_ascii=False), "config": config,
        "booking": booking, "tr_start": tr_start, "tr_end": tr_end,
        "can_reschedule": can_reschedule,
        "media_url": media_url,
        "direct_audio_url": media_url if config.audio_url and not youtube_id and not bunny_url else "",
        "direct_video_url": media_url if config.video_url and not youtube_id and not bunny_url else "",
        "youtube_video_id": youtube_id,
        "bunny_embed_url": bunny_url,
        "audio_was_skipped": user.events.filter(event_type="audio_skipped").exists(),
        "previous_bookings": previous_bookings,
        "repeat_booking_available_date": repeat_booking_available_date,
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
    if not user.audio_completed_at:
        user.audio_completed_at = timezone.now()
        user.state = "READY_TO_BOOK"
        user.save(update_fields=("audio_completed_at", "state", "updated_at"))
        OnboardingEvent.objects.create(user=user, event_type="audio_completed")
    return JsonResponse({"ok": True})


@require_POST
@skool_user_required
def skip_audio(request):
    user = request.skool_user
    if not user.test_completed_at:
        return JsonResponse({"ok": False, "error": "Önce kariyer testini tamamlayın."}, status=403)
    if not user.audio_completed_at:
        user.audio_completed_at = timezone.now()
        user.state = "READY_TO_BOOK"
        user.save(update_fields=("audio_completed_at", "state", "updated_at"))
        OnboardingEvent.objects.create(user=user, event_type="audio_skipped")
        send_telegram(
            f"⚠️ {user.full_name} Skool kaydını tamamlamadan takvime geçti.\n\n{admin_user_url(user)}",
            idempotency_key=f"audio-skipped:{user.pk}",
        )
    return JsonResponse({"ok": True})


@require_GET
@skool_user_required
def slots(request):
    user = request.skool_user
    if not user.audio_completed_at:
        return JsonResponse({"ok": False, "error": "Önce ses kaydını tamamlayın."}, status=403)
    finalize_expired_bookings(user)
    ensure_upcoming_slots()
    display_zone = ZoneInfo(SkoolSettings.load().display_timezone)
    tomorrow = timezone.localdate(timezone=display_zone) + timedelta(days=1)
    earliest_date = earliest_repeat_booking_date(user, display_zone)
    first_selectable_date = max(tomorrow, earliest_date) if earliest_date else tomorrow
    result = []
    queryset = MeetingSlot.objects.filter(local_date__gte=tomorrow).select_related("availability").order_by("start_at_utc")
    for slot in queryset[:360]:
        start, end = slot.start_at_utc.astimezone(display_zone), slot.end_at_utc.astimezone(display_zone)
        if start.date() < first_selectable_date:
            continue
        result.append({"id": slot.pk, "date": start.date().isoformat(), "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"), "status": slot.status})
        if len(result) == 180:
            break
    return JsonResponse({
        "ok": True,
        "timezone": "Europe/Istanbul",
        "slots": result,
        "first_selectable_date": first_selectable_date.isoformat(),
    })


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
    secret = getattr(settings, "GRCUSTASI_TELEGRAM_WEBHOOK_SECRET", "") or getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if secret and not hmac.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), secret):
        return JsonResponse({"ok": False}, status=403)
    payload = _json_body(request)
    message = payload.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    admin_chat = str(
        getattr(settings, "GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID", "")
        or getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", "")
        or getattr(settings, "TELEGRAM_CHAT_ID", "")
    )
    if not admin_chat or not hmac.compare_digest(chat_id, admin_chat):
        return JsonResponse({"ok": True})
    text = (message.get("text") or "").strip()
    if text.casefold().startswith("grcustasi "):
        text = text.split(" ", 1)[1].strip()
    command, _, argument = text.lstrip("/").partition(" ")
    command, argument = command.casefold(), argument.strip()
    if command == "create" and argument:
        invitation, raw = SkoolInvitation.create_invitation(argument)
        base = getattr(settings, "PUBLIC_BASE_URL", "https://www.grcustasi.com").rstrip("/")
        send_telegram(f"✅ {invitation.full_name} için erişim oluşturuldu.\n\nOnboarding linki:\n{base}{reverse('skool:onboarding')}?invite={raw}\n\nDurum: Kullanılmadı")
    elif command == "status" and argument:
        invitations = SkoolInvitation.objects.filter(normalized_name=normalize_name(argument))[:5]
        send_telegram("\n".join(f"{obj.full_name}: {obj.get_status_display()} ({obj.created_at:%d.%m.%Y})" for obj in invitations) or "Kayıt bulunamadı.")
    elif command == "revoke" and argument:
        count = SkoolInvitation.objects.filter(normalized_name=normalize_name(argument), status="invited").update(status="revoked", revoked_at=timezone.now())
        send_telegram(f"⛔ {argument}: {count} aktif davet iptal edildi.")
    elif command == "disable" and argument:
        count = SkoolInvitation.objects.filter(normalized_name=normalize_name(argument)).exclude(status="revoked").update(status="revoked", revoked_at=timezone.now())
        send_telegram(f"🔒 {argument}: {count} erişim devre dışı bırakıldı. Skool, çalışmalar ve takvim erişimi kapatıldı.")
    elif command == "list":
        query = SkoolInvitation.objects.all()
        if argument:
            query = query.filter(normalized_name__contains=normalize_name(argument))
        entries = list(query.order_by("full_name", "-created_at")[:50])
        send_telegram("👥 GRC Ustası erişimleri\n\n" + ("\n".join(f"• {obj.full_name} — {obj.get_status_display()}" for obj in entries) or "Kayıt bulunamadı."))
    elif command == "help":
        send_telegram(
            "🧭 GRC Ustası Telegram Komutları\n\n"
            "grcustasi create Ad Soyad — yeni erişim ve kişisel bağlantı\n"
            "grcustasi status Ad Soyad — erişim durumunu göster\n"
            "grcustasi disable Ad Soyad — tüm erişimi kapat\n"
            "grcustasi revoke Ad Soyad — kullanılmamış daveti iptal et\n"
            "grcustasi list — kişileri listele\n"
            "grcustasi list volkan — adında volkan geçenleri listele\n"
            "grcustasi help — bu kılavuzu göster"
        )
    else:
        send_telegram("Komut anlaşılmadı. Kullanım kılavuzu için: grcustasi help")
    return JsonResponse({"ok": True})
