from io import BytesIO
from PIL import Image, UnidentifiedImageError
from django.contrib import admin
from django.core.exceptions import ValidationError
from django import forms
from .models import Organization,Audit,Membership,Control,Notification,ControlEmail

class OrganizationForm(forms.ModelForm):
    logo=forms.ImageField(label='Kurum logosu',required=False,help_text='PNG, JPEG veya GIF; en fazla 2 MB. Veritabanında kalıcı saklanır.')
    remove_logo=forms.BooleanField(label='Yüklenen logoyu kaldır',required=False)
    class Meta:
        model=Organization
        fields=['name','slug','subdomain']
        labels={'name':'Kurum adı','slug':'Kurum kayıt kodu','subdomain':'Subdomain'}
    def clean_subdomain(self):
        value=(self.cleaned_data.get('subdomain') or '').lower() or None
        if value and (value in {'www','admin','api','mail','core','akademi','itauditlab'} or '_' in value or value.startswith('-') or value.endswith('-')):
            raise ValidationError('Geçerli, ayrılmış olmayan bir subdomain girin.')
        return value
    def clean_logo(self):
        upload=self.cleaned_data.get('logo')
        if not upload:return None
        if upload.size>2*1024*1024:raise ValidationError('Logo en fazla 2 MB olabilir.')
        try:
            im=Image.open(upload)
            if im.format not in ('PNG','JPEG','GIF') or im.width*im.height>16_000_000:raise ValueError()
            im.seek(0);im=im.convert('RGBA');im.thumbnail((1600,1600))
            out=BytesIO();im.save(out,format='PNG');self.normalized_logo=out.getvalue()
        except (ValueError,OSError,Image.DecompressionBombError):raise ValidationError('Geçerli bir PNG, JPEG veya GIF seçin (en fazla 16 megapiksel).')
        return upload
    def save(self,commit=True):
        obj=super().save(commit=False)
        if self.cleaned_data.get('remove_logo'):obj.logo_data=b''
        elif self.cleaned_data.get('logo'):obj.logo_data=self.normalized_logo
        if commit:obj.save()
        return obj

class SuperuserAdmin(admin.ModelAdmin):
    def has_module_permission(self,request):return request.user.is_superuser
    def has_view_permission(self,request,obj=None):return request.user.is_superuser
    def has_change_permission(self,request,obj=None):return request.user.is_superuser
    def has_add_permission(self,request):return request.user.is_superuser
    def has_delete_permission(self,request,obj=None):return request.user.is_superuser
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        from .notifications import queue
        queue(f'Merkezi yönetim güncellemesi · {obj._meta.verbose_name} #{obj.pk}\nKullanıcı: {request.user.email}')

@admin.register(Organization)
class OrganizationAdmin(SuperuserAdmin):
    form=OrganizationForm
    list_display=('name','subdomain','slug')
    search_fields=('name','subdomain')
    readonly_fields=('logo_preview',)
    def logo_preview(self,obj):
        from django.utils.html import format_html
        from .branding import organization_brand
        return format_html('<img src="{}" alt="Kurum logosu" style="max-width:240px;max-height:120px;background:white;padding:8px">',organization_brand(obj)['brand_logo_url'])
    logo_preview.short_description='Mevcut logo'

class MembershipInline(admin.TabularInline):
    model=Membership
    extra=1
    autocomplete_fields=['user']

@admin.register(Audit)
class AuditAdmin(SuperuserAdmin):
    list_display=('title','organization','phase','archived')
    list_filter=('organization','phase','archived')
    search_fields=('title','organization__name')
    fields=('organization','title','is_demo','archived','phase')
    readonly_fields=('phase',)
    inlines=[MembershipInline]
    def view_on_site(self,obj):return f'/console/?audit={obj.pk}'

@admin.register(Control)
class ControlAdmin(SuperuserAdmin):
    list_display=('code','title','audit','risk')
    list_filter=('audit','risk','framework')
    search_fields=('code','title','description')
    autocomplete_fields=['audit']
    def get_readonly_fields(self,request,obj=None):return ('audit',) if obj else ()
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        if not change and obj.audit.phase=='completed' and not obj.audit.membership_set.filter(role='it',user__is_active=True).exists():
            from django.contrib import messages
            self.message_user(request,'Kontrol eklendi; bu denetime aktif BT sorumlusu atanmadığı için e-posta alıcısı yok.',level=messages.WARNING)

@admin.register(Membership)
class MembershipAdmin(SuperuserAdmin):
    list_display=('user','audit','role')
    list_filter=('role','audit')
    autocomplete_fields=['user','audit']

@admin.register(Notification)
class NotificationAdmin(SuperuserAdmin):
    list_display=('id','created_at','delivered_at','attempts')
    readonly_fields=('message','created_at','delivered_at','attempts')
    actions=['retry']
    def has_add_permission(self,request):return False
    @admin.action(description='Bekleyen Telegram bildirimlerini yeniden gönder')
    def retry(self,request,queryset):
        from .notifications import deliver
        for pk in queryset.filter(delivered_at__isnull=True).values_list('pk',flat=True):deliver(pk)

@admin.register(ControlEmail)
class ControlEmailAdmin(SuperuserAdmin):
    list_display=('control','email','created_at','delivered_at','attempts')
    readonly_fields=('control','recipient','email','subject','body','created_at','delivered_at','attempts')
    actions=['retry']
    def has_add_permission(self,request):return False
    @admin.action(description='Bekleyen kontrol e-postalarını yeniden gönder')
    def retry(self,request,queryset):
        from .notifications import deliver_email
        for pk in queryset.filter(delivered_at__isnull=True).values_list('pk',flat=True):deliver_email(pk)

admin.site.site_header='Merkezi denetim yönetimi'
admin.site.site_title='Merkezi yönetim'
admin.site.index_title='Kurumlar, denetimler ve kullanıcılar'
