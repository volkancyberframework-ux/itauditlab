from __future__ import annotations
from django.db import models
from django.templatetags.static import static
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal


from django.db import models
from django.utils.text import slugify

from django.conf import settings
from django.db import models



class PageVisit(models.Model):
    path = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.path} - {self.user or self.ip_address}"

class BootcampInterest(models.Model):
    bootcamp = models.ForeignKey(
        "Bootcamp",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    email = models.EmailField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        bootcamp_title = self.bootcamp.title if self.bootcamp else "Bootcamp deleted"
        return f"{bootcamp_title} - {self.user or self.email or self.ip_address}"
class Bootcamp(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    duration = models.CharField(max_length=100, blank=True)
    level = models.CharField(max_length=100, blank=True)
    price = models.PositiveIntegerField(help_text="TL olarak yaz. Örn: 10000")
    currency = models.CharField(max_length=10, default="TRY")
    image = models.ImageField(upload_to="bootcamps/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def price_display(self):
        return f"₺{self.price:,.0f}".replace(",", ".")

class NewsletterLead(models.Model):
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=100, default="cybersecurity_fit_test_popup")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Currency(models.TextChoices):
    USD = "USD", "USD"
    EUR = "EUR", "EUR"
    TRY = "TRY", "TRY"

DIFFICULTY_CHOICES = [
    ("Beginner", "🌱 Temel"),
    ("Intermediate", "📚 Orta"),
    ("Advanced", "🔥 Zor"),
]


class DigitalProduct(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)

    image = models.ImageField(upload_to="digital_products/images/", blank=True, null=True)
    description = models.TextField(blank=True)

    duration = models.CharField(max_length=32, blank=True, help_text="e.g. 3h 56m")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="Beginner")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    reviews_count = models.PositiveIntegerField(default=0)

    uploader_name = models.CharField(max_length=120, default="ITAuditLab")
    static_avatar = models.ImageField(upload_to="digital_products/avatars/", blank=True, null=True)

    # fiyatlar
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.0"))],
        default=0
    )
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.0"))],
        blank=True, null=True,
        help_text="Boşsa price * 4 olarak otomatik ayarlanır."
    )
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)

    ruul_pay_link = models.URLField(blank=True)
    license_password = models.CharField(max_length=64, help_text="PDF şifresi (Ruul gösterir)")
    source_pdf = models.FileField(upload_to="digital_products/source_pdf/", blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:50]
            s = base
            i = 1
            while DigitalProduct.objects.filter(slug=s).exclude(pk=self.pk).exists():
                i += 1
                s = f"{base}-{i}"
            self.slug = s

        # original_price boşsa 4x
        if self.original_price is None and self.price is not None:
            self.original_price = (self.price or Decimal("0")) * Decimal("4")

        super().save(*args, **kwargs)

    @property
    def currency_symbol(self) -> str:
        return {"USD": "$", "EUR": "€", "TRY": "₺"}.get(self.currency, "")

    def _fmt(self, amount: Decimal) -> str:
        sym = self.currency_symbol
        if self.currency in ("USD", "TRY"):
            return f"{sym}{amount}"
        return f"{amount} {sym}"

    def price_display(self) -> str:
        return self._fmt(self.price or Decimal("0"))

    def original_price_display(self) -> str:
        base = self.original_price if self.original_price is not None else (self.price or Decimal("0")) * Decimal("4")
        return self._fmt(base)


# Ödeme niyeti / geçici kayıt (webhook gelene kadar)
import uuid

class PurchaseIntent(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    product = models.ForeignKey(DigitalProduct, on_delete=models.CASCADE, related_name="purchase_intents")
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)  # Ruul webhook geldikten sonra True yap

    def __str__(self):
        return f"{self.email} -> {self.product.title} ({'PAID' if self.is_paid else 'PENDING'})"


class Course(models.Model):
    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    class CourseType(models.TextChoices):
        VIDEO = 'video', 'Video'
        TEST  = 'test',  'Test'

    turkish_name = models.CharField(max_length=255)
    english_name = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='course_images/', blank=True, null=True)
    duration = models.DurationField(help_text="Format: hh:mm:ss")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    score = models.FloatField(default=0.0)
    preparer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prepared_courses'
    )
    description = models.TextField()
    attachment = models.FileField(upload_to='course_attachments/', blank=True, null=True)

    # Visibility / placement flags
    dashboard_activated = models.BooleanField(default=False)
    main_page_activated = models.BooleanField(default=False)
    is_english = models.BooleanField(default=False)
    is_turkish = models.BooleanField(default=False)

    # NEW: course type (Video/Test)
    course_type = models.CharField(
        max_length=10,
        choices=CourseType.choices,
        default=CourseType.VIDEO,
        db_index=True,
    )

    intro_video_url = models.URLField(
        blank=True,
        null=True,
        help_text="TEST kursları için sağ üst kapakta açılacak tanıtım videosu"
    )
    def __str__(self):
        return self.turkish_name or self.english_name or f"Course #{self.pk}"

    @property
    def cover_url(self):
        """Return a safe course cover URL even when no upload is present."""
        if self.image:
            if self.image.name.startswith("__static__/"):
                return static(self.image.name.removeprefix("__static__/"))
            try:
                return self.image.url
            except Exception:
                pass
        return static("assets/images/course/grc-ustasi-default-cover.jpg")

    @property
    def is_video(self) -> bool:
        return self.course_type == self.CourseType.VIDEO

    @property
    def is_test(self) -> bool:
        return self.course_type == self.CourseType.TEST

