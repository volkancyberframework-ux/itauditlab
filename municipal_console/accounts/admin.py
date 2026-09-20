from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class ConsoleUserAdmin(UserAdmin):
    ordering=('email',)
    list_display=('email','first_name','last_name','is_staff','is_active')
    fieldsets=((None,{'fields':('email','password')}),('Profil',{'fields':('first_name','last_name','must_change_password')}),('Yetkiler',{'fields':('is_active','is_staff','is_superuser','groups','user_permissions')}))
    add_fieldsets=((None,{'classes':('wide',),'fields':('email','password1','password2')}),)
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        from workspace.notifications import queue
        queue(f'Konsol hesabı güncellendi: {obj.email} · İşlemi yapan: {request.user.email}')
