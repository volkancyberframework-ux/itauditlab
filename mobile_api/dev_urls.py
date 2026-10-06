from django.urls import include, path
from django.http import JsonResponse

urlpatterns = [
    path('api/mobile/v1/', include('mobile_api.urls')),
    path('healthz/', lambda request: JsonResponse({'status': 'ok', 'environment': 'device-demo'})),
]
