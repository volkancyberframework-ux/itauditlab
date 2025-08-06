from django.contrib import admin
from .models import CustomUser, Course, CourseSection, CourseSubsection, CourseFAQ
import cloudinary.uploader

admin.site.register(Course)
admin.site.register(CourseSection)
admin.site.register(CourseSubsection)
admin.site.register(CourseFAQ)
admin.site.register(CustomUser)

class CourseAdminForm(forms.ModelForm):
    upload_pdf = forms.FileField(required=False)

    class Meta:
        model = Course
        fields = '__all__'

    def save(self, commit=True):
        instance = super().save(commit=False)

        pdf_file = self.cleaned_data.get('upload_pdf')
        if pdf_file:
            # ✅ Upload to Cloudinary as a RAW file
            result = cloudinary.uploader.upload(
                pdf_file,
                resource_type='raw',
                folder='course_attachments/',
                use_filename=True,
                unique_filename=False
            )
            instance.attachment = result.get('secure_url')

        if commit:
            instance.save()
        return instance


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
