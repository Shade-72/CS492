"""SIEM-004/005, AMG-007/008/009 tests.

Covers Carmen O'Brien's required-field validation (Sprint2_TaskID_2),
Keiana Henry's "students cannot modify attendance" rule (KHTASK4) and
"cannot view another student's grades" rule (KHTASK10), and the tkinter
scheduling conflict checks (Sprint2_TaskID_7/_8) -- all re-implemented as
Django form/view tests instead of print-statement-driven tkinter scripts.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .forms import ClassSectionForm, EnrollStudentInSectionForm, StudentEnrollmentForm
from .models import Attendance, ClassSection, Course, Grade, Student
from .report_cards import build_report_card, letter_grade, report_card_to_csv

User = get_user_model()
PASSWORD = "C0rrectHorse!Battery"


class EnrollmentValidationTests(TestCase):
    def test_valid_enrollment_passes(self):
        form = StudentEnrollmentForm(data={
            "student_id": "S-1", "name": "New Kid", "date_of_birth": "2015-05-01",
            "grade_level": 5, "contact_phone": "555-0100",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name_rejected(self):
        form = StudentEnrollmentForm(data={"student_id": "S-1", "name": "", "grade_level": 5})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_out_of_range_grade_level_rejected(self):
        form = StudentEnrollmentForm(data={"student_id": "S-1", "name": "Kid", "grade_level": 25})
        self.assertFalse(form.is_valid())
        self.assertIn("grade_level", form.errors)

    def test_invalid_phone_rejected(self):
        form = StudentEnrollmentForm(data={
            "student_id": "S-1", "name": "Kid", "grade_level": 5, "contact_phone": "abc",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("contact_phone", form.errors)


class AttendanceAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", password=PASSWORD, role=User.Role.ADMIN)
        self.teacher = User.objects.create_user("teacher1", password=PASSWORD, role=User.Role.TEACHER)
        self.student_user = User.objects.create_user("student1", password=PASSWORD, role=User.Role.STUDENT)
        self.course = Course.objects.create(name="Math")
        self.section = ClassSection.objects.create(
            course=self.course, teacher=self.teacher, room="1", day_of_week="MON",
            start_time="09:00", end_time="10:00",
        )
        self.student = Student.objects.create(student_id="S-1", name="Kid", grade_level=5, user=self.student_user)

    def _client_for(self, user):
        client = Client()
        client.login(username=user.username, password=PASSWORD)
        return client

    def test_teacher_can_record_attendance(self):
        response = self._client_for(self.teacher).post(reverse("academics:record_attendance"), {
            "student": self.student.pk, "section": self.section.pk, "date": "2026-09-15", "status": "present",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Attendance.objects.filter(student=self.student).exists())

    def test_student_cannot_record_attendance(self):
        response = self._client_for(self.student_user).post(reverse("academics:record_attendance"), {
            "student": self.student.pk, "section": self.section.pk, "date": "2026-09-15", "status": "present",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Attendance.objects.filter(student=self.student).exists())

    def test_anonymous_redirected_to_login(self):
        response = Client().get(reverse("academics:record_attendance"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.headers["Location"])


class GradeTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("teacher1", password=PASSWORD, role=User.Role.TEACHER)
        self.other_student_user = User.objects.create_user("other_student", password=PASSWORD, role=User.Role.STUDENT)
        self.student_user = User.objects.create_user("student1", password=PASSWORD, role=User.Role.STUDENT)
        self.course = Course.objects.create(name="Math")
        self.section = ClassSection.objects.create(
            course=self.course, teacher=self.teacher, room="1", day_of_week="MON",
            start_time="09:00", end_time="10:00",
        )
        self.student = Student.objects.create(student_id="S-1", name="Kid", grade_level=5, user=self.student_user)
        self.section.students.add(self.student)
        Grade.objects.create(student=self.student, section=self.section, assessment="Quiz",
                             score=8, max_score=10, recorded_by=self.teacher)

    def _client_for(self, user):
        client = Client()
        client.login(username=user.username, password=PASSWORD)
        return client

    def test_score_above_max_rejected(self):
        response = self._client_for(self.teacher).post(reverse("academics:enter_grade"), {
            "student": self.student.pk, "section": self.section.pk, "assessment": "Test",
            "score": 999, "max_score": 100,
        })
        self.assertEqual(response.status_code, 200)  # re-renders with errors
        self.assertEqual(Grade.objects.filter(assessment="Test").count(), 0)

    def test_student_can_view_own_grades(self):
        response = self._client_for(self.student_user).get(
            reverse("academics:student_grades", args=[self.student.student_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quiz")

    def test_student_cannot_view_another_students_grades(self):
        response = self._client_for(self.other_student_user).get(
            reverse("academics:student_grades", args=[self.student.student_id])
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_of_assigned_section_can_view_grades(self):
        response = self._client_for(self.teacher).get(
            reverse("academics:student_grades", args=[self.student.student_id])
        )
        self.assertEqual(response.status_code, 200)


class SchedulingConflictTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("teacher1", password=PASSWORD, role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user("teacher2", password=PASSWORD, role=User.Role.TEACHER)
        self.math = Course.objects.create(name="Math")
        self.english = Course.objects.create(name="English")
        self.existing = ClassSection.objects.create(
            course=self.math, teacher=self.teacher, room="101", day_of_week="MON",
            start_time="09:00", end_time="10:00",
        )

    def test_non_overlapping_section_is_valid(self):
        form = ClassSectionForm(data={
            "course": self.english.pk, "teacher": self.teacher.pk, "room": "101",
            "day_of_week": "MON", "start_time": "10:00", "end_time": "11:00",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_same_room_overlapping_time_rejected(self):
        form = ClassSectionForm(data={
            "course": self.english.pk, "teacher": self.other_teacher.pk, "room": "101",
            "day_of_week": "MON", "start_time": "09:30", "end_time": "10:30",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("already booked", str(form.errors))

    def test_teacher_double_booked_rejected(self):
        form = ClassSectionForm(data={
            "course": self.english.pk, "teacher": self.teacher.pk, "room": "202",
            "day_of_week": "MON", "start_time": "09:30", "end_time": "10:30",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("already teaching", str(form.errors))

    def test_end_before_start_rejected(self):
        form = ClassSectionForm(data={
            "course": self.english.pk, "teacher": self.other_teacher.pk, "room": "202",
            "day_of_week": "TUE", "start_time": "10:00", "end_time": "09:00",
        })
        self.assertFalse(form.is_valid())

    def test_student_double_booked_rejected(self):
        student = Student.objects.create(student_id="S-1", name="Kid", grade_level=5)
        other_section = ClassSection.objects.create(
            course=self.english, teacher=self.other_teacher, room="202", day_of_week="MON",
            start_time="09:30", end_time="10:30",
        )
        self.existing.students.add(student)
        form = EnrollStudentInSectionForm(data={"student": student.pk}, section=other_section)
        self.assertFalse(form.is_valid())


class ReportCardTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("teacher1", password=PASSWORD, role=User.Role.TEACHER)
        self.admin = User.objects.create_user("admin1", password=PASSWORD, role=User.Role.ADMIN)
        self.other_user = User.objects.create_user("stranger", password=PASSWORD, role=User.Role.STUDENT)
        course = Course.objects.create(name="Math")
        section = ClassSection.objects.create(
            course=course, teacher=self.teacher, room="1", day_of_week="MON",
            start_time="09:00", end_time="10:00",
        )
        self.student = Student.objects.create(student_id="S-1", name="Ava Rivera", grade_level=8)
        section.students.add(self.student)
        Grade.objects.create(student=self.student, section=section, assessment="Midterm",
                             score=45, max_score=50, recorded_by=self.teacher)
        for day, status in [("2026-09-15", "present"), ("2026-09-16", "tardy"), ("2026-09-17", "absent")]:
            Attendance.objects.create(student=self.student, section=section, date=day, status=status)

    def test_letter_grade_boundaries(self):
        for percent, letter in [(100, "A"), (90, "A"), (89.9, "B"), (70, "C"), (60, "D"), (59.9, "F")]:
            self.assertEqual(letter_grade(percent), letter, percent)

    def test_build_report_card_math_and_attendance(self):
        card = build_report_card(self.student)
        self.assertEqual(card["courses"][0], {"course": "Math", "percent": 90.0, "letter": "A"})
        self.assertEqual(card["overall_percent"], 90.0)
        att = card["attendance"]
        self.assertEqual((att["present"], att["tardy"], att["absent"], att["total"]), (1, 1, 1, 3))
        self.assertAlmostEqual(att["rate_percent"], 66.7, places=1)

    def test_csv_export_neutralizes_formula_injection(self):
        card = build_report_card(self.student)
        card["student"]["name"] = '=HYPERLINK("http://evil")'
        self.assertIn("'=HYPERLINK", report_card_to_csv(card))

    def test_admin_can_view_any_report_card(self):
        client = Client()
        client.login(username="admin1", password=PASSWORD)
        response = client.get(reverse("academics:report_card", args=[self.student.student_id]))
        self.assertEqual(response.status_code, 200)

    def test_unrelated_student_cannot_view_report_card(self):
        client = Client()
        client.login(username="stranger", password=PASSWORD)
        response = client.get(reverse("academics:report_card", args=[self.student.student_id]))
        self.assertEqual(response.status_code, 403)

    def test_csv_download_is_an_attachment(self):
        client = Client()
        client.login(username="admin1", password=PASSWORD)
        response = client.get(reverse("academics:report_card_csv", args=[self.student.student_id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])
