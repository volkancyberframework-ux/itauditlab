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
    LevelSettings,
    LevelReward,
    UserLevelReward,
    MobileSettings,
)


@admin.register(LearningPath)
class PathAdmin(admin.ModelAdmin):
    exclude = ["premium"]
    list_display = ["title", "published", "difficulty", "order"]
    list_editable = ["order"]
    list_filter = ["published", "difficulty"]
    search_fields = ["title"]


class OptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 2


from django import forms


class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .widgets import InformationPagesWidget
        self.fields["card_pages"].widget = InformationPagesWidget()
        labels = {"info": "Bilgi kartı (kaydırmalı anlatım)", "voice": "Sesli veya yazılı yanıt", "choice": "Tek seçim", "multi_select": "Çoklu seçim", "fill_blank": "Boşluk doldurma", "text": "Kısa yazılı yanıt", "image": "Görsel soru", "audio": "Ses kaydını dinle", "scenario": "Senaryo", "sentence_order": "Sürükleyerek cümle kur", "drag_select": "Kart kaydır ve taşı"}
        self.fields["kind"].choices = [(value, labels.get(value, label)) for value, label in self.fields["kind"].choices]
        self.fields["order"].help_text = "Yol içindeki gösterim sırası. Üç sorudan sonra bilgi kartı için: sorular 0, 1, 2; bilgi kartı 3; sonraki soru 4. Kartları da aynı yola bağlayın."
        self.fields["answer"].help_text = 'voice için tek doğru metin: ["veri kaybı"]. sentence_order için parça ID' + " listesi doğru sırada olmalı. Bilgi kartında boş bırakın."

    class Meta:
        model = Question
        fields = '__all__'

    def clean(self):
        data = super().clean()
        if data.get('kind') == 'voice':
            answer = data.get('answer')
            if not isinstance(answer, list) or len(answer) != 1 or not isinstance(answer[0], str) or not answer[0].strip():
                self.add_error('answer', 'Sesli/yazılı soru için tek bir doğru metin yazın: ["veri kaybı"].')
        if data.get('kind') == 'info':
            pages = data.get('card_pages')
            if not isinstance(pages, list) or not 1 <= len(pages) <= 12:
                self.add_error('card_pages', '1–12 sayfa ekleyin. Her sayfada title ve body, isteğe bağlı reveal bulunabilir.')
            elif any(not isinstance(page, dict) or not isinstance(page.get('body'), str) or not page['body'].strip() or any(not isinstance(page.get(key, ''), str) for key in ['title', 'reveal']) for page in pages):
                self.add_error('card_pages', 'Her sayfanın body alanına metin yazın; title ve reveal de metin olmalı.')
        return data


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionForm
    exclude = ["premium"]
    inlines = [OptionInline]
    # Private uploads cannot expose a public URL through ClearableFileInput.
    from django.db import models as django_models
    from django import forms

    formfield_overrides = {
        django_models.FileField: {"widget": forms.FileInput},
        django_models.ImageField: {"widget": forms.FileInput},
    }
    list_display = ["__str__", "kind", "published", "base_xp", "order"]
    list_editable = ["order"]
    list_filter = ["kind", "paths", "published", "difficulty"]
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
    readonly_fields = ["attempt", "duration", "created_at", "listen", "review_due_at", "feedback_sent_at"]
    list_display = ["id", "learner", "created_at", "review_due_at", "review_status", "feedback_sent_at"]
    list_filter = ["review_status", "feedback_sent_at"]
    search_fields = ["attempt__session__user__email", "feedback"]
    actions = ["send_feedback"]

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if obj and obj.feedback_sent_at:
            fields += ["feedback", "review_status"]
        return fields

    def learner(self, obj):
        return obj.attempt.session.user.email

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.review_status == "reviewed" and not obj.feedback_sent_at:
            self._send(request, obj)

    def _send(self, request, obj):
        from .feedback import send_voice_feedback
        try:
            if send_voice_feedback(obj.pk):
                self.message_user(request, f"{obj.attempt.session.user.email} adresine geri bildirim gönderildi.")
        except Exception:
            self.message_user(request, "E-posta gönderilemedi. Geri bildirimi ve e-posta ayarlarını kontrol edip 'Geri bildirimi e-postayla gönder' işlemini tekrar deneyin.", level="error")

    @admin.action(description="Geri bildirimi e-postayla gönder (incelenmiş kayıtlar)")
    def send_feedback(self, request, queryset):
        for obj in queryset:
            self._send(request, obj)

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


@admin.register(LevelSettings)
class LevelSettingsAdmin(admin.ModelAdmin):
    fields = ['xp_per_level']

    def has_add_permission(self, request):
        return not LevelSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LevelReward)
class LevelRewardAdmin(admin.ModelAdmin):
    list_display = ['level', 'title', 'kind', 'published']
    list_filter = ['published', 'kind']
    search_fields = ['title', 'description']


@admin.register(UserLevelReward)
class UserLevelRewardAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'earned_at', 'delivered_at']
    list_filter = ['reward', 'delivered_at']
    search_fields = ['user__username', 'user__email', 'reward__title']
    readonly_fields = ['user', 'reward', 'earned_at']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MobileSettings)
class MobileSettingsAdmin(admin.ModelAdmin):
    fields = ['free_path', 'whatsapp_phone']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'free_path':
            kwargs['queryset'] = LearningPath.objects.filter(published=True, owner=None)
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'free_path':
            field.required = True
        return field

    def has_add_permission(self, request):
        return not MobileSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
