import hashlib
import secrets
import unicodedata
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def normalize_name(value):
    value = " ".join((value or "").strip().split()).casefold()
    return unicodedata.normalize("NFC", value)


class SkoolInvitation(models.Model):
    STATUS = [("invited", "Davet edildi"), ("claimed", "Kullanıldı"), ("revoked", "İptal edildi")]
    full_name = models.CharField("Ad soyad", max_length=160)
    normalized_name = models.CharField(max_length=160, db_index=True, editable=False)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=STATUS, default="invited", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Skool daveti"
        verbose_name_plural = "Skool davetleri"

    @classmethod
    def create_invitation(cls, full_name):
        raw = secrets.token_urlsafe(32)
        invitation = cls.objects.create(
            full_name=" ".join(full_name.strip().split()),
            normalized_name=normalize_name(full_name),
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
        return invitation, raw

    @staticmethod
    def hash_token(raw):
        return hashlib.sha256((raw or "").encode()).hexdigest()

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_name(self.full_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} — {self.get_status_display()}"


class SkoolLab(models.Model):
    title = models.CharField("Çalışma adı", max_length=180)
    description = models.TextField("Açıklama", blank=True)
    pdf = models.FileField("Laboratuvar PDF'i", upload_to="skool_labs/")
    order = models.PositiveSmallIntegerField("Sıra", default=0)
    is_active = models.BooleanField("Yayında", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "title")
        verbose_name = "Skool laboratuvarı"
        verbose_name_plural = "Skool laboratuvarları"

    def __str__(self):
        return self.title


class SkoolLabProgress(models.Model):
    user = models.ForeignKey("SkoolUser", on_delete=models.CASCADE, related_name="lab_progress")
    lab = models.ForeignKey(SkoolLab, on_delete=models.CASCADE, related_name="user_progress")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "lab"), name="unique_skool_lab_progress")]
        ordering = ("completed_at",)
        verbose_name = "Laboratuvar ilerlemesi"
        verbose_name_plural = "Laboratuvar ilerlemeleri"

    def __str__(self):
        return f"{self.user} - {self.lab}"


class SkoolUser(models.Model):
    STATES = [
        ("IDENTITY_VERIFIED", "Kimlik doğrulandı"), ("TEST_IN_PROGRESS", "Test sürüyor"),
        ("TEST_COMPLETED", "Test tamamlandı"), ("AUDIO_IN_PROGRESS", "Ses kaydı dinleniyor"),
        ("AUDIO_COMPLETED", "Ses kaydı tamamlandı"), ("READY_TO_BOOK", "Rezervasyona hazır"),
        ("BOOKED", "Görüşme planlandı"), ("COMPLETED", "Tamamlandı"),
    ]
    invitation = models.OneToOneField(SkoolInvitation, on_delete=models.PROTECT, related_name="user")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    full_name = models.CharField(max_length=160)
    state = models.CharField(max_length=24, choices=STATES, default="IDENTITY_VERIFIED", db_index=True)
    foundation_result = models.CharField(max_length=20, choices=[("strong", "Güçlü uygunluk"), ("develop", "Geliştirilebilir noktalar"), ("foundation", "Temel eksikler")], blank=True)
    current_question = models.PositiveSmallIntegerField(default=1)
    intro_seen = models.BooleanField(default=False)
    identity_verified_at = models.DateTimeField(default=timezone.now)
    test_started_at = models.DateTimeField(null=True, blank=True)
    test_completed_at = models.DateTimeField(null=True, blank=True)
    audio_started_at = models.DateTimeField(null=True, blank=True)
    audio_completed_at = models.DateTimeField(null=True, blank=True)
    audio_listened_seconds = models.PositiveIntegerField(default=0)
    audio_last_position = models.PositiveIntegerField(default=0)
    audio_duration_seconds = models.PositiveIntegerField(default=0)
    audio_progress_updated_at = models.DateTimeField(null=True, blank=True)
    labs_welcome_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Skool kullanıcısı"
        verbose_name_plural = "Skool kullanıcıları"

    def __str__(self):
        return self.full_name


class CareerTestAnswer(models.Model):
    user = models.ForeignKey(SkoolUser, on_delete=models.CASCADE, related_name="answers")
    question_id = models.PositiveSmallIntegerField()
    question_text = models.TextField()
    selected_option = models.CharField(max_length=240)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "question_id"), name="unique_skool_answer")]
        ordering = ("question_id",)


