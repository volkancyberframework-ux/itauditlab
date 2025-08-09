from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


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
    dashboard_activated = models.BooleanField(default=False)  # New
    main_page_activated = models.BooleanField(default=False)  # New
    is_english = models.BooleanField(default=False)  # New
    is_turkish = models.BooleanField(default=False)

def __str__(self):
    return self.turkish_name or self.english_name or f"Course #{self.pk}"

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