def __str__(self):
    return self.turkish_name or self.english_name or f"Course #{self.pk}"

class TestQuestion(models.Model):
    SINGLE = "single"
    MULTIPLE = "multiple"
    TYPES = [(SINGLE, "Single choice"), (MULTIPLE, "Multiple choice")]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="test_questions")
    text = models.CharField(max_length=500)
    explanation = models.TextField(blank=True)
    question_type = models.CharField(max_length=8, choices=TYPES, default=SINGLE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.course_id}] {self.text[:60]}"

class TestOption(models.Model):
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        mark = "✔" if self.is_correct else "✖"
        return f"{mark} {self.text[:60]}"



class CourseSection(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    order = models.PositiveIntegerField(null=True, blank=True)
    big_title = models.CharField(max_length=255)

    def __str__(self):
        course_name = self.course.turkish_name or self.course.english_name or f"Course #{self.course.pk}"
        return f"{course_name} - {self.big_title}"



class CourseSubsection(models.Model):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='subsections')
    order = models.PositiveIntegerField(default=0)
    small_title = models.CharField(max_length=255)
    bunny_video_id = models.URLField(blank=True, null=True, help_text="Paste Bunny Direct Play URL (playlist.m3u8 or .mp4) OR just the video ID")
    duration = models.CharField(max_length=20, blank=True, help_text="e.g. 3m 12s")

    def __str__(self):
        return f"{self.section.big_title} → {self.small_title}"


class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    orientation_seen = models.BooleanField(default=False)
    is_automatic = models.BooleanField(default=False, help_text="Program otomasyonunun açtığı erişim; öğrencinin kendi kaydı değildir.")

    class Meta:
        unique_together = ('user', 'course')


class LearningProgram(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LearningProgramStep(models.Model):
    program = models.ForeignKey(
        LearningProgram, on_delete=models.CASCADE, related_name="steps"
    )
    day_offset = models.PositiveIntegerField(help_text="Başlangıçtan kaç gün sonra açılacak")
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    email_title = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("day_offset", "order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("program", "course"), name="unique_program_course_step"
            )
        ]

    def __str__(self):
        return f"{self.program} · Gün {self.day_offset} · {self.course}"


class ProgramEnrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_programs"
    )
    program = models.ForeignKey(
        LearningProgram, on_delete=models.PROTECT, related_name="enrollments"
    )
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    progress_warning_enabled = models.BooleanField(
        'Önceki ders uyarısı ve ilk ihlalde hesap kapatma', default=False,
        help_text='Dersler takviminde açılmaya devam eder. Tamamlanmadığı doğrulanmış önceki dersler varken öğrenci ikinci uyarıyı onaylayarak yeni derse geçerse ana hesabı kapatılır. Bilinmeyen tamamlanma durumu ihlal sayılmaz.',
    )
    welcome_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "program"), name="unique_user_learning_program"
            )
        ]
        ordering = ("-is_active", "start_date", "user__email")

    def __str__(self):
        return f"{self.user.email} · {self.program}"


class ProgramRelease(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Mail bekliyor"
        SENT = "sent", "Gönderildi"
        FAILED = "failed", "Mail hatası"

    enrollment = models.ForeignKey(
        ProgramEnrollment, on_delete=models.CASCADE, related_name="releases"
    )
    step = models.ForeignKey(LearningProgramStep, on_delete=models.PROTECT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    access_granted_at = models.DateTimeField(blank=True, null=True)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("enrollment", "step"), name="unique_program_step_release"
            )
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.enrollment} · {self.step} · {self.get_status_display()}"

class CourseFAQ(models.Model):
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()

    def __str__(self):
        return f"FAQ: {self.question[:50]}..."

