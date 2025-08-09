from django.contrib import admin
from django import forms
from .models import CustomUser, Course, CourseSection, CourseSubsection, CourseFAQ


admin.site.register(CourseFAQ)
admin.site.register(CustomUser)


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


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ("id", "display_course", "difficulty", "duration", "score")
    search_fields = ("id", "description")
    list_filter = ("difficulty",)

    def display_course(self, obj):
        return getattr(obj, "name", None) or getattr(obj, "turkish_name", None) or getattr(obj, "english_name", None) or str(obj)
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
