from django.urls import path
from . import views
from .web_billing import PaymentLink
from .engagement import Activity, NotificationPlan
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    path("activity/", Activity.as_view()),
    path("notifications/plan/", NotificationPlan.as_view()),
    path("payments/link/", PaymentLink.as_view()),
    path("audio/<int:pk>/", views.AudioDownload.as_view()),
    path("questions/<int:pk>/image/", views.ImageDownload.as_view()),
    path("subscriptions/webhook/", views.BillingWebhook.as_view()),
    path("events/", views.Analytics.as_view()),
    path("auth/password-reset/", views.PasswordReset.as_view()),
    path(
        "auth/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="mobile_api/reset_form.html",
            success_url=reverse_lazy("mobile_reset_done"),
        ),
        name="mobile_reset_confirm",
    ),
    path(
        "auth/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="mobile_api/reset_done.html"
        ),
        name="mobile_reset_done",
    ),
    path("subscriptions/sync/", views.SubscriptionSync.as_view()),
    path("submissions/<int:pk>/audio/", views.VoiceDownload.as_view()),
    path("sessions/<uuid:pk>/voice/", views.Voice.as_view()),
    path("auth/change-password/", views.ChangePassword.as_view()),
    path("auth/register/", views.Register.as_view()),
    path("sessions/<uuid:pk>/continue/", views.ContinueCard.as_view()),
    path("auth/login/", views.Login.as_view()),
    path("auth/refresh/", views.Refresh.as_view()),
    path("auth/logout/", views.Logout.as_view()),
    path("profile/", views.Profile.as_view()),
    path("paths/", views.Paths.as_view()),
    path("paths/<int:pk>/restart/", views.RestartPath.as_view()),

    path("sessions/", views.Sessions.as_view()),
    path("sessions/<uuid:pk>/", views.SessionDetail.as_view()),
    path("sessions/<uuid:pk>/answer/", views.Answer.as_view()),
]
