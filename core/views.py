from __future__ import annotations
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db import models
from django.db.models import Prefetch, IntegerField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Course, Enrollment,CourseSection,CourseSubsection,CourseFAQ,CustomUser,TestQuestion,TestOption
from .utils.bunny import generate_bunny_token
from core.models import CourseSubsection
from django.db.models import Prefetch, IntegerField
from django.db.models.functions import Coalesce
from django.shortcuts import render, get_object_or_404
from django.db.models import Prefetch, IntegerField
from django.db.models.functions import Coalesce
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.contrib.auth.decorators import login_required
import logging
import random
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden



User = get_user_model()

def custom_login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            if user.is_first_login:
                return render(request, 'login.html', {
                    'show_password_change_popup': True
                })
            return redirect('dashboard_student')
        else:
            return render(request, 'login.html', {
                'error': 'Invalid credentials'
            })
    return render(request, 'login.html')


@csrf_exempt
def force_password_change_popup(request):
    if request.method == 'POST':
        pw1 = request.POST.get('new_password')
        pw2 = request.POST.get('confirm_password')
        if pw1 != pw2:
            return render(request, 'login.html', {
                'error': "Passwords do not match",
                'show_password_change_popup': True
            })

        user = request.user
        user.password = make_password(pw1)
        user.is_first_login = False
        user.save()
        return redirect('dashboard_student')

@login_required
def unenroll_course(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        Enrollment.objects.filter(user=request.user, course_id=course_id).delete()
    return redirect('dashboard_student')  # or the view where the user is listed

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')  # or any landing page


def landing_page(request):
    courses = Course.objects.filter(main_page_activated=True)
    return render(request, 'index.html', {'courses': courses})

def terms_and_conditions(request):
    """
    Render the Terms & Conditions page for ITAuditLab.
    Uses the shared _terms_body.html partial so the content matches the modal.
    """
    return render(request, "terms_page.html")

def pricing_view(request):
    return render(request, 'pricing.html')

def coming_soon_view(request):
    return render(request, 'coming-soon.html')

def for_individuals(request):
    return render(request, "for-individuals.html")

def for_businesses(request):
    return render(request, "for-businesses.html")

logger = logging.getLogger(__name__)

def _bunny_url_passthrough(val: str | None) -> str | None:
    if not val:
        return None
    s = val.strip()
    # Doğrudan URL (play veya embed) veriyorsun → aynen kullan
    if s.startswith(("http://", "https://")):
        return s
    # İstersen raw id gelirse embed'e çevir:
    lib = getattr(settings, "BUNNY_LIBRARY_ID", "").strip()
    base = getattr(settings, "BUNNY_IFRAME_BASE", "https://iframe.mediadelivery.net/embed").rstrip("/")
    return f"{base}/{lib}/{s}" if lib else None

@login_required
@never_cache
def course_single(request, pk):
    course = get_object_or_404(Course, pk=pk)

    sections_qs = course.sections.annotate(
        sort_key=Coalesce('order', 'id', output_field=IntegerField())
    ).order_by('sort_key', 'id')

    subsections_prefetch = Prefetch(
        'subsections',
        queryset=CourseSubsection.objects.annotate(
            sort_key=Coalesce('order', 'id', output_field=IntegerField())
        ).order_by('sort_key', 'id')
    )

    sections = sections_qs.prefetch_related(subsections_prefetch)
    faqs = course.faqs.all()

    first_video_url = None
    for sec in sections:
        for sub in sec.subsections.all():
            raw = getattr(sub, "bunny_video_id", None)
            sub.bunny_iframe_url = _bunny_url_passthrough(raw)
            if not first_video_url and sub.bunny_iframe_url:
                first_video_url = sub.bunny_iframe_url

    # NEW: flags for template to avoid calling methods in templates
    is_test = getattr(course, "is_test", None)
    if is_test is None:
        is_test = (course.course_type == Course.CourseType.TEST)

    can_access_test = True
    if is_test:
        # deny if user not allowed
        can_access_test = request.user.has_course_access(course)

    return render(request, "course-single.html", {
        "course": course,
        "sections": sections,
        "faqs": faqs,
        "first_video_url": first_video_url or "",
        "is_test": is_test,
        "can_access_test": can_access_test,
    })


@login_required
def course_random_question(request, pk):
    course = get_object_or_404(Course, pk=pk)

    # Is this a test course?
    is_test_course = False
    if hasattr(Course, "CourseType"):
      is_test_course = (course.course_type == Course.CourseType.TEST)
    else:
      is_test_course = (getattr(course, "course_type", None) == "test")
    if not is_test_course:
        return HttpResponseBadRequest("Not a test course.")

    # Permission: only allowed users (if method exists)
    has_access = getattr(request.user, "has_course_access", None)
    if callable(has_access) and not has_access(course):
        return HttpResponseForbidden("No access to this test.")

    qs = TestQuestion.objects.filter(course=course, is_active=True).prefetch_related("options")
    if not qs.exists():
        return JsonResponse({"ok": True, "question": None})

    # random pick
    ids = list(qs.values_list("id", flat=True))
    q = qs.get(id=random.choice(ids))

    data = {
        "ok": True,
        "question": {
            "id": q.id,
            "text": q.text,
            "type": q.question_type,  # "single" | "multiple"
            "explanation": q.explanation or "",
            "options": [{"id": o.id, "text": o.text} for o in q.options.all()],
            "correct_option_ids": list(q.options.filter(is_correct=True).values_list("id", flat=True)),
        },
    }
    return JsonResponse(data)

@login_required
def dashboard_student(request):
    user = request.user

    # Enroll işlemi (erişim kuralını da uygula)
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        course = get_object_or_404(Course, pk=course_id, dashboard_activated=True)

        # Test erişim kuralı: video herkese açık, testler sadece izinli
        if hasattr(user, "has_course_access") and not user.has_course_access(course):
            messages.error(request, "Bu teste erişiminiz yok.")
            return redirect('/dashboard-student/#currentlyLearning')

        Enrollment.objects.get_or_create(user=user, course=course)
        return redirect('/dashboard-student/#currentlyLearning')

    # ---- Görünür kurslar (dashboard_activated + dil + erişim kuralı) ----
    base_qs = Course.objects.filter(dashboard_activated=True)

    # Dil filtresi
    if user.is_turkish and not user.is_english:
        base_qs = base_qs.filter(is_turkish=True)
    elif user.is_english and not user.is_turkish:
        base_qs = base_qs.filter(is_english=True)
    elif user.is_english and user.is_turkish:
        base_qs = base_qs.filter(models.Q(is_english=True) | models.Q(is_turkish=True))
    else:
        base_qs = Course.objects.none()

    # Erişim kuralı (video: herkes, test: sadece allowed_tests)
    allowed_test_ids = user.allowed_tests.values_list('id', flat=True) if hasattr(user, "allowed_tests") else []
    courses = base_qs.filter(
        models.Q(course_type=Course.CourseType.VIDEO) |
        models.Q(id__in=allowed_test_ids)
    ).distinct()

    # ---- Enrolled sekmesi için: sadece kayıtlı + görünür kurslar ----
    enrolled_courses = courses.filter(enrollment__user=user).distinct()

    # Şablonda hızlı kontrol için ID seti
    enrolled_course_ids = set(enrolled_courses.values_list('id', flat=True))

    return render(request, 'dashboard-student.html', {
        'courses': courses,                         # Tüm görünür kurslar
        'enrolled_courses': enrolled_courses,       # Sadece kayıt olunan görünür kurslar
        'enrolled_course_ids': enrolled_course_ids  # Üyelik kontrolü için
    })
