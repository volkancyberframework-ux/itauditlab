from __future__ import annotations
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal


from django.db import models
from django.utils.text import slugify

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

    class Meta:
        unique_together = ('user', 'course')

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
