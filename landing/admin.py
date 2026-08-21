from django.contrib import admin
from .models import (
    AssessmentSession, Certificate, CorporateInquiry, DailyTrafficMetric, DailyTrafficReport,
    JobMarketCount, LandingVisit, Lead, NewsletterSubscriber, PartnerApplication,
    SiteSetting, WaitingList,
)


@admin.register(CorporateInquiry)
class CorporateInquiryAdmin(admin.ModelAdmin):
    list_display = ('company', 'name', 'service', 'employee_count', 'email', 'created_at')
    list_filter = ('service', 'employee_count', 'created_at')
    search_fields = ('company', 'name', 'email', 'phone', 'message')
    readonly_fields = ('created_at',)


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'partnership_type', 'company_role', 'email', 'created_at')
    list_filter = ('partnership_type', 'created_at')
    search_fields = ('name', 'email', 'phone', 'company_role', 'message')
    readonly_fields = ('created_at',)


@admin.register(LandingVisit)
class LandingVisitAdmin(admin.ModelAdmin):
    list_display = ('visit_date', 'short_visitor', 'page_views', 'is_returning', 'first_path', 'last_seen')
    list_filter = ('visit_date', 'is_returning', 'first_path')
    readonly_fields = ('visitor_hash', 'visit_date', 'first_path', 'page_views', 'is_returning', 'first_seen', 'last_seen')

    @admin.display(description='Anonim ziyaretçi')
    def short_visitor(self, obj):
        return obj.visitor_hash[:12]


@admin.register(DailyTrafficMetric)
class DailyTrafficMetricAdmin(admin.ModelAdmin):
    list_display = ('date', 'page_views', 'filtered_bot_requests', 'updated_at')
    readonly_fields = ('date', 'page_views', 'filtered_bot_requests', 'updated_at')


@admin.register(DailyTrafficReport)
class DailyTrafficReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'sent_at')
    readonly_fields = ('report_date', 'sent_at')


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

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email','discount_percent','consent','is_active','created_at')
    list_filter = ('consent','is_active','created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at',)

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
