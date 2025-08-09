from django.contrib import admin
from django import forms
from .models import CustomUser, Course, CourseSection, CourseSubsection, CourseFAQ


admin.site.register(CourseSection)
admin.site.register(CourseSubsection)
admin.site.register(CourseFAQ)
admin.site.register(CustomUser)


class CourseAdminForm(forms.ModelForm):
    # Optional extra upload field to attach/replace the course PDF from admin
    upload_pdf = forms.FileField(required=False, help_text="Upload/replace course attachment (PDF or any file)")

    class Meta:
        model = Course
        fields = "__all__"

    def save(self, commit=True):
        instance = super().save(commit=False)

        pdf_file = self.cleaned_data.get("upload_pdf")
        if pdf_file:
            # If there is an existing file, remove it first
            if instance.pk and getattr(instance, "attachment", None):
                instance.attachment.delete(save=False)
            # Save the new file to the FileField storage (Render disk)
            instance.attachment.save(pdf_file.name, pdf_file, save=False)

        if commit:
            instance.save()
        return instance


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
