"""Separate test/live ledgers; payments and archived tests are retained."""
import uuid
from django.db import models


class ChipCampaign(models.Model):
    mode = models.CharField(max_length=4, unique=True, choices=[('test', 'Test'), ('live', 'Gerçek ödeme')])
    enabled = models.BooleanField('Bağlantı açık', default=False)
    generation = models.UUIDField(default=uuid.uuid4, editable=False)
    confirmed_count = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = 'Siberkobi çip kampanyası'
        verbose_name_plural = 'Siberkobi çip kampanyaları'
        constraints = [models.CheckConstraint(check=models.Q(confirmed_count__lte=43), name='chip_capacity_43')]

    def __str__(self):
        return f'Siberkobi · {self.get_mode_display()}'


class ChipPurchase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(ChipCampaign, on_delete=models.PROTECT, related_name='purchases')
    generation = models.UUIDField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    stripe_session = models.CharField(max_length=255, unique=True, null=True, editable=False)
    payment_intent = models.CharField(max_length=255, unique=True, null=True, editable=False)
    state = models.CharField(max_length=12, default='pending', choices=[('pending', 'Ödeme bekleniyor'), ('paid', 'Ödendi'), ('expired', 'Süresi doldu')])
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=255, blank=True)
    position = models.PositiveSmallIntegerField(null=True, editable=False)
    share_percent = models.DecimalField(max_digits=23, decimal_places=20, null=True, editable=False)
    paid_at = models.DateTimeField(null=True, editable=False)
    email_sent_at = models.DateTimeField(null=True, editable=False)
    telegram_sent_at = models.DateTimeField(null=True, editable=False)
    notification_error = models.CharField(max_length=240, blank=True, editable=False)
    terms_version = models.CharField(max_length=40, default='chip-disclosure-v1', editable=False)

    class Meta:
        verbose_name = 'Siberkobi çip ödemesi'
        verbose_name_plural = 'Siberkobi çip ödemeleri'
        ordering = ['position', 'created_at']
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'generation', 'position'], name='chip_unique_rank'),
            models.CheckConstraint(check=models.Q(position__isnull=True) | models.Q(position__gte=1, position__lte=43), name='chip_valid_rank'),
        ]

    def __str__(self):
        return f'{self.position or "Bekleyen"} · {self.email or self.id}'
