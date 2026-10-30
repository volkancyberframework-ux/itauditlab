from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from .models import Course
from .progress_guard import blockers, issue_confirmation, disable_after_confirmation, warning_enrollments


def guard_response(request, course):
    findings = blockers(request.user, course)
    if not findings:
        return None
    return render(request, 'program-progress-confirm.html', {
        'course': course, 'findings': findings,
        'confirmation_token': issue_confirmation(request.user, course, findings),
    })


@login_required
@require_POST
@never_cache
def acknowledge(request):
    if request.POST.get('acknowledged') != 'yes':
        return HttpResponseBadRequest('Uyarıyı okuduğunuzu onaylayın.')
    request.session['program_progress_ack'] = list(warning_enrollments(request.user).values_list('pk', flat=True))
    return redirect('dashboard_student')


@login_required
@require_POST
@never_cache
def confirm(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not request.user.can_enroll(course):
        return HttpResponseForbidden('Bu derse katılma yetkiniz yok.')
    if request.POST.get('continue_despite_warning') != 'yes':
        return HttpResponseBadRequest('İkinci uyarı açıkça onaylanmadı.')
    try:
        event = disable_after_confirmation(request.user, course, request.POST.get('confirmation_token', ''))
    except (signing.BadSignature, ValueError, TypeError):
        return HttpResponseBadRequest('Uyarı onayı geçersiz veya süresi dolmuş. Ders sayfasını tekrar açın.')
    if event is None:
        warning = guard_response(request, course)
        return warning if warning is not None else redirect('dashboard_student')
    logout(request)
    return render(request, 'program-progress-disabled.html', status=403)
