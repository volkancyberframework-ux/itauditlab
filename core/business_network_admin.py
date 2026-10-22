import json
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from .models import BusinessNetworkCity
from .business_network import set_city_state

@admin.register(BusinessNetworkCity)
class BusinessNetworkCityAdmin(admin.ModelAdmin):
    change_list_template='admin/business_network_cities.html'
    list_display=('city_code','city_name','is_active','updated_at','updated_by','toggle_button')
    list_filter=('is_active',)
    search_fields=('city_code','city_name')
    readonly_fields=('city_code','city_name','activated_at','updated_at','updated_by')
    list_per_page=81
    actions=None
    def get_urls(self):
        return [path('map/<str:city_code>/',self.admin_site.admin_view(self.toggle),name='core_businessnetworkcity_toggle')]+super().get_urls()
    @method_decorator(csrf_protect)
    @method_decorator(require_http_methods(['PATCH']))
    def toggle(self,request,city_code):
        if not self.has_change_permission(request):return JsonResponse({'error':'permission_denied'},status=403)
        try:data=json.loads(request.body)
        except (ValueError,UnicodeDecodeError):return JsonResponse({'error':'invalid_json'},status=400)
        if not isinstance(data,dict) or set(data)!={'is_active'} or type(data['is_active']) is not bool:
            return JsonResponse({'error':'invalid_state'},status=400)
        try:city=set_city_state(city_code,data['is_active'],request.user)
        except BusinessNetworkCity.DoesNotExist:return JsonResponse({'error':'not_found'},status=404)
        self.log_change(request,city,'İş ağı durumu: '+str(city.is_active))
        return JsonResponse({'city_code':city.pk,'is_active':city.is_active})
    def changelist_view(self,request,extra_context=None):
        from landing.business_network import context
        return super().changelist_view(request,{**(extra_context or {}),**context(),'network_admin':self.has_change_permission(request)})
    def get_list_display(self,request):
        return self.list_display if self.has_change_permission(request) else self.list_display[:-1]
    @admin.display(description='Durum değiştir')
    def toggle_button(self,obj):
        return format_html('<button type="button" data-toggle-city="{}" aria-pressed="{}">{}</button>',obj.pk,str(obj.is_active).lower(),'Pasifleştir' if obj.is_active else 'Aktifleştir')
    def save_model(self,request,obj,form,change):
        old=BusinessNetworkCity.objects.get(pk=obj.pk)
        obj.updated_by=request.user
        if old.is_active != obj.is_active:obj.activated_at=timezone.now() if obj.is_active else None
        super().save_model(request,obj,form,change)
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False
