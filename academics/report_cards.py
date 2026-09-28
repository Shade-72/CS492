"""AMG-009: Report Card Generation.

    - Includes grades + attendance    -> build_report_card()
    - Exportable digital format       -> CSV download (views.py) and the
                                          page itself
    - Students/parents see only their own -> enforced in views.py via
                                          accounts.access.can_view_student
"""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from statistics import mean

from .models import Student

LETTER_SCALE = ((90, "A"), (80, "B"), (70, "C"), (60, "D"))


def letter_grade(percent: float) -> str:
    for cutoff, letter in LETTER_SCALE:
        if percent >= cutoff:
            return letter
    return "F"


def build_report_card(student: Student) -> dict:
    earned: dict[str, float] = defaultdict(float)
    possible: dict[str, float] = defaultdict(float)
    for grade in student.grades.select_related("section__course"):
        course_name = grade.section.course.name
        earned[course_name] += grade.score
        possible[course_name] += grade.max_score

    courses = []
    for course_name in sorted(possible):
        pct = round(earned[course_name] / possible[course_name] * 100, 1) if possible[course_name] else 0.0
        courses.append({"course": course_name, "percent": pct, "letter": letter_grade(pct)})

    overall = round(mean(c["percent"] for c in courses), 1) if courses else None

    counts = {"present": 0, "absent": 0, "tardy": 0}
    for record in student.attendance_records.all():
        if record.status in counts:
            counts[record.status] += 1
    total_days = sum(counts.values())
    rate = round((counts["present"] + counts["tardy"]) / total_days * 100, 1) if total_days else None

    return {
        "student": {"student_id": student.student_id, "name": student.name,
                    "grade_level": student.grade_level},
        "courses": courses,
        "overall_percent": overall,
        "overall_letter": letter_grade(overall) if overall is not None else None,
        "attendance": {**counts, "total": total_days, "rate_percent": rate},
    }


def _safe_cell(value):
    """Neutralize spreadsheet formula injection in exported CSV."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def report_card_to_csv(card: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    student, attendance = card["student"], card["attendance"]
    writer.writerow(["Report Card"])
    writer.writerow(["Student", _safe_cell(student["name"])])
    writer.writerow(["Student ID", _safe_cell(student["student_id"])])
    writer.writerow(["Grade level", student["grade_level"]])
    writer.writerow([])
    writer.writerow(["Course", "Percent", "Letter"])
    for course in card["courses"]:
        writer.writerow([_safe_cell(course["course"]), course["percent"], course["letter"]])
    writer.writerow(["Overall", card["overall_percent"], card["overall_letter"]])
    writer.writerow([])
    writer.writerow(["Attendance", "Count"])
    for key in ("present", "absent", "tardy", "total"):
        writer.writerow([key.capitalize(), attendance[key]])
    writer.writerow(["Attendance rate (%)", attendance["rate_percent"]])
    return buf.getvalue()
