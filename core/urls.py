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
from . import views_store


urlpatterns = [
    path('', landing_page, name='landing'),
    path('course-single/<int:pk>/', views.course_single, name='course_single'),
    path("course/<int:pk>/random-question/", views.course_random_question, name="course_random_question"),
    path('login/', views.custom_login_view, name='login'),
    path('force-password-change/', views.force_password_change_popup, name='force_password_change_popup'),
    path('dashboard-student/', dashboard_student, name='dashboard_student'),
    path('logout/', logout_view, name='logout'),
    path('unenroll/', views.unenroll_course, name='unenroll_course'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('coming-soon/', views.coming_soon_view, name='coming-soon'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path("for-individuals/", views.for_individuals, name="for_individuals"),
    path("for-businesses/", views.for_businesses, name="for_businesses"),
    path("about/", views.about_view, name="about"),

    path("store/", views_store.product_list_view, name="product_list"),
    path("store/<slug:slug>/detail.json", views_store.product_detail_json, name="product_detail_json"),
    path("store/<slug:slug>/intent/", views_store.create_purchase_intent, name="create_purchase_intent"),
    path("store/success/<uuid:token>/", views_store.purchase_success, name="purchase_success"),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
