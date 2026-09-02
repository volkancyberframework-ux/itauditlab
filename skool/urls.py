from django.urls import path

from . import views

app_name = "skool"

urlpatterns = [
    path("skooltoplulugu", views.onboarding, name="onboarding"),
    path("skooltoplulugu/", views.onboarding),
    path("skooltoplulugu/yolculuk/", views.journey, name="journey"),
    path("skooltoplulugu/cikis/", views.skool_logout, name="logout"),
    path("calismalar", views.labs, name="labs"),
    path("calismalar/", views.labs),
    path("calismalar/<int:pk>/pdf/", views.lab_pdf, name="lab_pdf"),
    path("calismalar/<int:pk>/tamamla/", views.complete_lab, name="complete_lab"),
    path("skooltoplulugu/api/basla/", views.mark_intro, name="mark_intro"),
    path("skooltoplulugu/api/cevap/", views.save_answer, name="save_answer"),
    path("skooltoplulugu/api/ses-ilerleme/", views.audio_progress, name="audio_progress"),
    path("skooltoplulugu/api/ses-tamamla/", views.complete_audio, name="complete_audio"),
    path("skooltoplulugu/api/ses-atla/", views.skip_audio, name="skip_audio"),
    path("skooltoplulugu/api/saatler/", views.slots, name="slots"),
    path("skooltoplulugu/api/rezervasyon/", views.book, name="book"),
    path("skooltoplulugu/api/degistir/", views.reschedule, name="reschedule"),
    path("admin/skool/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/skool/availability/", views.admin_availability, name="admin_availability"),
    path("admin/skool/bookings/", views.admin_bookings, name="admin_bookings"),
    path("admin/skool/users/<int:pk>/", views.admin_user, name="admin_user"),
    path("api/skool/telegram/", views.telegram_webhook, name="telegram_webhook"),
]
