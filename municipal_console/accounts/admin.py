from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class ConsoleUserAdmin(UserAdmin):
    readonly_fields=('privacy_accepted_at','privacy_version')
    ordering=('email',)
    search_fields=('email','first_name','last_name')
    list_display=('email','first_name','last_name','is_staff','is_active')
    fieldsets=((None,{'fields':('email','password')}),('Profil',{'fields':('first_name','last_name','must_change_password')}),('Yetkiler',{'fields':('is_active','is_staff','is_superuser','groups','user_permissions')}))
    add_fieldsets=((None,{'classes':('wide',),'fields':('email','first_name','last_name','password1','password2')}),)
    fieldsets=fieldsets+(('Gizlilik onayı',{'fields':('privacy_accepted_at','privacy_version')}),)
