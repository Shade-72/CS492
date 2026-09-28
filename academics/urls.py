from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    path("students/enroll/", views.enroll_student, name="enroll_student"),
    path("students/<str:student_id>/", views.student_detail, name="student_detail"),
    path("students/<str:student_id>/grades/", views.student_grades, name="student_grades"),
    path("attendance/record/", views.record_attendance, name="record_attendance"),
    path("grades/enter/", views.enter_grade, name="enter_grade"),
    path("sections/schedule/", views.schedule_section, name="schedule_section"),
    path("sections/<int:section_id>/enroll/", views.enroll_in_section, name="enroll_in_section"),
    path("report-card/<str:student_id>/", views.report_card, name="report_card"),
    path("report-card/<str:student_id>/export.csv", views.report_card_csv, name="report_card_csv"),
    path("api/report-card/<str:student_id>/", views.api_report_card, name="api_report_card"),
]
