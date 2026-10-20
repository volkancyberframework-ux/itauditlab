from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from .models import (MonitoringSettings, LessonEvidence, StudentIntervention,
    MonitoringAudit, DailyMonitoringSnapshot)
from . import monitoring_views as views


@admin.register(MonitoringSettings)
class MonitoringDashboardAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def changelist_view(self, request, extra_context=None):
        return redirect('admin:core_student_monitoring')
    def get_urls(self):
        routes = [
            ('panel/', views.dashboard, 'core_student_monitoring'),
            ('settings/', views.save_settings, 'core_monitoring_settings'),
            ('refresh/', views.refresh, 'core_monitoring_refresh'),
            ('student/<int:student_id>/', views.student_detail, 'core_monitoring_student'),
            ('student/<int:student_id>/draft/', views.draft, 'core_monitoring_draft'),
            ('student/<int:student_id>/evidence/', views.save_evidence, 'core_monitoring_evidence'),
            ('enrollment/<int:enrollment_id>/', views.enrollment_policy, 'core_monitoring_policy'),
            ('intervention/<int:intervention_id>/', views.intervention, 'core_monitoring_intervention'),
            ('intervention/<int:intervention_id>/action/', views.intervention_action, 'core_monitoring_intervention_action'),
        ]
        return [path(url, self.admin_site.admin_view(view), name=name) for url, view, name in routes] + super().get_urls()


class MonitoringReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(StudentIntervention)
class InterventionHistoryAdmin(MonitoringReadOnlyAdmin):
    list_display = ['student', 'status', 'created_at', 'marked_sent_at', 'marked_sent_by']
    list_filter = ['status', 'created_at']
    search_fields = ['student__email', 'student__first_name', 'student__last_name']


@admin.register(MonitoringAudit)
class MonitoringAuditAdmin(MonitoringReadOnlyAdmin):
    list_display = ['created_at', 'actor_email', 'action', 'student']
    list_filter = ['action', 'created_at']
    search_fields = ['student__email', 'actor_email', 'reason']


@admin.register(DailyMonitoringSnapshot)
class DailySnapshotAdmin(MonitoringReadOnlyAdmin):
    list_display = ['reporting_date', 'captured_at']


@admin.register(LessonEvidence)
class LessonEvidenceAdmin(MonitoringReadOnlyAdmin):
    list_display = ['user', 'course', 'completion_known', 'completed_at', 'last_accessed_at', 'verified_by']
    search_fields = ['user__email', 'course__turkish_name']