# =========================
# Custom user w/ test access
# =========================
class CustomUser(AbstractUser):
    last_account_access_at = models.DateTimeField('Son doğrulanmış hesap erişimi', null=True, blank=True, db_index=True)
    inactivity_disabled_at = models.DateTimeField('20 gün hareketsizlik nedeniyle pasife alınma', null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk and self.is_active and (kwargs.get("update_fields") is None or "is_active" in kwargs["update_fields"]):
            previous = type(self).objects.filter(pk=self.pk).values('is_active').first()
            if previous and not previous['is_active']:
                from django.utils import timezone
                self.inactivity_disabled_at = None
                self.last_account_access_at = timezone.now()
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'inactivity_disabled_at', 'last_account_access_at'}
        return super().save(*args, **kwargs)

    is_mobile = models.BooleanField(
        "Mobile", default=False, db_index=True,
        help_text="Bu hesabın mobil uygulamaya giriş yapmasına izin verir.",
    )
    mobile_full_access = models.BooleanField(
        "Mobil tam erişim", default=False, db_index=True,
        help_text="Bütün öğrenme yollarını açar. Kapalı hesap yalnızca ücretsiz yolu görür.",
    )
    mobile_email_verified = models.BooleanField("Mobil e-posta doğrulandı", default=True, help_text="Mevcut/yönetici tarafından tanımlanan hesaplar doğrulanmış kabul edilir. Yeni mobil kayıtlar e-posta onayı gerektirir.")
    mobile_must_change_password = models.BooleanField("İlk girişte şifre yenileme", default=False)
    mobile_paid_until = models.DateTimeField("Ücretli mobil erişim bitişi", null=True, blank=True, db_index=True)

    @property
    def mobile_paid(self):
        from django.utils import timezone
        return self.is_mobile and (self.mobile_full_access or bool(self.mobile_paid_until and self.mobile_paid_until > timezone.now()))

    @property
    def mobile_free(self):
        return self.is_mobile and not self.mobile_paid

    mobile_last_date = models.DateField(
        "Last date", null=True, blank=True,
        help_text="Mobil erişimin son günü (Türkiye saati). Boşsa sınırsız erişim.",
    )
    is_first_login = models.BooleanField(default=True)
    is_english = models.BooleanField(default=False)
    is_turkish = models.BooleanField(default=False)

    # Pick TEST courses per-user in admin.
    # NOTE: String 'test' avoids referencing Course before it's defined.
    allowed_tests = models.ManyToManyField(
        Course,
        blank=True,
        related_name='users_with_test_access',
        limit_choices_to={'course_type': 'test'},
    )

    def has_course_access(self, course: Course) -> bool:
        """Videos are open to all. Tests require explicit selection (or superuser)."""
        if getattr(self, "is_superuser", False):
            return True
        if course.course_type == Course.CourseType.VIDEO:
            return True
        return self.allowed_tests.filter(pk=course.pk).exists()

    def can_enroll(self, course: "Course") -> bool:
        """Sadece önceden onaylanan kullanıcılar enroll edebilir.
        - Süperuser/staff her şeye kayıt olabilir
        - Test kursları: allowed_tests içinde olmalı
        - Video kursları: (şimdilik) serbest bırakmak istiyorsan True döndür;
          sadece onayla diyorsan burada ayrı bir mekanizma eklemelisin.
        """
        if getattr(self, "is_superuser", False) or getattr(self, "is_staff", False):
            return True
        if course.course_type == Course.CourseType.TEST:
            return self.allowed_tests.filter(pk=course.pk).exists()
        # Video’ları da onaylı yapmak istiyorsan burayı False yap ve ayrı whitelist alanı ekle.
        return True  # Video’lar serbest (mevcut akışla uyumlu)


class MentorshipRequest(models.Model):
    REQUEST_TYPES = (("question", "Tek soru"), ("meeting", "Birebir görüşme"))
    STATUS = (("pending", "Bekliyor"), ("answered", "Yanıtlandı"), ("scheduled", "Planlandı"), ("closed", "Kapandı"))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentorship_requests")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="mentorship_requests")
    request_type = models.CharField(max_length=16, choices=REQUEST_TYPES)
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Birebir destek talebi"
        verbose_name_plural = "Birebir destek talepleri"

    def __str__(self):
        return f"{self.user} — {self.get_request_type_display()} — {self.course}"


class StudentMeetingBooking(models.Model):
    """Normal öğrenci hesabının Skool kimliğinden tamamen bağımsız görüşme kaydı."""

    STATUS = (("active", "Aktif"), ("completed", "Tamamlandı"), ("cancelled", "İptal"))

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_meeting_bookings"
    )
    request = models.OneToOneField(
        MentorshipRequest, on_delete=models.PROTECT, related_name="booking"
    )
    slot = models.OneToOneField(
        "skool.MeetingSlot", on_delete=models.PROTECT, related_name="student_booking"
    )
    meeting_url = models.URLField()
    status = models.CharField(max_length=16, choices=STATUS, default="active", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user",), condition=models.Q(status="active"),
                name="one_active_normal_student_booking",
            )
        ]
        verbose_name = "Öğrenci görüşme rezervasyonu"
        verbose_name_plural = "Öğrenci görüşme rezervasyonları"

    def __str__(self):
        return f"{self.user.email} — {self.slot.start_at_utc}"


