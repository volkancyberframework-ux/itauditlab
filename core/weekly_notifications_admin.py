from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from core.models import WeeklyTelegramSchedule
from core.weekly_notifications import WEEKDAYS


@admin.register(WeeklyTelegramSchedule)
class WeeklyTelegramScheduleAdmin(admin.ModelAdmin):
    fields = WEEKDAYS
    formfield_overrides = {
        WeeklyTelegramSchedule._meta.get_field('monday').__class__: {
            'widget': forms.Textarea(attrs={'rows': 5, 'cols': 90, 'maxlength': 3500}),
            'help_text': 'Her hafta bu gün, Türkiye saatiyle 05:00’te gönderilir. Boş bırakırsanız ek bildirim gönderilmez. En fazla 3500 karakter.',
        },
    }

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_or_change_permission(request):
            return super().changelist_view(request, extra_context)
        if WeeklyTelegramSchedule.objects.filter(pk=1).exists():
            return redirect(reverse('admin:core_weeklytelegramschedule_change', args=[1]))
        if self.has_add_permission(request):
            return redirect(reverse('admin:core_weeklytelegramschedule_add'))
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not WeeklyTelegramSchedule.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
