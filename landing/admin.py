from django.contrib import admin
from .models import (
    AssessmentSession, Certificate, CorporateInquiry, DailyTrafficMetric, DailyTrafficReport,
    JobMarketCount, LandingVisit, Lead, NewsletterSubscriber, PartnerApplication,
    SiteSetting, WaitingList, TravelRegistration, TravelPayment,
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


class TravelPaymentInline(admin.TabularInline):
    model = TravelPayment
    extra = 0
    can_delete = False
    readonly_fields = tuple(field.name for field in TravelPayment._meta.fields)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TravelRegistration)
class TravelRegistrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'starts_on', 'payment_status', 'registered_at', 'telegram_sent_at')
    search_fields = ('name', 'email', 'payments__checkout_session_id', 'payments__payment_intent_id')
    list_filter = ('starts_on', 'payment_status')
    readonly_fields = tuple(field.name for field in TravelRegistration._meta.fields)
    inlines = [TravelPaymentInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from .models import MobileWaitlist

@admin.register(MobileWaitlist)
class MobileWaitlistAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

from .models import LegalRegulation, LegalRevision
from django.forms.models import model_to_dict

class LegalRevisionInline(admin.TabularInline):
    model = LegalRevision
    extra = 0
    can_delete = False
    readonly_fields = ('created_at','actor','snapshot')
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(LegalRegulation)
class LegalRegulationAdmin(admin.ModelAdmin):
    list_display = ('short_name','country_code','category','status','review_state','published','last_verified_at','link_status')
    list_filter = ('country_code','category','status','review_state','published','last_verified_at')
    search_fields = ('official_name','short_name','regulatory_authority','source_notes')
    readonly_fields = ('source_hash','checked_at','link_status','updated_at')
    inlines = (LegalRevisionInline,)
    actions = ('reset_source_baseline',)
    @admin.action(description='Kaynak karşılaştırma bazını sıfırla (hukuki yayın onayı vermez)')
    def reset_source_baseline(self,request,queryset):
        for obj in queryset:
            obj.source_hash=''
            obj.save(update_fields=['source_hash'])
            LegalRevision.objects.create(regulation=obj,actor=request.user.get_username(),snapshot={'action':'reset_source_baseline'})
            self.log_change(request,obj,'Source comparison baseline cleared; publication unchanged.')
        self.message_user(request,'Kaynak karşılaştırma bazı sıfırlandı. Yayın ve doğrulama tarihi değiştirilmedi.')
    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)
        snapshot = model_to_dict(obj)
        for key in ('publication_date','effective_date','last_verified_at'):
            if snapshot.get(key): snapshot[key] = str(snapshot[key])
        LegalRevision.objects.create(regulation=obj,actor=request.user.get_username(),snapshot=snapshot)
    def has_delete_permission(self, request, obj=None):
        return False
