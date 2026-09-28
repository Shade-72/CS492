"""Sprint 2 forms: enrollment validation (SIEM-004), attendance and grade
entry (SIEM-005 / AMG-008), and scheduling conflict detection (AMG-007).
"""
from __future__ import annotations

import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Attendance, ClassSection, Course, Grade, Student

_PHONE_RE = re.compile(r"^[0-9()+\-.\s]{7,20}$")


class StudentEnrollmentForm(forms.ModelForm):
    """SIEM-004 + SIEM-005-Task-2 ("Add required field validation for
    enrollment"), ported from Carmen O'Brien's Sprint2_TaskID_1/_2 sqlite3
    scripts: required fields, a sane date of birth, and a valid grade
    level, with clear per-field error messages instead of a bare
    sqlite3.IntegrityError.
    """

    contact_phone = forms.CharField(required=False, help_text="Optional emergency contact number.")

    class Meta:
        model = Student
        fields = ["student_id", "name", "date_of_birth", "grade_level"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"].strip()
        if not student_id:
            raise ValidationError("Student ID is required.")
        return student_id

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Name is required.")
        return name

    def clean_grade_level(self):
        grade_level = self.cleaned_data["grade_level"]
        if not (1 <= grade_level <= 12):
            raise ValidationError("Grade level must be between 1 and 12.")
        return grade_level

    def clean_contact_phone(self):
        phone = self.cleaned_data.get("contact_phone", "").strip()
        if phone and not _PHONE_RE.match(phone):
            raise ValidationError("Enter a valid phone number.")
        return phone


class AttendanceForm(forms.ModelForm):
    """SIEM-005. The view restricts *who* can submit this (teacher/admin
    only); the form only validates the data itself."""

    class Meta:
        model = Attendance
        fields = ["student", "section", "date", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class GradeForm(forms.ModelForm):
    """AMG-008."""

    class Meta:
        model = Grade
        fields = ["student", "section", "assessment", "score", "max_score"]

    def clean(self):
        cleaned = super().clean()
        score, max_score = cleaned.get("score"), cleaned.get("max_score")
        if score is not None and max_score is not None:
            if max_score <= 0:
                raise ValidationError("Max score must be greater than zero.")
            if score < 0 or score > max_score:
                raise ValidationError("Score must be between 0 and the max score.")
        return cleaned


class ClassSectionForm(forms.ModelForm):
    """AMG-007: "Build class scheduling UI and basic conflict detection".

    Ported from Carmen O'Brien's tkinter desktop app (Sprint2_TaskID_7),
    which checked for double-booked teachers/students/rooms against a
    sqlite3 table from inside button-click handlers. The same three checks,
    now as form validation so they run identically whether the section is
    created from the HTML UI or the admin site.
    """

    class Meta:
        model = ClassSection
        fields = ["course", "teacher", "room", "day_of_week", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and start >= end:
            raise ValidationError("End time must be after start time.")
        if not (start and end and cleaned.get("day_of_week")):
            return cleaned

        candidate = ClassSection(
            day_of_week=cleaned["day_of_week"], start_time=start, end_time=end,
            room=cleaned.get("room", ""), teacher=cleaned.get("teacher"),
        )
        others = ClassSection.objects.filter(day_of_week=cleaned["day_of_week"])
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)

        for other in others:
            if not candidate.overlaps(other):
                continue
            if other.room == candidate.room:
                raise ValidationError(f"Room {candidate.room} is already booked at that time.")
            if cleaned.get("teacher") and other.teacher_id == cleaned["teacher"].pk:
                raise ValidationError("This teacher is already teaching another class at that time.")
        return cleaned


class EnrollStudentInSectionForm(forms.Form):
    """AMG-007's third rule: a *student* cannot be double-booked either.
    Checked here, separately from ClassSectionForm, because it depends on
    which student is being added -- not on the section's own fields.
    """

    student = forms.ModelChoiceField(queryset=Student.objects.all())

    def __init__(self, *args, section: ClassSection, **kwargs):
        self.section = section
        super().__init__(*args, **kwargs)

    def clean_student(self):
        student = self.cleaned_data["student"]
        conflict = student.sections.filter(day_of_week=self.section.day_of_week).exclude(
            pk=self.section.pk
        )
        for other in conflict:
            if self.section.overlaps(other):
                raise ValidationError(
                    f"{student.name} is already scheduled for {other} at that time."
                )
        return student
