from django.urls import path, include, re_path
from itaudit.health import readiness
from .views import app

urlpatterns = [
    path('api/mobile/v1/', include('mobile_api.urls')),
    path('healthz/', readiness),
    re_path(r'^(?P<path>.*)$', app),
]
