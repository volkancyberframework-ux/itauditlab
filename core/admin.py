from django.contrib import admin
from .models import CustomUser, Course, CourseSection, CourseSubsection, CourseFAQ

admin.site.register(Course)
admin.site.register(CourseSection)
admin.site.register(CourseSubsection)
admin.site.register(CourseFAQ)
admin.site.register(CustomUser)
