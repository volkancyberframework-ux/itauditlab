import secrets

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Count
from django.utils import timezone
from django.urls import reverse

from .models import (
    AvailabilityException, BookingHistory, CareerTestAnswer, MeetingBooking, MeetingSlot,
    NotificationLog, OnboardingEvent, SkoolInvitation, SkoolSettings, SkoolUser,
    TravelAvailability, SkoolLab,
)


class AnswerInline(admin.TabularInline):
    model = CareerTestAnswer
    extra = 0
    can_delete = False
    readonly_fields = ("question_id", "question_text", "selected_option", "answered_at")


class EventInline(admin.TabularInline):
    model = OnboardingEvent
    extra = 0
    can_delete = False
    readonly_fields = ("event_type", "detail", "created_at")


class OptionalEndDateForm(forms.ModelForm):
    """Tek gün için bitşi boş bırakır; aralık için ikinci tarihi kullanır."""
    end_date = forms.DateField(
        required=False,
        label="Bitiş tarihi (aralık için)",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Tek gün seçiyorsanız boş bırakın.",
    )

    class Meta:
        fields = "__all__"
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("start_date") and not cleaned.get("end_date"):
            cleaned["end_date"] = cleaned["start_date"]
            self.instance.end_date = cleaned["start_date"]
        return cleaned


class TravelAvailabilityForm(OptionalEndDateForm):
    class Meta(OptionalEndDateForm.Meta):
        model = TravelAvailability


class AvailabilityExceptionForm(OptionalEndDateForm):
    class Meta(OptionalEndDateForm.Meta):
        model = AvailabilityException


@admin.register(SkoolInvitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "status", "created_at", "claimed_at")
    list_filter = ("status", "created_at")
    search_fields = ("full_name", "normalized_name")
    readonly_fields = ("normalized_name", "token_hash", "created_at", "claimed_at", "revoked_at")

    def save_model(self, request, obj, form, change):
        if not change and not obj.token_hash:
            raw = secrets.token_urlsafe(32)
            obj.token_hash = SkoolInvitation.hash_token(raw)
            request._skool_invite_token = raw
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        raw = getattr(request, "_skool_invite_token", "")
        if raw:
            base = getattr(settings, "PUBLIC_BASE_URL", "https://www.grcustasi.com").rstrip("/")
            self.message_user(request, f"Davet bağlantısı: {base}{reverse('skool:onboarding')}?invite={raw}", messages.SUCCESS)
        return super().response_add(request, obj, post_url_continue)


@admin.register(SkoolLab)
class SkoolLabAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active", "created_at")
    list_editable = ("order", "is_active")
    search_fields = ("title", "description")


@admin.register(SkoolUser)
class SkoolUserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "state", "current_question", "test_completed_at", "audio_completed_at", "updated_at")
    list_filter = ("state", "test_completed_at", "audio_completed_at")
    search_fields = ("full_name",)
    readonly_fields = tuple(field.name for field in SkoolUser._meta.fields)
    inlines = (AnswerInline, EventInline)


@admin.register(TravelAvailability)
class TravelAvailabilityAdmin(admin.ModelAdmin):
    form = TravelAvailabilityForm
    list_display = ("location_name", "timezone", "start_date", "end_date", "local_available_start", "local_available_end", "enabled", "booking_count", "needs_attention")
    list_filter = ("enabled", "timezone")
    search_fields = ("location_name", "timezone")
    actions = ("regenerate_future_slots",)

    @admin.action(description="Aktif rezervasyonu olmayan gelecek slotları yeniden üret")
    def regenerate_future_slots(self, request, queryset):
        from .services import ensure_upcoming_slots

        blocked = []
        regenerated = 0
        for availability in queryset:
            if MeetingBooking.objects.filter(
                slot__availability=availability,
                status="active",
                slot__start_at_utc__gte=timezone.now(),
            ).exists():
                blocked.append(availability.location_name)
                continue
            availability.slots.filter(
                start_at_utc__gte=timezone.now(), status="available"
            ).delete()
            regenerated += 1
        if regenerated:
            ensure_upcoming_slots()
            self.message_user(request, f"{regenerated} uygunluk için gelecek slotlar güvenle yeniden üretildi.", messages.SUCCESS)
        if blocked:
            self.message_user(
                request,
                "Aktif rezervasyon bulunduğu için değiştirilmeyen planlar: " + ", ".join(blocked),
                messages.WARNING,
            )

    @admin.display(description="Aktif görüşme")
    def booking_count(self, obj):
        return MeetingBooking.objects.filter(slot__availability=obj, status="active").count()

    @admin.display(description="Plan kontrolü", boolean=True)
    def needs_attention(self, obj):
        return MeetingBooking.objects.filter(slot__availability=obj, status="active").exclude(slot__local_date__range=(obj.start_date, obj.end_date)).exists()


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    form = AvailabilityExceptionForm
    list_display = ("start_date", "end_date", "availability", "reason", "active_booking_warning")
    list_filter = ("start_date", "availability")

    @admin.display(description="Uyarı")
    def active_booking_warning(self, obj):
        count = MeetingBooking.objects.filter(status="active", slot__local_date__range=(obj.start_date, obj.end_date)).count()
        return f"Bu aralıkta {count} aktif görüşme var" if count else "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        slots = MeetingSlot.objects.filter(
            local_date__range=(obj.start_date, obj.end_date), status="available"
        )
        if obj.availability_id:
            slots = slots.filter(availability=obj.availability)
        disabled = slots.update(status="disabled")
        if disabled:
            self.message_user(request, f"{disabled} boş görüşme saati bu istisna nedeniyle kapatıldı.", messages.INFO)


@admin.register(MeetingSlot)
class MeetingSlotAdmin(admin.ModelAdmin):
    list_display = ("local_date", "start_at_utc", "end_at_utc", "availability", "status")
    list_filter = ("status", "local_date", "availability")
    readonly_fields = ("created_at",)


@admin.register(MeetingBooking)
class MeetingBookingAdmin(admin.ModelAdmin):
    list_display = ("user", "slot", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__full_name",)
    readonly_fields = ("created_at", "updated_at", "cancelled_at")


@admin.register(BookingHistory)
class BookingHistoryAdmin(admin.ModelAdmin):
    list_display = ("booking", "old_slot", "new_slot", "changed_at")
    readonly_fields = ("booking", "old_slot", "new_slot", "changed_at")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("notification_type", "key", "sent_at")
    readonly_fields = ("notification_type", "key", "detail", "sent_at")


@admin.register(SkoolSettings)
class SkoolSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SkoolSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
