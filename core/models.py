from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    is_first_login = models.BooleanField(default=True)


class Course(models.Model):
    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='course_images/')
    duration = models.DurationField(help_text="Format: hh:mm:ss")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    score = models.FloatField(default=0.0)
    preparer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='prepared_courses')
    description = models.TextField()
    attachments = models.FileField(upload_to='course_attachments/', null=True, blank=True)

    def __str__(self):
        return self.name


class CourseSection(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    big_title = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.course.name} - {self.big_title}"


class CourseSubsection(models.Model):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='subsections')
    small_title = models.CharField(max_length=255)
    video_url = models.URLField(blank=True, null=True)
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