from django.db.models.signals import post_save
from django.dispatch import receiver
import requests


@receiver(post_save, sender=Enrollment)
def enrollment_telegram_notification(sender, instance, created, **kwargs):
    if not created:
        return

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": f"""
🎓 Yeni Enrollment

👤 Kullanıcı:
{instance.user.email}

📚 Kurs:
{instance.course.turkish_name}

🆔 Course ID:
{instance.course.id}
"""
            },
            timeout=5,
        )
    except Exception as e:
        print("Telegram enrollment notification error:", e)

# Keep CORE's monitoring domain together while registering models in this app.
from .monitoring_models import (  # noqa: E402,F401
    MonitoringSettings, LessonEvidence, EnrollmentMonitoringPolicy, MonitoringPause,
    MonitoringLessonOverride, StudentIntervention, MonitoringAudit, DailyMonitoringSnapshot,
)


class BusinessNetworkCity(models.Model):
    city_code = models.CharField('Plaka kodu', max_length=2, primary_key=True)
    city_name = models.CharField('İl', max_length=40)
    is_active = models.BooleanField('Aktif', default=False)
    activated_at = models.DateTimeField('Aktifleştirme tarihi', null=True, blank=True)
    updated_at = models.DateTimeField('Son güncelleme', auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Güncelleyen', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ('city_code',)
        verbose_name = 'Türkiye iş ağı ili'
        verbose_name_plural = 'Türkiye İş Ağı Yönetimi'

    def clean(self):
        from django.core.exceptions import ValidationError
        from .business_network import PROVINCES
        if PROVINCES.get(self.city_code) != self.city_name:
            raise ValidationError('İl adı ve plaka kodu sabit referans verisiyle eşleşmelidir.')

    def __str__(self):
        return f'{self.city_code} — {self.city_name}'


class WeeklyTelegramSchedule(models.Model):
    from django.core.validators import MaxLengthValidator

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    monday = models.TextField('Pazartesi', blank=True, validators=[MaxLengthValidator(3500)])
    tuesday = models.TextField('Salı', blank=True, validators=[MaxLengthValidator(3500)])
    wednesday = models.TextField('Çarşamba', blank=True, validators=[MaxLengthValidator(3500)])
    thursday = models.TextField('Perşembe', blank=True, validators=[MaxLengthValidator(3500)])
    friday = models.TextField('Cuma', blank=True, validators=[MaxLengthValidator(3500)])
    saturday = models.TextField('Cumartesi', blank=True, validators=[MaxLengthValidator(3500)])
    sunday = models.TextField('Pazar', blank=True, validators=[MaxLengthValidator(3500)])

    class Meta:
        verbose_name = 'Haftalık Telegram bildirimi'
        verbose_name_plural = 'Haftalık Telegram bildirimleri'
        constraints = [models.CheckConstraint(check=models.Q(id=1), name='weekly_telegram_singleton')]

    def __str__(self):
        return 'Haftalık Telegram bildirimleri'


class ProgramProgressViolation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    course_id_snapshot = models.PositiveIntegerField()
    course_title = models.CharField(max_length=255)
    programs = models.JSONField(default=list)
    confirmation_id = models.UUIDField(unique=True)
    warning_version = models.CharField(max_length=30, default='2026-10-30-v1')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    instant_sent_at = models.DateTimeField(null=True, blank=True)
    morning_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Program ilerleme ihlali'
        verbose_name_plural = 'Program ilerleme ihlalleri'
        ordering = ['-created_at', '-pk']


from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def reset_program_progress_warning(sender, request, user, **kwargs):
    if request is not None:
        request.session.pop('program_progress_ack', None)


class ContactChangeNotice(models.Model):
    """Frozen recipient list for the October 2026 contact announcement."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)


class AccountInactivityRun(models.Model):
    disabled_accounts = models.JSONField(default=list)
    telegram_parts_sent = models.PositiveIntegerField(default=0)
    telegram_sent_at = models.DateTimeField(null=True, blank=True)
    telegram_error = models.CharField(max_length=160, blank=True)
    reporting_date = models.DateField(unique=True)
    checked_count = models.PositiveIntegerField(default=0)
    disabled_user_ids = models.JSONField(default=list)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Günlük hesap hareketsizlik kontrolü'
        verbose_name_plural = 'Günlük hesap hareketsizlik kontrolleri'
