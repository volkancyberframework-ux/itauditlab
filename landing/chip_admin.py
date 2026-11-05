from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path
from .chip_models import ChipCampaign, ChipPurchase


@admin.register(ChipCampaign)
class ChipCampaignAdmin(admin.ModelAdmin):
    change_form_template = 'admin/chip_campaign_change.html'
    list_display = ['mode', 'enabled', 'confirmed_count']
    readonly_fields = ['mode', 'generation', 'confirmed_count']
    fields = ['mode', 'enabled', 'generation', 'confirmed_count']

    def get_urls(self):
        return [path('test-reset/', self.admin_site.admin_view(self.test_reset), name='chip_test_reset')] + super().get_urls()

    def test_reset(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        done = False
        if request.method == 'POST' and request.POST.get('confirm') == 'TEST SIFIRLA':
            from .chip import reset_test
            reset_test()
            done = True
            self.message_user(request, 'Test sayacı sıfırlandı ve test bağlantısı kapatıldı. Eski kayıtlar arşivde; gerçek ödeme kayıtları korundu.', messages.SUCCESS)
        return TemplateResponse(request, 'admin/chip_test_reset.html', {
            **self.admin_site.each_context(request), 'title': 'Siberkobi test sayacını sıfırla', 'done': done})

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChipPurchase)
class ChipPurchaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'campaign', 'position', 'email', 'share_percent', 'state', 'paid_at', 'notification_error']
    list_filter = ['campaign__mode', 'state', 'generation']
    search_fields = ['email', 'name', 'stripe_session', 'payment_intent']
    readonly_fields = [field.name for field in ChipPurchase._meta.fields]
    actions = ['retry_notifications']

    @admin.action(description='Bekleyen e-posta / Telegram bildirimlerini yeniden dene')
    def retry_notifications(self, request, queryset):
        from .chip import notify
        for pk in queryset.filter(state='paid').values_list('pk', flat=True):
            notify(pk)
        self.message_user(request, 'Bildirimler kontrol edildi; sonuçlar kayıtların üzerinde görülebilir.')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


from .chip_models import ChipRequestRound, ChipParticipationRequest


@admin.register(ChipRequestRound)
class ChipRequestRoundAdmin(admin.ModelAdmin):
    change_form_template = 'admin/chip_request_round.html'
    list_display = ['mode', 'enabled', 'requested_units']
    readonly_fields = ['mode', 'generation', 'requested_units']
    fields = ['mode', 'enabled', 'generation', 'requested_units']

    def get_urls(self):
        return [path('archive/', self.admin_site.admin_view(self.archive), name='chip_request_archive')] + super().get_urls()

    def archive(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        done = False
        if request.method == 'POST' and request.POST.get('confirm') == 'TALEPLERİ ARŞİVLE' and request.POST.get('mode') in ('live', 'test'):
            from .chip_requests import archive_round
            archive_round(request.POST['mode'])
            done = True
            self.message_user(request, 'Talep sayacı sıfırlandı; eski talepler arşivlendi. Ödeme kayıtları değişmedi.')
        return TemplateResponse(request, 'admin/chip_request_archive.html', {
            **self.admin_site.each_context(request), 'title': 'Talep dönemini arşivle', 'done': done})

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChipParticipationRequest)
class ChipParticipationRequestAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'email', 'round', 'quantity', 'start_position', 'provisional_percent', 'duplicate_of', 'created_at', 'notification_error']
    list_filter = ['round__mode', 'generation']
    search_fields = ['email']
    readonly_fields = [field.name for field in ChipParticipationRequest._meta.fields]
    actions = ['retry_request_notifications']

    @admin.action(description='Bekleyen talep bildirimlerini yeniden dene')
    def retry_request_notifications(self, request, queryset):
        from .chip_requests import notify
        for pk in queryset.values_list('pk', flat=True):
            notify(pk)
        self.message_user(request, 'Talep bildirimleri kontrol edildi. Bu kayıtlar ödeme onayı değildir.')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
