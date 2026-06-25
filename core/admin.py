from urllib.parse import quote

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import render
from django.urls import path
from django.utils.translation import gettext_lazy as _

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
)

DEFAULT_PASSWORD = "Siberkobi1234"


from django.contrib import admin
from .models import Bootcamp, BootcampPurchase


@admin.register(Bootcamp)
class BootcampAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "currency", "duration", "level", "is_active", "order", "created_at")
    list_filter = ("is_active", "currency", "created_at")
    search_fields = ("title", "description", "level")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("order", "-created_at")


@admin.register(BootcampPurchase)
class BootcampPurchaseAdmin(admin.ModelAdmin):
    list_display = ("bootcamp", "email", "is_paid", "stripe_session_id", "created_at", "paid_at")
    list_filter = ("is_paid", "created_at", "paid_at")
    search_fields = ("email", "stripe_session_id", "bootcamp__title")
    readonly_fields = ("created_at",)

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


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    autocomplete_fields = ("course",)
    verbose_name = "Enrollment"
    verbose_name_plural = "Enrollments"


class QuickStudentCreateForm(forms.Form):
    email = forms.EmailField(label="Öğrenci e-posta adresi")

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

                course_lines = "\n".join(
                    [
                        f"✅ {course.turkish_name or course.english_name}"
                        for course in courses
                    ]
                )

                if not course_lines:
                    course_lines = "✅ İçerikler kısa süre içinde hesabınıza tanımlanacaktır."

                meeting_text = ""

                if has_meeting:
                    meeting_text = f"""

📅 Birebir Görüşme Bilgisi

Volkan ile planladığınız gün ve saatte aşağıdaki link üzerinden görüşmeye katılabilirsiniz.

🔗 Görüşme Linki:
{meeting_link}

Görüşmeye katılmadan önce mümkünse platforma giriş yapıp size tanımlanan içeriklere göz atmanızı öneririm.
"""

                subject = "🎓 Siberkobi Siber Güvenlik Kampına Hoş Geldiniz"

                body = f"""Merhaba,

🎓 Volkan Güler ile Siberkobi üzerinden Siber Güvenlik Kampına hoş geldiniz.

Bu süreçte size sadece video izleteceğimiz bir sistem değil; gerçek iş hayatına daha yakın, uygulamalı, soru odaklı ve kariyer gelişiminizi destekleyen bir öğrenme deneyimi sunmayı hedefliyoruz.

Aşağıda sizin için oluşturulan hesap bilgilerini bulabilirsiniz.

━━━━━━━━━━━━━━━━━━━━
🔐 Giriş Bilgileriniz
━━━━━━━━━━━━━━━━━━━━

🌐 Platform: https://siberkobi.co
👤 Kullanıcı adı: {email}
🔑 İlk giriş parolası: {DEFAULT_PASSWORD}

İlk girişinizden sonra güvenliğiniz için parolanızı değiştirmenizi öneririm.

━━━━━━━━━━━━━━━━━━━━
📚 Size Tanımlanan İçerikler
━━━━━━━━━━━━━━━━━━━━

{course_lines}

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
Siberkobi
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
                    },
                )

        else:
            form = QuickStudentCreateForm()

        return render(request, "admin/quick_create_student.html", {"form": form})
