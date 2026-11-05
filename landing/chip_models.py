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


class ChipRequestRound(models.Model):
    mode = models.CharField(max_length=4, unique=True, choices=[('live', 'Katılım talepleri'), ('test', 'Test talepleri')])
    enabled = models.BooleanField('Talep formu açık', default=True)
    generation = models.UUIDField(default=uuid.uuid4, editable=False)
    requested_units = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = 'Siberkobi talep dönemi'
        verbose_name_plural = 'Siberkobi talep dönemleri'
        constraints = [models.CheckConstraint(check=models.Q(requested_units__lte=43), name='chip_request_capacity')]

    def __str__(self):
        return self.get_mode_display()


class ChipParticipationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    round = models.ForeignKey(ChipRequestRound, on_delete=models.PROTECT, related_name='requests')
    generation = models.UUIDField(editable=False)
    nonce = models.UUIDField(editable=False)
    email = models.EmailField()
    display_name = models.CharField(max_length=160, blank=True)
    duplicate_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='duplicate_links', editable=False)
    quantity = models.PositiveSmallIntegerField()
    start_position = models.PositiveSmallIntegerField(editable=False)
    provisional_percent = models.DecimalField(max_digits=23, decimal_places=20, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    email_sent_at = models.DateTimeField(null=True, editable=False)
    telegram_sent_at = models.DateTimeField(null=True, editable=False)
    notification_error = models.CharField(max_length=240, blank=True, editable=False)

    class Meta:
        verbose_name = 'Siberkobi katılım talebi (ödeme onayı değil)'
        verbose_name_plural = 'Siberkobi katılım talepleri (ödeme onayı değil)'
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['round', 'generation', 'nonce'], name='chip_request_idempotent'),
            models.UniqueConstraint(fields=['round', 'generation', 'start_position'], condition=models.Q(duplicate_of__isnull=True), name='chip_request_start_unique'),
            models.UniqueConstraint(fields=['round', 'generation', 'email'], condition=models.Q(duplicate_of__isnull=True), name='chip_request_email_once'),
            models.CheckConstraint(check=models.Q(quantity__gte=1, quantity__lte=43, start_position__gte=1) & models.Q(start_position__lte=44-models.F('quantity')), name='chip_request_position_range'),
        ]

    @property
    def end_position(self):
        return self.start_position + self.quantity - 1

    def __str__(self):
        return f'Talep {self.start_position}–{self.end_position} · {self.email}'
