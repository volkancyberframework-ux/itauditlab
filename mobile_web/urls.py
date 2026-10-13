from django.urls import path, include, re_path
from itaudit.health import readiness
from .views import app, web_asset, pwa_worker
from . import web_api

urlpatterns = [
    path("grc-pwa-sw.js", pwa_worker),
    path("web-api/auth/login/", web_api.Login.as_view()),
    path("web-api/auth/refresh/", web_api.Refresh.as_view()),
    path("web-api/auth/logout/", web_api.Logout.as_view()),
    path("web-api/paths/", web_api.Paths.as_view()),
    path("web-api/sessions/", web_api.Sessions.as_view()),
    path("web-api/sessions/<uuid:pk>/answer/", web_api.Answer.as_view()),
    path("web-api/questions/<int:pk>/image/", web_api.Image.as_view()),
    path("web-features/<path:path>", web_asset),
    path('api/mobile/v1/', include('mobile_api.urls')),
    path('healthz/', readiness),
    re_path(r'^(?P<path>.*)$', app),
]
