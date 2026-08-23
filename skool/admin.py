from django.contrib import admin, messages
from django.db.models import Count
from django.utils import timezone

from .models import (
    AvailabilityException, BookingHistory, CareerTestAnswer, MeetingBooking, MeetingSlot,
    NotificationLog, OnboardingEvent, SkoolInvitation, SkoolSettings, SkoolUser,
    TravelAvailability,
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


@admin.register(SkoolInvitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "status", "created_at", "claimed_at")
    list_filter = ("status", "created_at")
    search_fields = ("full_name", "normalized_name")
    readonly_fields = ("normalized_name", "token_hash", "created_at", "claimed_at", "revoked_at")


@admin.register(SkoolUser)
class SkoolUserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "state", "current_question", "test_completed_at", "audio_completed_at", "updated_at")
    list_filter = ("state", "test_completed_at", "audio_completed_at")
    search_fields = ("full_name",)
    readonly_fields = tuple(field.name for field in SkoolUser._meta.fields)
    inlines = (AnswerInline, EventInline)


@admin.register(TravelAvailability)
class TravelAvailabilityAdmin(admin.ModelAdmin):
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
    list_display = ("start_date", "end_date", "availability", "reason", "active_booking_warning")
    list_filter = ("start_date", "availability")

    @admin.display(description="Uyarı")
    def active_booking_warning(self, obj):
        count = MeetingBooking.objects.filter(status="active", slot__local_date__range=(obj.start_date, obj.end_date)).count()
        return f"Bu aralıkta {count} aktif görüşme var" if count else "—"


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
