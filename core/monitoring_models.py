"""CORE monitoring records. Access to courses remains governed by existing models."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class MonitoringSettings(models.Model):
    mode = models.CharField('Gecikme kuralı', max_length=10, choices=[('next', 'Sonraki ders kuralı'), ('days', 'Gün eşiği')], default='next')
    days = models.PositiveIntegerField('Tamamlama süresi (gün)', default=3, validators=[MinValueValidator(1), MaxValueValidator(365)])
    last_lesson_days = models.PositiveIntegerField('Son ders için gün eşiği (0: kapalı)', default=0, validators=[MaxValueValidator(365)])
    critical_lessons = models.PositiveIntegerField('Kritik gecikmiş ders sayısı', default=3, validators=[MinValueValidator(1), MaxValueValidator(10000)])
    critical_days = models.PositiveIntegerField('Kritik ortalama gecikme (gün)', default=7, validators=[MinValueValidator(1), MaxValueValidator(3650)])
    administrative_timezone = models.CharField('Yönetim saat dilimi', max_length=64, default='Europe/Istanbul')

    class Meta:
        verbose_name = 'Öğrenci İlerlemesi ve Müdahale'
        verbose_name_plural = 'Öğrenci İlerlemesi ve Müdahale'

    def clean(self):
        try:
            ZoneInfo(self.administrative_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError({'administrative_timezone': 'Geçerli bir IANA saat dilimi girin.'})


class LessonEvidence(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    course = models.ForeignKey('core.Course', on_delete=models.PROTECT)
    first_accessed_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    completion_known = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    evidence = models.TextField(blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'course'], name='unique_core_lesson_evidence')]
        verbose_name = 'Ders tamamlanma kanıtı'
        verbose_name_plural = 'Ders tamamlanma kanıtları'


class EnrollmentMonitoringPolicy(models.Model):
    enrollment = models.OneToOneField('core.ProgramEnrollment', on_delete=models.CASCADE, related_name='monitoring_policy')
    status = models.CharField(max_length=12, default='active', choices=[('active', 'Aktif'), ('paused', 'Duraklatıldı'), ('archived', 'Arşivlendi'), ('completed', 'Tamamlandı')])
    class Meta:
        verbose_name = 'İzleme kayıt durumu'
        verbose_name_plural = 'İzleme kayıt durumları'


class MonitoringPause(models.Model):
    enrollment = models.ForeignKey('core.ProgramEnrollment', on_delete=models.CASCADE, related_name='monitoring_pauses')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    class Meta:
        indexes = [models.Index(fields=['enrollment', 'started_at'])]


class MonitoringLessonOverride(models.Model):
    enrollment = models.ForeignKey('core.ProgramEnrollment', on_delete=models.CASCADE, related_name='monitoring_overrides')
    step = models.ForeignKey('core.LearningProgramStep', on_delete=models.PROTECT)
    exempt = models.BooleanField(default=False)
    required = models.BooleanField(default=True)
    access_granted_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=['enrollment', 'step'], name='unique_core_monitor_override')]


class StudentIntervention(models.Model):
    STATUSES = [('draft', 'Taslak'), ('opened', 'E-posta uygulaması açıldı'), ('sent', 'Elle gönderildi işaretlendi'), ('awaiting', 'Yanıt bekleniyor'), ('responded', 'Yanıt alındı'), ('meeting', 'Görüşme planlandı'), ('resolved', 'Çözüldü')]
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='core_interventions')
    enrollment_ids = models.JSONField(default=list)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    progress_snapshot = models.JSONField(default=dict)
    monitoring_settings = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=STATUSES, default='draft', db_index=True)
    marked_sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    marked_sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['student', 'status', 'created_at'])]
        verbose_name = 'Öğrenci müdahalesi'
        verbose_name_plural = 'Öğrenci müdahale geçmişi'


class MonitoringAudit(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    actor_email = models.EmailField(blank=True)
    action = models.CharField(max_length=60)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    intervention = models.ForeignKey(StudentIntervention, null=True, on_delete=models.PROTECT)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = 'İzleme işlem kaydı'
        verbose_name_plural = 'İzleme denetim izi'


class DailyMonitoringSnapshot(models.Model):
    reporting_date = models.DateField(unique=True)
    captured_at = models.DateTimeField(auto_now_add=True)
    settings_snapshot = models.JSONField(default=dict)
    students = models.JSONField(default=list)
    metrics = models.JSONField(default=dict)
    class Meta:
        ordering = ['reporting_date']
        verbose_name = 'Günlük izleme özeti'
        verbose_name_plural = 'Günlük izleme özetleri'
