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

from .models import Course, Enrollment
from .utils.bunny import generate_bunny_token



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


def pricing_view(request):
    return render(request, 'pricing.html')

def coming_soon_view(request):
    return render(request, 'coming-soon.html')

@login_required
def course_single(request, pk):
    course = get_object_or_404(Course, pk=pk)

    # Sections ordered by 'order' then 'id'
    sections_qs = course.sections.annotate(
        sort_key=Coalesce('order', 'id')
    ).order_by('sort_key', 'id')

    # Preorder subsections the same way
    from core.models import Subsection  # adjust import if needed
    subsections_prefetch = Prefetch(
        'subsections',
        queryset=Subsection.objects.annotate(
            sort_key=Coalesce('order', 'id')
        ).order_by('sort_key', 'id')
    )

    sections = sections_qs.prefetch_related(subsections_prefetch)
    faqs = course.faqs.all()

    first_video_url = None
    first_section = sections.first()
    if first_section:
        first_sub = first_section.subsections.all().first()  # already pre-ordered
        if first_sub and first_sub.bunny_video_id:
            raw = first_sub.bunny_video_id.strip()
            first_video_url = raw if raw.startswith(("http://","https://")) \
                else f"{settings.BUNNY_STREAM_BASE}/{raw}/playlist.m3u8"

    return render(request, "course-single.html", {
        "course": course,
        "sections": sections,
        "faqs": faqs,
        "first_video_url": first_video_url,
    })


@login_required
def dashboard_student(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        course = get_object_or_404(Course, pk=course_id)
        Enrollment.objects.get_or_create(user=request.user, course=course)
        return redirect('/dashboard-student/#currentlyLearning')  # go directly to the Enrolled tab

    # Base queryset: only dashboard_activated courses
    courses = Course.objects.filter(dashboard_activated=True)

    # Filter by language
    if request.user.is_turkish and not request.user.is_english:
        courses = courses.filter(is_turkish=True)
    elif request.user.is_english and not request.user.is_turkish:
        courses = courses.filter(is_english=True)
    elif request.user.is_english and request.user.is_turkish:
        courses = courses.filter(models.Q(is_english=True) | models.Q(is_turkish=True))
    else:
        courses = Course.objects.none()  # no matching courses

    enrolled_courses = courses.filter(enrollment__user=request.user)

    return render(request, 'dashboard-student.html', {
        'courses': courses,
        'enrolled_courses': enrolled_courses
    })
