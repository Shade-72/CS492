"""SIEM-004 (Student Profile Enrollment), SIEM-005 (Attendance Tracking),
AMG-007 (Course Scheduling), AMG-008 (Grade Entry), and the data AMG-009
(Report Card Generation) reads.

Replaces Carmen O'Brien's raw sqlite3 `students`/`schedule` tables
(Sprint2_TaskID_1, _7, _8) and Keiana Henry's raw sqlite3 `attendance`
table (KHTask3/KHTASK4) with one Django ORM schema everyone else's views
share.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from accounts.fields import EncryptedCharField, EncryptedTextField


class Student(models.Model):
    """A student's profile.

    SSN, home address, and medical notes are encrypted at rest (UMA-003),
    same as Keiana Henry's SENSITIVE_FIELDS list and Carmen O'Brien's
    encrypted `Student` model (TaskID16) -- unified into one model instead
    of two.
    """

    student_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="student_profile",
    )
    name = models.CharField(max_length=150)
    date_of_birth = models.DateField(null=True, blank=True)
    grade_level = models.PositiveSmallIntegerField()
    parents = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="children", blank=True,
        limit_choices_to={"role": "parent"},
    )

    ssn = EncryptedCharField(max_length=32, blank=True, default="")
    home_address = EncryptedCharField(max_length=255, blank=True, default="")
    medical_notes = EncryptedTextField(blank=True, default="")

    # SIEM-006: the only fields a parent's view is ever built from.
    PARENT_VISIBLE_FIELDS = ("student_id", "name", "grade_level")

    def parent_view(self) -> dict:
        return {field: getattr(self, field) for field in self.PARENT_VISIBLE_FIELDS}

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.student_id} - {self.name}"


class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class ClassSection(models.Model):
    """AMG-007: a scheduled meeting of a course, taught by one teacher.

    Conflict detection (a teacher, student, or room double-booked at an
    overlapping time) lives in academics/forms.py, since it depends on
    which section is being created/edited, not on the model alone.
    """

    DAYS = [
        ("MON", "Monday"), ("TUE", "Tuesday"), ("WED", "Wednesday"),
        ("THU", "Thursday"), ("FRI", "Friday"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sections_taught",
        limit_choices_to={"role": "teacher"},
    )
    room = models.CharField(max_length=50)
    day_of_week = models.CharField(max_length=3, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    students = models.ManyToManyField(Student, related_name="sections", blank=True)

    def overlaps(self, other: "ClassSection") -> bool:
        if self.day_of_week != other.day_of_week:
            return False
        return self.start_time < other.end_time and other.start_time < self.end_time

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.course} ({self.get_day_of_week_display()} {self.start_time}-{self.end_time})"


class Attendance(models.Model):
    """SIEM-005. Only a teacher or admin may create/edit these (enforced in
    the view with accounts.decorators.role_required, matching Keiana
    Henry's `can_modify_attendance()` check from KHTASK4)."""

    STATUS_CHOICES = [("present", "Present"), ("absent", "Absent"), ("tardy", "Tardy")]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        unique_together = ("student", "section", "date")
        ordering = ["-date"]


class Grade(models.Model):
    """AMG-008. Visibility to "the correct student" (KHTASK10) is enforced
    in views.py, not here -- a model has no idea who's asking."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="grades")
    section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="grades")
    assessment = models.CharField(max_length=150)
    score = models.FloatField()
    max_score = models.FloatField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
