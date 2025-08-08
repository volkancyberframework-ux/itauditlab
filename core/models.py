from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from .validators import validate_youtube_url


class CustomUser(AbstractUser):
    is_first_login = models.BooleanField(default=True)
    is_english = models.BooleanField(default=False)
    is_turkish = models.BooleanField(default=False)


class Course(models.Model):
    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    turkish_name = models.CharField(max_length=255)
    english_name = models.CharField(max_length=255, blank=True, null=True)  # New
    image = models.ImageField(upload_to='course_images/')
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
    attachment = models.URLField(blank=True, null=True)
    dashboard_activated = models.BooleanField(default=False)  # New
    main_page_activated = models.BooleanField(default=False)  # New
    is_english = models.BooleanField(default=False)  # New
    is_turkish = models.BooleanField(default=False)

def __str__(self):
    return self.english_name

class CourseSection(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    big_title = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.course.name} - {self.big_title}"


class CourseSubsection(models.Model):
    section = models.ForeignKey('CourseSection', on_delete=models.CASCADE, related_name='subsections')
    small_title = models.CharField(max_length=255)
    video_url = models.URLField(
        blank=True, null=True,
        validators=[validate_youtube_url],
        help_text="Paste a YouTube link (watch, youtu.be, shorts, or embed)."
    )
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
