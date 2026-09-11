from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.generic import RedirectView
from itaudit.health import readiness

urlpatterns = [
    path(
        'media/__static__/img/course-covers/<str:filename>',
        RedirectView.as_view(
            url=f'{settings.STATIC_URL}img/course-covers/%(filename)s',
            permanent=True,
        ),
        name='static_course_cover',
    ),
    path('healthz/', readiness, name='healthz'),
    path('bulamazsinki/', admin.site.urls),
    path('', include('landing.urls')),
    path('', include('skool.urls')),
    path('', include('core.urls')),
]

# Static & Media
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Prod'da sadece MEDIA'yı Django üzerinden servis et (küçük projeler için)
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
