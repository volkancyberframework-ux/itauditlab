from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


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
