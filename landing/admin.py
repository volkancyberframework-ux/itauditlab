from django.contrib import admin
from .models import AssessmentSession, Certificate, JobMarketCount, Lead, SiteSetting, WaitingList


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = ('email','profile_type','discount_percent','discount_expires_at','completed','updated_at')
    list_filter = ('profile_type','discount_percent','completed','created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at','updated_at')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name','email','profile_type','residence_type','region','result_type','discount_percent','discount_expires_at','created_at')
    list_filter = ('profile_type','residence_type','region','career_clarity','opportunity_awareness','effort_awareness','ethics_commitment','result_type','student_discount_eligible','created_at')
    search_fields = ('name','email','whatsapp')
    readonly_fields = ('test_score','result_type','created_at')

@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = ('name','email','whatsapp','created_at'); search_fields = ('name','email','whatsapp')

@admin.register(JobMarketCount)
class JobMarketAdmin(admin.ModelAdmin):
    list_display = ('country','grc','source_label','is_demo','last_checked_at','updated_at')
    list_filter = ('is_demo','source_label')
    search_fields = ('country','source_label')

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_id','participant_name','issue_date','expiry_date','status'); search_fields = ('certificate_id','participant_name'); list_filter = ('status',)

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return not SiteSetting.objects.exists()
    def has_delete_permission(self, request, obj=None): return False
