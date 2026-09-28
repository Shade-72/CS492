"""Demo data for every screen in the app (accounts, academics, family
portal, notices). Mirrors the Sprint 1 Flask project's seed.py.

    python manage.py seed_demo_data

Safe to run more than once: it wipes and recreates the demo rows.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

DEMO_PASSWORD = "C0rrectHorse!Battery"


class Command(BaseCommand):
    help = "Create demo users, students, classes, grades, and messages."

    @transaction.atomic
    def handle(self, *args, **options):
        from academics.models import Attendance, ClassSection, Course, Grade, Student
        from accounts.models import User
        from family_portal.models import Message, MessageThread
        from notices.models import Announcement

        # Wipe demo rows so this command is idempotent.
        Message.objects.all().delete()
        MessageThread.objects.all().delete()
        Grade.objects.all().delete()
        Attendance.objects.all().delete()
        Student.objects.all().delete()
        ClassSection.objects.all().delete()
        Course.objects.all().delete()
        Announcement.objects.all().delete()
        User.objects.filter(username__in=[
            "demo_admin", "demo_teacher", "demo_parent", "other_parent", "demo_student",
        ]).delete()

        admin = User.objects.create_superuser("demo_admin", password=DEMO_PASSWORD, role=User.Role.ADMIN)
        teacher = User.objects.create_user("demo_teacher", password=DEMO_PASSWORD, role=User.Role.TEACHER)
        parent = User.objects.create_user("demo_parent", password=DEMO_PASSWORD, role=User.Role.PARENT)
        other_parent = User.objects.create_user("other_parent", password=DEMO_PASSWORD, role=User.Role.PARENT)
        student_user = User.objects.create_user("demo_student", password=DEMO_PASSWORD, role=User.Role.STUDENT)

        math = Course.objects.create(name="Math")
        english = Course.objects.create(name="English")
        section = ClassSection.objects.create(
            course=math, teacher=teacher, room="101",
            day_of_week="MON", start_time="09:00", end_time="10:00",
        )
        section_eng = ClassSection.objects.create(
            course=english, teacher=teacher, room="102",
            day_of_week="TUE", start_time="09:00", end_time="10:00",
        )

        ava = Student.objects.create(
            student_id="S-100", user=student_user, name="Ava Rivera", grade_level=8,
            ssn="123-45-6789", home_address="12 Elm St", medical_notes="Peanut allergy",
        )
        ava.parents.add(parent)
        leo = Student.objects.create(student_id="S-101", name="Leo Rivera", grade_level=6)
        leo.parents.add(parent)
        mia = Student.objects.create(student_id="S-200", name="Mia Chen", grade_level=8)
        mia.parents.add(other_parent)

        for student, math_score, eng_score in [(ava, (45, 50), (88, 100)),
                                                (leo, (72, 100), (91, 100)),
                                                (mia, (30, 50), (60, 100))]:
            section.students.add(student)
            section_eng.students.add(student)
            Grade.objects.create(student=student, section=section, assessment="Midterm",
                                 score=math_score[0], max_score=math_score[1], recorded_by=teacher)
            Grade.objects.create(student=student, section=section_eng, assessment="Essay",
                                 score=eng_score[0], max_score=eng_score[1], recorded_by=teacher)
            for day, status in [("2026-09-15", "present"), ("2026-09-16", "present"),
                                ("2026-09-17", "tardy"), ("2026-09-18", "absent")]:
                Attendance.objects.create(student=student, section=section, date=day,
                                          status=status, recorded_by=teacher)

        Announcement.objects.create(
            title="Welcome back!", message="First day of Sprint 2 demo data.", created_by=admin,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded demo data. Log in as demo_admin / demo_teacher / demo_parent / "
            f"other_parent / demo_student, password: {DEMO_PASSWORD}"
        ))
