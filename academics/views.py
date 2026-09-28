from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.access import can_view_student, log_access
from accounts.decorators import client_ip, role_required

from .forms import (
    AttendanceForm, ClassSectionForm, EnrollStudentInSectionForm, GradeForm, StudentEnrollmentForm,
)
from .models import Attendance, ClassSection, Grade, Student
from .report_cards import build_report_card, report_card_to_csv


# ---- SIEM-004: Student Profile Enrollment ----------------------------------
@role_required("admin")
def enroll_student(request):
    if request.method == "POST":
        form = StudentEnrollmentForm(request.POST)
        if form.is_valid():
            student = form.save()
            return redirect("academics:student_detail", student_id=student.student_id)
    else:
        form = StudentEnrollmentForm()
    return render(request, "academics/enroll_student.html", {"form": form})


@role_required("admin", "teacher")
def student_detail(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    return render(request, "academics/student_detail.html", {"student": student})


# ---- SIEM-005: Attendance Tracking -----------------------------------------
@role_required("teacher", "admin")
def record_attendance(request):
    """Only a teacher or admin may reach this view at all (role_required),
    matching Keiana Henry's `can_modify_attendance()` (KHTASK4) -- a
    student can never even load the form, let alone submit it."""
    if request.method == "POST":
        form = AttendanceForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.recorded_by = request.user
            record.save()
            form = AttendanceForm()
    else:
        form = AttendanceForm()
    recent = Attendance.objects.select_related("student", "section")[:20]
    return render(request, "academics/record_attendance.html", {"form": form, "recent": recent})


# ---- AMG-008: Grade Entry ---------------------------------------------------
@role_required("teacher", "admin")
def enter_grade(request):
    if request.method == "POST":
        form = GradeForm(request.POST)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.recorded_by = request.user
            grade.save()
            form = GradeForm()
    else:
        form = GradeForm()
    recent = Grade.objects.select_related("student", "section")[:20]
    return render(request, "academics/enter_grade.html", {"form": form, "recent": recent})


@login_required
def student_grades(request, student_id):
    """KHTASK10: "you cannot view another student's grades" -- generalized
    to every role via accounts.access.can_view_student (admin, the
    student themself, their assigned teacher, or their parent)."""
    student = get_object_or_404(Student, student_id=student_id)
    allowed = can_view_student(request.user, student)
    log_access(request.user, "view_grades", student_id, allowed, client_ip(request))
    if not allowed:
        raise PermissionDenied("You cannot view another student's grades.")
    grades = student.grades.select_related("section__course")
    return render(request, "academics/student_grades.html", {"student": student, "grades": grades})


# ---- AMG-007: Course Scheduling ---------------------------------------------
@role_required("admin")
def schedule_section(request):
    if request.method == "POST":
        form = ClassSectionForm(request.POST)
        if form.is_valid():
            form.save()
            form = ClassSectionForm()
    else:
        form = ClassSectionForm()
    sections = ClassSection.objects.select_related("course", "teacher")
    return render(request, "academics/schedule_section.html", {"form": form, "sections": sections})


@role_required("admin")
def enroll_in_section(request, section_id):
    """AMG-007's third conflict rule (a student can't be double-booked) and
    Sprint2_TaskID_8's "prevent duplicate assignment" (a student already
    in the section is simply already in the M2M, so re-adding is a no-op,
    not a duplicate row)."""
    section = get_object_or_404(ClassSection, pk=section_id)
    error = None
    if request.method == "POST":
        form = EnrollStudentInSectionForm(request.POST, section=section)
        if form.is_valid():
            section.students.add(form.cleaned_data["student"])
            return redirect("academics:schedule_section")
        error = form.errors.get("student", [None])[0]
    else:
        form = EnrollStudentInSectionForm(section=section)
    return render(
        request, "academics/enroll_in_section.html", {"form": form, "section": section, "error": error}
    )


# ---- AMG-009: Report Card Generation ---------------------------------------
def _authorized_card(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    allowed = can_view_student(request.user, student)
    log_access(request.user, "view_report_card", student_id, allowed, client_ip(request))
    if not allowed:
        return None
    return build_report_card(student)


@login_required
def report_card(request, student_id):
    card = _authorized_card(request, student_id)
    if card is None:
        raise PermissionDenied("Report card not found.")
    return render(request, "academics/report_card.html", {"card": card})


@login_required
def report_card_csv(request, student_id):
    card = _authorized_card(request, student_id)
    if card is None:
        raise PermissionDenied("Report card not found.")
    response = HttpResponse(report_card_to_csv(card), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="report_card_{student_id}.csv"'
    return response


@login_required
def api_report_card(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    allowed = can_view_student(request.user, student)
    log_access(request.user, "view_report_card", student_id, allowed, client_ip(request))
    if not allowed:
        return JsonResponse({"success": False, "message": "Report card not found."}, status=404)
    return JsonResponse({"success": True, "report_card": build_report_card(student)})
