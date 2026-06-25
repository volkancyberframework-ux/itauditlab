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

from django.views.decorators.http import require_POST
import requests

from .models import (
    Course, Enrollment, CourseSection, CourseSubsection, CourseFAQ,
    CustomUser, TestQuestion, TestOption, NewsletterLead
)


from django.shortcuts import render

from .models import Bootcamp, PageVisit

def bootcamps_view(request):

    ip = (
        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]
        or request.META.get("REMOTE_ADDR")
    )

    PageVisit.objects.create(
        path=request.path,
        ip_address=ip,
        user=request.user if request.user.is_authenticated else None,
    )

    bootcamps = Bootcamp.objects.filter(is_active=True)

    return render(
        request,
        "bootcamps.html",
        {"bootcamps": bootcamps},
    )
def deneme(request):
    return render(request, "index_b2b_siberkobi.html")

def akademi(request):
    return render(request, "akademi.html")

@require_POST
def newsletter_lead_create(request):
    email = (request.POST.get("email") or "").strip().lower()

    if not email:
        return JsonResponse({"ok": False, "error": "Email zorunlu."}, status=400)

    lead, created = NewsletterLead.objects.get_or_create(email=email)

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    if bot_token and chat_id and created:
        text = f"Yeni Siberkobi test talebi:\nEmail: {email}"
        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data={"chat_id": chat_id, "text": text},
                timeout=5
            )
        except Exception as e:
            print("Telegram error:", e)

    return JsonResponse({
        "ok": True,
        "message": "support@siberkobi.co adresine ulaşın, testinizi ileteceğiz."
    })

User = get_user_model()





def about_view(request):
    return render(request, "about.html")


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
        # keep the Enrolled tab active after POST
        return redirect('/dashboard-student/#currentlyLearning')
    return redirect('dashboard_student')

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

    # ---- ACCESS CONTROL (deep-link protection) ----
    # Determine if test
    is_test = getattr(course, "is_test", None)
    if is_test is None:
        # supports both enum and plain string
        is_test = (
            getattr(course, "course_type", None) == getattr(Course, "CourseType", None).TEST
            if hasattr(Course, "CourseType") else
            getattr(course, "course_type", "") == "test"
        )

    if is_test:
        # tests: only for assigned users (unless staff)
        has_access = getattr(request.user, "has_course_access", None)
        allowed = bool(request.user.is_staff or request.user.is_superuser)
        if callable(has_access):
            allowed = allowed or has_access(course)
        if not allowed:
            messages.error(request, "You don’t have access to this test.")
            return redirect("dashboard_student")
    else:
        # videos: require enrollment (unless staff)
        if not (request.user.is_staff or request.user.is_superuser
                or Enrollment.objects.filter(user=request.user, course=course).exists()):
            messages.error(request, "Please enroll to access this course.")
            # send them to the list; you can keep the tab anchor if you like
            return redirect("dashboard_student")

    # ---- normal view rendering below (unchanged) ----
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

    # Flags for template
    can_access_test = True if not is_test else True  # passed above
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

    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        course = get_object_or_404(Course, pk=course_id, dashboard_activated=True)

        if not user.can_enroll(course):
            messages.error(request, "Enroll olamadınız. Uygun Katıl seviyesine yükseltin.")
            return redirect('/dashboard-student/#allCourses')

        Enrollment.objects.get_or_create(user=user, course=course)
        return redirect('/dashboard-student/#currentlyLearning')

    # Görünecek kurslar (dil + dashboard_activated)
    base_qs = Course.objects.filter(dashboard_activated=True)
    if user.is_turkish and not user.is_english:
        courses = base_qs.filter(is_turkish=True).distinct()
    elif user.is_english and not user.is_turkish:
        courses = base_qs.filter(is_english=True).distinct()
    elif user.is_english and user.is_turkish:
        courses = base_qs.filter(models.Q(is_english=True) | models.Q(is_turkish=True)).distinct()
    else:
        courses = Course.objects.none()

    # ID'ye göre sıralama (artan)
    courses = courses.order_by('id')

    # Enroll olan kurs ID'leri
    enrolled_course_ids = list(
        Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
    )

    # Enrolled sekmesi (görünürlük filtresi + ID sıralı)
    enrolled_courses = courses.filter(id__in=enrolled_course_ids).order_by('id').distinct()

    # İzinli enroll kontrolü için (template'te modal kararı)
    can_enroll_ids = [c.id for c in courses if user.can_enroll(c)]

    return render(request, 'dashboard-student.html', {
        'courses': courses,
        'enrolled_courses': enrolled_courses,
        'enrolled_course_ids': enrolled_course_ids,
        'can_enroll_ids': can_enroll_ids,
    })

import stripe

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Bootcamp


def bootcamps_view(request):
    bootcamps = Bootcamp.objects.filter(is_active=True)
    return render(request, "bootcamps.html", {"bootcamps": bootcamps})


@require_POST
def bootcamp_checkout(request, slug):
    bootcamp = get_object_or_404(Bootcamp, slug=slug, is_active=True)

    email = ""
    username = "Misafir"

    if request.user.is_authenticated:
        email = request.user.email or ""
        username = request.user.get_full_name() or request.user.username or request.user.email
    else:
        email = request.POST.get("email", "").strip().lower()

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    if bot_token and chat_id and request.user.is_authenticated:
        text = (
            "🚀 Bootcamp Katıl Butonuna Basıldı\n\n"
            f"Bootcamp: {bootcamp.title}\n"
            f"Kullanıcı: {username}\n"
            f"Email: {email}\n"
            f"Fiyat: {bootcamp.price} {bootcamp.currency}"
        )

        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data={"chat_id": chat_id, "text": text},
                timeout=5
            )
        except Exception as e:
            print("Telegram error:", e)

    if not settings.STRIPE_SECRET_KEY:
        return HttpResponseBadRequest("Stripe ayarı eksik.")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        customer_email=email or None,
        line_items=[
            {
                "price_data": {
                    "currency": bootcamp.currency.lower(),
                    "product_data": {
                        "name": bootcamp.title,
                        "description": bootcamp.description[:400],
                    },
                    "unit_amount": int(bootcamp.price * 100),
                },
                "quantity": 1,
            }
        ],
        success_url=request.build_absolute_uri(reverse("bootcamp_payment_success")),
        cancel_url=request.build_absolute_uri(reverse("bootcamps")),
    )

    return redirect(session.url)

def bootcamp_payment_success(request):
    return render(request, "bootcamp-success.html")

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
import stripe


def create_membership_checkout(request, plan):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    plans = {
        "monthly": {
            "name": "Siberkobi Aylık Üyelik",
            "amount": 9999,
            "interval": "month",
        },
        "yearly": {
            "name": "Siberkobi Yıllık Üyelik",
            "amount": 69999,
            "interval": "year",
        },
    }

    selected_plan = plans.get(plan)

    if not selected_plan:
        messages.error(request, "Geçersiz üyelik paketi.")
        return redirect("landing")

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=(
                request.user.email
                if request.user.is_authenticated and request.user.email
                else None
            ),
            line_items=[
                {
                    "price_data": {
                        "currency": "try",
                        "unit_amount": selected_plan["amount"] * 100,
                        "product_data": {
                            "name": selected_plan["name"],
                        },
                        "recurring": {
                            "interval": selected_plan["interval"],
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=request.build_absolute_uri("/login/?payment=success"),
            cancel_url=request.build_absolute_uri("/?payment=cancel"),
        )

        return redirect(checkout_session.url)

    except Exception as e:
        messages.error(request, f"Ödeme başlatılamadı: {e}")
        return redirect("landing")
