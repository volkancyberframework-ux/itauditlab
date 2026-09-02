from urllib.parse import quote
import csv
import io
from datetime import datetime, timedelta

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import (
    CustomUser,
    Course,
    CourseSection,
    CourseSubsection,
    CourseFAQ,
    TestQuestion,
    TestOption,
    Enrollment,
    DigitalProduct,
    PurchaseIntent,
    NewsletterLead,
    LearningProgram,
    LearningProgramStep,
    ProgramEnrollment,
    ProgramRelease,
    MentorshipRequest,
    StudentMeetingBooking,
)


@admin.register(MentorshipRequest)
class MentorshipRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "request_type", "status", "created_at")
    list_filter = ("request_type", "status", "created_at")
    search_fields = ("user__username", "user__email", "course__turkish_name", "reason")
    readonly_fields = ("user", "course", "request_type", "reason", "created_at", "updated_at")


@admin.register(StudentMeetingBooking)
class StudentMeetingBookingAdmin(admin.ModelAdmin):
    list_display = ("user", "request", "slot", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "request__reason")
    readonly_fields = ("user", "request", "slot", "meeting_url", "created_at", "updated_at")

DEFAULT_PASSWORD = "GRCUstasi1234"


def format_program_calendar(steps, start_date):
    """Program adımlarını e-posta taslağı için gerçek tarihlere dönüştürür."""
    lines = []
    for step in steps:
        if isinstance(step, dict):
            day_offset = step["day_offset"]
            title = step["email_title"] or step["course__turkish_name"] or step["course__english_name"]
        else:
            day_offset = step.day_offset
            title = step.email_title or step.course.turkish_name or step.course.english_name
        release_date = start_date + timedelta(days=day_offset)
        lines.append(f"📅 {release_date:%d.%m.%Y} — {title}")
    return "\n".join(lines)


def build_program_calendar_email(enrollment):
    """Program Enrollment için gönderime hazır, markalı takvim taslağı üretir."""
    program = enrollment.program
    calendar = format_program_calendar(
        program.steps.order_by("day_offset", "order", "id").values(
            "day_offset", "email_title", "course__turkish_name", "course__english_name"
        ),
        enrollment.start_date,
    )
    subject = f"🗓️ {program.name} Eğitim Takvimi"
    body = f"""Merhaba,

GRC Ustası eğitim programınıza kaydınız tamamlandı.

━━━━━━━━━━━━━━━━━━━━
🗓️ {program.name}
━━━━━━━━━━━━━━━━━━━━

Program başlangıç tarihi: {enrollment.start_date:%d.%m.%Y}

{calendar or "Program adımları yönetim panelinden eklenecektir."}

İçerikleriniz bu kişisel takvime göre otomatik olarak erişime açılacaktır.

🌐 Eğitim paneli: https://www.grcustasi.com/dashboard-student/
👤 Kullanıcı hesabı: {enrollment.user.email}

Sorularınız için volkan@grcustasi.com adresinden ulaşabilirsiniz.

İyi çalışmalar,
Volkan Güler
GRC Ustası
"""
    mailto_url = (
        f"mailto:{quote(enrollment.user.email)}"
        f"?subject={quote(subject)}"
        f"&body={quote(body)}"
    )
    return subject, body, mailto_url


from django.contrib import admin
from .models import Bootcamp

from .models import PageVisit, BootcampInterest

import requests

@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user_display",
        "ip_with_country",
        "path",
        "time_spent",
    )

    search_fields = (
        "path",
        "ip_address",
        "user__email",
        "user__username",
    )

    list_filter = (
        "path",
        "created_at",
    )

    def user_display(self, obj):
        return obj.user.email if obj.user else "-"
    user_display.short_description = "User"

    def time_spent(self, obj):
        seconds = obj.duration_seconds or 0

        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours}s {minutes}dk"

        if minutes:
            return f"{minutes}dk {seconds}sn"

        return f"{seconds}sn"

    time_spent.short_description = "Time on Page"

    def ip_with_country(self, obj):
        if not obj.ip_address:
            return "-"

        try:
            r = requests.get(
                f"http://ip-api.com/json/{obj.ip_address}?fields=country",
                timeout=2,
            )

            country = r.json().get("country")

            if country:
                return f"{obj.ip_address} ({country})"

        except Exception:
            pass

        return obj.ip_address

    ip_with_country.short_description = "IP Address"
