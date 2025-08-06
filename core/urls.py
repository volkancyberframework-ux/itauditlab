from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views
from .views import (
    landing_page,
    course_single,
    login,
    dashboard_student,
    logout_view,
    force_password_change_popup,
    pricing_view,
    coming_soon_view
)

urlpatterns = [
    path('', landing_page, name='landing'),
    path('course-single/<int:pk>/', views.course_single, name='course_single'),
    path('login/', views.custom_login_view, name='login'),
    path('force-password-change/', views.force_password_change_popup, name='force_password_change_popup'),
    path('dashboard-student/', dashboard_student, name='dashboard_student'),
    path('logout/', logout_view, name='logout'),
    path('unenroll/', views.unenroll_course, name='unenroll_course'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('coming-soon/', views.coming_soon_view, name='coming-soon'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