class OnboardingEvent(models.Model):
    user = models.ForeignKey(SkoolUser, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=40)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class SkoolSettings(models.Model):
    audio_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    meeting_duration_minutes = models.PositiveSmallIntegerField(default=90)
    daily_slot_count = models.PositiveSmallIntegerField(default=3)
    minimum_gap_minutes = models.PositiveSmallIntegerField(default=15)
    display_timezone = models.CharField(max_length=64, default="Europe/Istanbul")
    meet_url = models.URLField(default="https://meet.google.com/jbv-csdm-eyy")

    class Meta:
        verbose_name = "Skool ayarı"
        verbose_name_plural = "Skool ayarları"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            "audio_url": getattr(settings, "SKOOL_AUDIO_URL", ""),
            "meeting_duration_minutes": getattr(settings, "SKOOL_MEETING_DURATION_MINUTES", 90),
            "daily_slot_count": getattr(settings, "SKOOL_DAILY_SLOT_COUNT", 3),
            "minimum_gap_minutes": getattr(settings, "SKOOL_MINIMUM_GAP_MINUTES", 15),
            "display_timezone": getattr(settings, "SKOOL_DISPLAY_TIMEZONE", "Europe/Istanbul"),
            "meet_url": getattr(settings, "SKOOL_GOOGLE_MEET_URL", "https://meet.google.com/jbv-csdm-eyy"),
        })
        return obj


class TravelAvailability(models.Model):
    location_name = models.CharField(max_length=100)
    timezone = models.CharField(max_length=64)
    start_date = models.DateField()
    end_date = models.DateField()
    local_available_start = models.TimeField()
    local_available_end = models.TimeField()
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("start_date",)
        verbose_name = "Seyahat ve uygunluk"
        verbose_name_plural = "Seyahat ve uygunluk"

    def clean(self):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValidationError({"timezone": "Geçerli bir IANA zaman dilimi girin."}) from exc
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "Bitiş tarihi başlangıçtan önce olamaz."})
        start_minutes = self.local_available_start.hour * 60 + self.local_available_start.minute
        end_minutes = self.local_available_end.hour * 60 + self.local_available_end.minute
        settings_obj = SkoolSettings.load()
        required = settings_obj.daily_slot_count * settings_obj.meeting_duration_minutes
        if end_minutes - start_minutes < required:
            raise ValidationError("Bu aralık günlük görüşme sayısı için yeterli değil.")

    def __str__(self):
        return f"{self.location_name}: {self.start_date} — {self.end_date}"


class AvailabilityException(models.Model):
    availability = models.ForeignKey(TravelAvailability, null=True, blank=True, on_delete=models.CASCADE, related_name="exceptions")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "Bitiş tarihi başlangıçtan önce olamaz."})


class MeetingSlot(models.Model):
    STATUS = [("available", "Müsait"), ("booked", "Dolu"), ("disabled", "Kapalı")]
    availability = models.ForeignKey(TravelAvailability, on_delete=models.PROTECT, related_name="slots")
    local_date = models.DateField(db_index=True)
    start_at_utc = models.DateTimeField(unique=True)
    end_at_utc = models.DateTimeField()
    status = models.CharField(max_length=12, choices=STATUS, default="available", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("start_at_utc",)
        constraints = [models.UniqueConstraint(fields=("availability", "local_date", "start_at_utc"), name="unique_skool_slot")]

    def __str__(self):
        return f"{self.availability.location_name} — {self.start_at_utc}"


class MeetingBooking(models.Model):
    STATUS = [("active", "Aktif"), ("completed", "Tamamlandı"), ("rescheduled", "Değiştirildi"), ("cancelled", "İptal")]
    user = models.ForeignKey(SkoolUser, on_delete=models.PROTECT, related_name="bookings")
    slot = models.OneToOneField(MeetingSlot, on_delete=models.PROTECT, related_name="booking")
    status = models.CharField(max_length=16, choices=STATUS, default="active", db_index=True)
    meeting_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user",), condition=Q(status="active"), name="one_active_skool_booking")]


class BookingHistory(models.Model):
    booking = models.ForeignKey(MeetingBooking, on_delete=models.CASCADE, related_name="history")
    old_slot = models.ForeignKey(MeetingSlot, on_delete=models.PROTECT, related_name="old_booking_history")
    new_slot = models.ForeignKey(MeetingSlot, on_delete=models.PROTECT, related_name="new_booking_history")
    changed_at = models.DateTimeField(auto_now_add=True)


class NotificationLog(models.Model):
    key = models.CharField(max_length=160, unique=True)
    notification_type = models.CharField(max_length=40)
    sent_at = models.DateTimeField(auto_now_add=True)
    detail = models.JSONField(default=dict, blank=True)