@admin.register(BootcampInterest)
class BootcampInterestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "bootcamp_display", "user_display", "email", "ip_address")
    search_fields = ("bootcamp__title", "email", "ip_address", "user__email", "user__username")
    list_filter = ("created_at",)

    def bootcamp_display(self, obj):
        return obj.bootcamp.title if obj.bootcamp else "-"
    bootcamp_display.short_description = "Bootcamp"

    def user_display(self, obj):
        return obj.user.email if obj.user else "-"
    user_display.short_description = "User"

@admin.register(Bootcamp)
class BootcampAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "currency", "duration", "level", "is_active", "order", "created_at")
    list_filter = ("is_active", "currency", "created_at")
    search_fields = ("title", "description", "level")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("order", "-created_at")


@admin.register(NewsletterLead)
class NewsletterLeadAdmin(admin.ModelAdmin):
    pass


@admin.register(DigitalProduct)
class DigitalProductAdmin(admin.ModelAdmin):
    list_display = (
        "title", "price", "original_price", "currency",
        "difficulty", "rating", "reviews_count", "is_active"
    )
    list_filter = ("is_active", "currency", "difficulty")
    search_fields = ("title", "description", "uploader_name", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(PurchaseIntent)
class PurchaseIntentAdmin(admin.ModelAdmin):
    list_display = ("email", "product", "created_at", "is_paid", "token")
    list_filter = ("is_paid", "created_at", "product")
    search_fields = ("email", "product__title", "token")


class TestOptionInline(admin.TabularInline):
    model = TestOption
    extra = 2


@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "question_type", "is_active", "text")
    list_filter = ("course", "question_type", "is_active")
    search_fields = ("text",)
    inlines = [TestOptionInline]


class CourseAdminForm(forms.ModelForm):
    upload_pdf = forms.FileField(
        required=False,
        help_text="Upload/replace course attachment"
    )

    class Meta:
        model = Course
        fields = "__all__"

    def save(self, commit=True):
        instance = super().save(commit=False)
        pdf_file = self.cleaned_data.get("upload_pdf")

        if pdf_file:
            if instance.pk and getattr(instance, "attachment", None):
                instance.attachment.delete(save=False)
            instance.attachment.save(pdf_file.name, pdf_file, save=False)

        if commit:
            instance.save()

        return instance


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = (
        "id", "display_course", "course_type",
        "difficulty", "duration", "score"
    )
    search_fields = ("id", "description", "turkish_name", "english_name")
    list_filter = (
        "course_type", "difficulty", "dashboard_activated",
        "main_page_activated", "is_english", "is_turkish"
    )

    def display_course(self, obj):
        return obj.turkish_name or obj.english_name or str(obj)

    display_course.short_description = "Course"


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "big_title", "order")
    list_editable = ("order",)
    ordering = ("order", "id")
    search_fields = ("big_title",)
    list_filter = ("course",)


@admin.register(CourseSubsection)
class CourseSubsectionAdmin(admin.ModelAdmin):
    list_display = ("id", "section", "small_title", "order")
    list_editable = ("order",)
    ordering = ("order", "id")
    search_fields = ("small_title",)
    list_filter = ("section__course", "section")


@admin.register(CourseFAQ)
class CourseFAQAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "question")
    search_fields = (
        "question", "answer",
        "course__turkish_name", "course__english_name"
    )
    list_filter = ("course",)


class LearningProgramStepInline(admin.TabularInline):
    model = LearningProgramStep
    extra = 0
    autocomplete_fields = ("course",)
    ordering = ("day_offset", "order")


@admin.register(LearningProgram)
class LearningProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "student_count", "step_count")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    inlines = (LearningProgramStepInline,)

    @admin.display(description="Öğrenci")
    def student_count(self, obj):
        return obj.enrollments.count()

    @admin.display(description="Adım")
    def step_count(self, obj):
        return obj.steps.count()


