from django.contrib import admin

from .models import Attendance, ClassSection, Course, Grade, Student

admin.site.register(Course)
admin.site.register(ClassSection)
admin.site.register(Attendance)
admin.site.register(Grade)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "name", "grade_level")
    search_fields = ("student_id", "name")
