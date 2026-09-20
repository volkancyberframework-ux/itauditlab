from django.contrib import admin
from django.core.exceptions import ValidationError
from django import forms
from .models import Organization, Audit, Membership, Control, Activity

class OrganizationForm(forms.ModelForm):
    class Meta:
        model=Organization
        fields='__all__'
    def clean_subdomain(self):
        value=(self.cleaned_data.get('subdomain') or '').lower() or None
        if value and (value in {'www','admin','api','mail','core'} or '_' in value or value.startswith('-') or value.endswith('-')):
            raise ValidationError('Geçerli, ayrılmış olmayan bir subdomain girin.')
        return value

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    form=OrganizationForm
    list_display=('name','subdomain','slug')
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        from .notifications import queue
        queue(f'Kurum ayarı değişti: {obj.name} · {obj.subdomain} · {request.user.email}')
    def has_module_permission(self, request): return request.user.is_superuser
    def has_view_permission(self,request,obj=None): return request.user.is_superuser
    def has_change_permission(self,request,obj=None): return request.user.is_superuser
    def has_add_permission(self,request): return request.user.is_superuser
    def has_delete_permission(self,request,obj=None): return request.user.is_superuser

class OperationalAdmin(admin.ModelAdmin):
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        from .notifications import queue
        queue(f'Torbalı Belediyesi · Merkezi yönetim güncellemesi\nKayıt türü: {obj._meta.verbose_name}\nKayıt: {obj.pk}\nKullanıcı: {request.user.email}')
admin.site.register([Audit,Membership,Control],OperationalAdmin)
admin.site.site_header='Torbalı Belediyesi · Merkezi yönetim'
admin.site.site_title='Merkezi yönetim'
admin.site.index_title='Kurumlar ve denetim kullanıcıları'

from .models import Notification
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display=('id','created_at','delivered_at','attempts')
    readonly_fields=('message','created_at','delivered_at','attempts')
    actions=['retry']
    def has_add_permission(self,request):return False
    @admin.action(description='Bekleyen bildirimleri yeniden gönder')
    def retry(self,request,queryset):
        from .notifications import deliver
        for pk in queryset.filter(delivered_at__isnull=True).values_list('pk',flat=True):deliver(pk)