class ProgramEnrollmentAdminForm(forms.ModelForm):
    prepare_calendar_email = forms.BooleanField(
        required=False,
        initial=False,
        label="Kaydettikten sonra takvim e-posta taslağını hazırla",
        help_text=(
            "Öğrencinin başlangıç tarihi ve program adımlarından gönderime hazır "
            "bir e-posta oluşturur; e-posta otomatik gönderilmez."
        ),
    )

    class Meta:
        model = ProgramEnrollment
        fields = "__all__"


@admin.register(ProgramEnrollment)
class ProgramEnrollmentAdmin(admin.ModelAdmin):
    form = ProgramEnrollmentAdminForm
    list_display = ("user", "program", "start_date", "is_active", "welcome_sent_at", "progress")
    list_filter = ("program", "is_active", "start_date")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("user", "program")
    list_editable = ("is_active",)
    date_hierarchy = "start_date"
    change_list_template = "admin/program_enrollment_changelist.html"

    def get_urls(self):
        return [
            path(
                "<int:object_id>/calendar-email/",
                self.admin_site.admin_view(self.calendar_email),
                name="core_programenrollment_calendar_email",
            ),
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv),
                name="core_programenrollment_import_csv",
            )
        ] + super().get_urls()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.cleaned_data.get("prepare_calendar_email"):
            request._program_calendar_email_id = obj.pk

    def response_add(self, request, obj, post_url_continue=None):
        if getattr(request, "_program_calendar_email_id", None):
            return redirect(
                reverse("admin:core_programenrollment_calendar_email", args=[obj.pk])
            )
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if getattr(request, "_program_calendar_email_id", None):
            return redirect(
                reverse("admin:core_programenrollment_calendar_email", args=[obj.pk])
            )
        return super().response_change(request, obj)

    def calendar_email(self, request, object_id):
        enrollment = get_object_or_404(
            ProgramEnrollment.objects.select_related("user", "program"),
            pk=object_id,
        )
        subject, body, mailto_url = build_program_calendar_email(enrollment)
        return render(
            request,
            "admin/program_enrollment_calendar_email.html",
            {
                "email": enrollment.user.email,
                "subject": subject,
                "body": body,
                "mailto_url": mailto_url,
                "program_enrollment": enrollment,
            },
        )

    def import_csv(self, request):
        if request.method == "POST" and request.FILES.get("csv_file"):
            stream = io.StringIO(request.FILES["csv_file"].read().decode("utf-8-sig"))
            bootstrap_history = request.POST.get("bootstrap_history") == "on"
            imported = 0
            errors = []
            for row_number, row in enumerate(csv.DictReader(stream), start=2):
                email = row.get("email", "").strip().lower()
                try:
                    user = CustomUser.objects.get(email__iexact=email)
                    program = LearningProgram.objects.get(
                        slug=row.get("program", "normal").strip().lower()
                    )
                    start_date = datetime.strptime(
                        row.get("start_date", "").strip(), "%Y-%m-%d"
                    ).date()
                    enrollment, _ = ProgramEnrollment.objects.update_or_create(
                        user=user,
                        program=program,
                        defaults={"start_date": start_date, "is_active": True},
                    )
                    if bootstrap_history:
                        now = timezone.now()
                        elapsed_days = (timezone.localdate() - start_date).days
                        for step in program.steps.filter(day_offset__lte=elapsed_days).select_related("course"):
                            if step.course.course_type == Course.CourseType.TEST:
                                user.allowed_tests.add(step.course)
                            ProgramRelease.objects.update_or_create(
                                enrollment=enrollment,
                                step=step,
                                defaults={
                                    "status": ProgramRelease.Status.SENT,
                                    "access_granted_at": now,
                                    "email_sent_at": now,
                                    "error_message": "Geçmiş akış CSV geçişinde işlendi.",
                                },
                            )
                        if not enrollment.welcome_sent_at:
                            enrollment.welcome_sent_at = now
                            enrollment.save(update_fields=("welcome_sent_at",))
                    imported += 1
                except Exception as exc:
                    errors.append(f"Satır {row_number} ({email or '-'}): {exc}")
            if imported:
                messages.success(request, f"{imported} öğrenci programlara aktarıldı.")
            for error in errors[:10]:
                messages.error(request, error)
            return redirect(reverse("admin:core_programenrollment_changelist"))
        return render(request, "admin/program_enrollment_import.html")

    @admin.display(description="İlerleme")
    def progress(self, obj):
        total = obj.program.steps.count()
        sent = obj.releases.filter(status=ProgramRelease.Status.SENT).count()
        return f"{sent}/{total}"


