from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import ContactChangeNotice


class ContactNoticeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        match = request.resolver_match
        if not user.is_authenticated or not user.is_active or user.is_staff or user.is_superuser:
            return None
        if 'admin' in match.namespaces or request.path_info.startswith(('/api/', '/static/', '/media/', '/healthz/')):
            return None
        if getattr(request, 'urlconf', None) == 'mobile_web.urls':
            return None
        if match.view_name in {'contact_change_notice', 'logout', 'login', 'force_password_change_popup'}:
            return None
        if ContactChangeNotice.objects.filter(user=user, acknowledged_at__isnull=True).exists():
            return redirect('contact_change_notice')
        return None


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def contact_notice(request):
    pending = ContactChangeNotice.objects.filter(user=request.user, acknowledged_at__isnull=True)
    if not pending.exists():
        return redirect('dashboard_student')
    error = False
    if request.method == 'POST':
        if request.POST.get('understood') == 'yes':
            pending.update(acknowledged_at=timezone.now())
            return redirect('dashboard_student')
        error = True
    return render(request, 'contact-change-notice.html', {'notice_error': error}, status=400 if error else 200)
