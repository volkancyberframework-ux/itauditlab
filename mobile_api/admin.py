from django.contrib import admin
from .models import (
    LearningPath,
    Module,
    Question,
    AudioAsset,
    LearningSession,
    UserPathProgress,
    QuestionAttempt,
    XPTransaction,
    Subscription,
    VoiceSubmission,
    QuestionOption,
)


@admin.register(LearningPath)
class PathAdmin(admin.ModelAdmin):
    list_display = ["title", "published", "premium", "difficulty", "order"]
    list_filter = ["published", "premium", "difficulty"]
    search_fields = ["title"]


class OptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    # Private uploads cannot expose a public URL through ClearableFileInput.
    from django.db import models as django_models
    from django import forms

    formfield_overrides = {
        django_models.FileField: {"widget": forms.FileInput},
        django_models.ImageField: {"widget": forms.FileInput},
    }
    list_display = ["__str__", "kind", "published", "premium", "base_xp", "order"]
    list_filter = ["kind", "published", "premium", "difficulty"]
    filter_horizontal = ["paths"]
    search_fields = ["prompt"]


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(
    [LearningSession, UserPathProgress, QuestionAttempt, XPTransaction, Subscription],
    ReadOnlyAdmin,
)
admin.site.register(Module)


@admin.register(AudioAsset)
class AudioAdmin(admin.ModelAdmin):
    from django.db import models as django_models
    from django import forms

    formfield_overrides = {django_models.FileField: {"widget": forms.FileInput}}


@admin.register(VoiceSubmission)
class VoiceAdmin(admin.ModelAdmin):
    exclude = ["file"]
    readonly_fields = ["attempt", "duration", "created_at", "listen"]

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        from django.urls import path

        return [
            path(
                "<int:pk>/listen/",
                self.admin_site.admin_view(self.download),
                name="mobile_voice_listen",
            )
        ] + super().get_urls()

    def download(self, request, pk):
        from django.http import FileResponse, Http404

        if not request.user.has_perm("mobile_api.view_voicesubmission"):
            raise Http404()
        voice = VoiceSubmission.objects.filter(pk=pk).first()
        if not voice:
            raise Http404()
        return FileResponse(voice.file.open("rb"), content_type="audio/mp4")

    def listen(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse

        return format_html(
            '<audio controls src="{}"></audio>',
            reverse("admin:mobile_voice_listen", args=[obj.pk]),
        )
