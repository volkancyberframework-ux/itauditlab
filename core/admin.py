from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
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
)

from django.contrib import admin
from .models import NewsletterLead


@admin.register(NewsletterLead)
class NewsletterLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "created_at")
    search_fields = ("email",)
    list_filter = ("source", "created_at")
    ordering = ("-created_at",)


@admin.register(DigitalProduct)
class DigitalProductAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "original_price", "currency", "difficulty", "rating", "reviews_count", "is_active")
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

# -----------------------------
# Course upload form (PDF helper)
# -----------------------------
class CourseAdminForm(forms.ModelForm):
    upload_pdf = forms.FileField(required=False, help_text="Upload/replace course attachment (PDF or any file)")

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

# -----------------------------
# Course admin
# -----------------------------
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ("id", "display_course", "course_type", "difficulty", "duration", "score")
    search_fields = ("id", "description", "turkish_name", "english_name")
    list_filter = ("course_type", "difficulty", "dashboard_activated", "main_page_activated", "is_english", "is_turkish")

    def display_course(self, obj):
        return getattr(obj, "turkish_name", None) or getattr(obj, "english_name", None) or str(obj)
    display_course.short_description = "Course"

# -----------------------------
# Sections admins
# -----------------------------
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
    search_fields = ("question", "answer", "course__turkish_name", "course__english_name")
    list_filter = ("course",)

# -----------------------------
# NEW: Enrollment inline (per user)
# -----------------------------
class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    autocomplete_fields = ("course",)
    verbose_name = "Enrollment"
    verbose_name_plural = "Enrollments"

# -----------------------------
# CustomUser admin
# -----------------------------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "is_staff", "is_first_login", "is_english", "is_turkish")
    list_filter = UserAdmin.list_filter + ("is_first_login", "is_english", "is_turkish")
    search_fields = UserAdmin.search_fields + ("email",)

    # Nice dual-select UI for test access
    filter_horizontal = ("allowed_tests",)

    fieldsets = UserAdmin.fieldsets + (
        (_("Profile flags"), {"fields": ("is_first_login", "is_english", "is_turkish")}),
        (_("Test access"), {"fields": ("allowed_tests",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_("Profile flags"), {"classes": ("wide",), "fields": ("is_first_login", "is_english", "is_turkish")}),
    )

    # <-- ADDED: show/edit enrollments on the user page
    inlines = [EnrollmentInline]
