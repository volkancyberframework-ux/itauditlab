import uuid
from django.conf import settings
from django.db import models
from .storage import PrivateVoiceStorage


class LearningPath(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=32, default="shield")
    color = models.CharField(max_length=7, default="#166B5B")
    difficulty = models.CharField(max_length=16, default="beginner")
    minutes = models.PositiveIntegerField(default=10)
    premium = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE
    )
    preferences = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Module(models.Model):
    path = models.ForeignKey(
        LearningPath, on_delete=models.CASCADE, related_name="modules"
    )
    title = models.CharField(max_length=180)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class AudioAsset(models.Model):
    title = models.CharField(max_length=180)
    file = models.FileField(upload_to="audio/", storage=PrivateVoiceStorage())
    name_key = models.CharField(max_length=120, blank=True, db_index=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    TYPES = [
        (v, v)
        for v in [
            "choice",
            "multi_select",
            "fill_blank",
            "text",
            "image",
            "audio",
            "scenario",
            "voice",
            "sentence_order",
            "drag_select",
        ]
    ]
    module = models.ForeignKey(Module, null=True, blank=True, on_delete=models.SET_NULL)
    paths = models.ManyToManyField(LearningPath, related_name="questions", blank=True)
    kind = models.CharField(max_length=20, choices=TYPES)
    prompt = models.TextField()
    context = models.TextField(blank=True)
    options = models.JSONField(
        default=list, blank=True, help_text='[{"id":"a","text":"..."}]'
    )
    answer = models.JSONField(
        default=list,
        blank=True,
        help_text="Doğru seçenek ID listesi veya kabul edilen metinler. sentence_order için ID'leri doğru cümle sırasıyla yazın; şıklardaki correct işaretleri bu türde kullanılmaz.",
    )
    explanation = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="images/", storage=PrivateVoiceStorage(), blank=True
    )
    audio = models.ForeignKey(
        AudioAsset, null=True, blank=True, on_delete=models.SET_NULL
    )
    intro = models.ForeignKey(
        AudioAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    difficulty = models.CharField(max_length=16, default="beginner")
    goals = models.JSONField(
        default=list,
        blank=True,
        help_text="Hedef adları: Sertifika, Denetim, Teknik bilgi vb.",
    )
    base_xp = models.PositiveIntegerField(default=10)
    premium = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.prompt[:80]


class LearningSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    questions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class UserPathProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    completed = models.ManyToManyField(Question, blank=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "path"], name="mobile_user_path_unique"
            )
        ]


class QuestionAttempt(models.Model):
    session = models.ForeignKey(
        LearningSession, on_delete=models.CASCADE, related_name="attempts"
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer = models.JSONField()
    is_correct = models.BooleanField()
    xp_change = models.IntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"], name="mobile_session_question_unique"
            )
        ]


class XPTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    attempt = models.OneToOneField(QuestionAttempt, on_delete=models.PROTECT)
    amount = models.IntegerField()
    reason = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=255, unique=True)
    product_id = models.CharField(max_length=100, default="grcustasi_premium_monthly")
    status = models.CharField(
        max_length=20,
        choices=[
            (s, s) for s in ["trial", "active", "expired", "cancelled", "grace_period"]
        ],
    )
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField()


class VoiceSubmission(models.Model):
    attempt = models.OneToOneField(QuestionAttempt, on_delete=models.CASCADE)
    file = models.FileField(upload_to="recordings/", storage=PrivateVoiceStorage())
    duration = models.PositiveIntegerField()
    review_status = models.CharField(
        max_length=12,
        default="pending",
        choices=[("pending", "pending"), ("reviewed", "reviewed")],
    )
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AnalyticsEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)


class QuestionOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answer_options"
    )
    key = models.CharField(max_length=40)
    text = models.CharField(max_length=500)
    correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "key"], name="mobile_question_option_key"
            )
        ]


class BillingIdentity(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