@admin.register(ProgramRelease)
class ProgramReleaseAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "step", "status", "access_granted_at", "email_sent_at")
    list_filter = ("status", "enrollment__program")
    search_fields = ("enrollment__user__email", "step__course__turkish_name")
    readonly_fields = ("enrollment", "step", "status", "access_granted_at", "email_sent_at", "error_message", "created_at")

    def has_add_permission(self, request):
        return False


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    autocomplete_fields = ("course",)
    verbose_name = "Enrollment"
    verbose_name_plural = "Enrollments"


class QuickStudentCreateForm(forms.Form):
    email = forms.EmailField(label="Öğrenci e-posta adresi")

    program = forms.ModelChoiceField(
        queryset=LearningProgram.objects.filter(is_active=True).order_by("name"),
        required=False,
        label="Öğrenciyi bir programa kaydet",
        help_text="Program seçerseniz öğrenci için Program Enrollment kaydı ve kişisel eğitim takvimi oluşturulur.",
    )

    program_start_date = forms.DateField(
        required=False,
        label="Program başlangıç tarihi",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Takvimdeki bütün içerik tarihleri bu güne göre hesaplanır.",
    )

    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all().order_by("id"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Tanımlanacak içerikler",
    )

    has_meeting = forms.BooleanField(
        required=False,
        label="Meeting var mı?",
    )

    meeting_link = forms.URLField(
        required=False,
        label="Meeting linki",
        initial="https://meet.google.com/vza-zmpe-fjf",
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("program") and not cleaned.get("program_start_date"):
            self.add_error("program_start_date", "Bir program seçtiğinizde başlangıç tarihi zorunludur.")
        if cleaned.get("program_start_date") and not cleaned.get("program"):
            self.add_error("program", "Başlangıç tarihi için bir program seçin.")
        return cleaned


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username", "email", "is_active", "is_staff",
        "is_first_login", "is_english", "is_turkish"
    )
    list_filter = UserAdmin.list_filter + (
        "is_first_login", "is_english", "is_turkish"
    )
    search_fields = UserAdmin.search_fields + ("email",)
    filter_horizontal = ("allowed_tests",)
    inlines = [EnrollmentInline]

    change_list_template = "admin/customuser_changelist.html"

    fieldsets = UserAdmin.fieldsets + (
        (_("Profile flags"), {
            "fields": ("is_first_login", "is_english", "is_turkish")
        }),
        (_("Test access"), {
            "fields": ("allowed_tests",)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (_("Profile flags"), {
            "classes": ("wide",),
            "fields": ("is_first_login", "is_english", "is_turkish")
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "quick-create-student/",
                self.admin_site.admin_view(self.quick_create_student),
                name="quick_create_student",
            ),
        ]
        return custom_urls + urls

    def quick_create_student(self, request):
        if request.method == "POST":
            form = QuickStudentCreateForm(request.POST)

            if form.is_valid():
                email = form.cleaned_data["email"].strip().lower()
                courses = form.cleaned_data["courses"]
                program = form.cleaned_data["program"]
                program_start_date = form.cleaned_data["program_start_date"]
                has_meeting = form.cleaned_data["has_meeting"]
                meeting_link = form.cleaned_data["meeting_link"]

                user, created = CustomUser.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": email,
                        "is_first_login": True,
                        "is_turkish": True,
                        "is_english": False,
                    },
                )

                if created:
                    user.set_password(DEFAULT_PASSWORD)
                    user.save()

                for course in courses:
                    Enrollment.objects.get_or_create(user=user, course=course)

                    if course.course_type == Course.CourseType.TEST:
                        user.allowed_tests.add(course)

                program_enrollment = None
                program_calendar = ""
                if program:
                    program_enrollment, _ = ProgramEnrollment.objects.update_or_create(
                        user=user,
                        program=program,
                        defaults={"start_date": program_start_date, "is_active": True},
                    )
                    program_calendar = format_program_calendar(
                        program.steps.order_by("day_offset", "order", "id").values(
                            "day_offset", "email_title", "course__turkish_name", "course__english_name"
                        ),
                        program_start_date,
                    )

                course_lines = "\n".join(
                    [
                        f"✅ {course.turkish_name or course.english_name}"
                        for course in courses
                    ]
                )

                if not course_lines:
                    course_lines = "✅ İçerikler program takviminize göre hesabınıza tanımlanacaktır." if program else "✅ İçerikler kısa süre içinde hesabınıza tanımlanacaktır."

                program_text = ""
                if program:
                    program_text = f"""

━━━━━━━━━━━━━━━━━━━━
🗓️ {program.name} Eğitim Takvimi
━━━━━━━━━━━━━━━━━━━━

Program başlangıç tarihi: {program_start_date:%d.%m.%Y}

{program_calendar or "Program adımları yönetim panelinden eklenecektir."}

İçerikleriniz bu kişisel takvime göre otomatik olarak erişime açılacaktır.
"""

                meeting_text = ""

                if has_meeting:
                    meeting_text = f"""

📅 Birebir Görüşme Bilgisi

Volkan ile planladığınız gün ve saatte aşağıdaki link üzerinden görüşmeye katılabilirsiniz.

🔗 Görüşme Linki:
{meeting_link}

Görüşmeye katılmadan önce mümkünse platforma giriş yapıp size tanımlanan içeriklere göz atmanızı öneririm.
"""

                subject = "🎓 GRC Ustası Eğitim Programına Hoş Geldiniz"

                body = f"""Merhaba,

🎓 Volkan Güler ile GRC Ustası eğitim programına hoş geldiniz.

Bu süreçte size sadece video izleteceğimiz bir sistem değil; gerçek iş hayatına daha yakın, uygulamalı, soru odaklı ve kariyer gelişiminizi destekleyen bir öğrenme deneyimi sunmayı hedefliyoruz.

Aşağıda sizin için oluşturulan hesap bilgilerini bulabilirsiniz.

━━━━━━━━━━━━━━━━━━━━
🔐 Giriş Bilgileriniz
━━━━━━━━━━━━━━━━━━━━

🌐 Platform: https://www.grcustasi.com
👤 Kullanıcı adı: {email}
🔑 İlk giriş parolası: {DEFAULT_PASSWORD}

İlk girişinizden sonra güvenliğiniz için parolanızı değiştirmenizi öneririm.

━━━━━━━━━━━━━━━━━━━━
📚 Size Tanımlanan İçerikler
━━━━━━━━━━━━━━━━━━━━

{course_lines}
{program_text}

Bu içeriklerde ilerlerken lütfen:

✅ Videoları dikkatlice izleyin
✅ Soruları çözün
✅ Ekleri ve dokümanları indirin
✅ Anlamadığınız yerleri not alın
✅ Takıldığınız konularda iletişime geçmekten çekinmeyin

Bu kampın amacı sadece teorik bilgi vermek değil; aynı zamanda siber güvenlik, IT audit, GRC ve kariyer yolculuğunuzda daha net, daha güçlü ve daha özgüvenli ilerlemenize destek olmaktır.
{meeting_text}
━━━━━━━━━━━━━━━━━━━━
💬 İletişim ve Destek
━━━━━━━━━━━━━━━━━━━━

Her türlü ihtiyacınızda birebir Volkan ile iletişime geçebilirsiniz. Lütfen bundan çekinmeyin.

Takıldığınız bir konu, anlamadığınız bir bölüm, kariyerle ilgili bir soru veya platformla ilgili teknik bir problem olursa bana ulaşabilirsiniz.

Başarılar dilerim. Bu sürecin sizin için gerçekten faydalı ve dönüştürücü olmasını umuyorum. 🚀

Volkan Güler
GRC Ustası
"""

                mailto_url = (
                    f"mailto:{quote(email)}"
                    f"?subject={quote(subject)}"
                    f"&body={quote(body)}"
                )

                messages.success(request, f"{email} için hesap hazırlandı.")

                return render(
                    request,
                    "admin/quick_create_student_result.html",
                    {
                        "email": email,
                        "subject": subject,
                        "body": body,
                        "mailto_url": mailto_url,
                        "created": created,
                        "program_enrollment": program_enrollment,
                    },
                )

        else:
            form = QuickStudentCreateForm()

        return render(request, "admin/quick_create_student.html", {"form": form})
