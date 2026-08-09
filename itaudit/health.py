from django.db import connections
from django.http import HttpResponse


def readiness(request):
    """Report ready only when Django can reach its primary database."""
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return HttpResponse("not ready", status=503, content_type="text/plain")

    return HttpResponse("ok", content_type="text/plain")
