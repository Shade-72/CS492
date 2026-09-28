"""SIEM-006 / AMG-009 / CNS-011: the single "who may see this student's
records" rule, and the audit-log helper ("Access logged") shared by every
app that touches student data.

Deliberately takes duck-typed `student`/`user` objects rather than importing
`academics.models.Student`, so this module (in `accounts`) never has to
import from an app that itself depends on `accounts` -- avoiding a circular
import while still being the one place this rule lives.
"""
from __future__ import annotations

import logging

access_logger = logging.getLogger("accounts.access")


def can_view_student(user, student) -> bool:
    if user is None or not getattr(user, "is_authenticated", False) or student is None:
        return False
    if user.role == "admin":
        return True
    if user.role == "parent":
        return student.parents.filter(pk=user.pk).exists()
    if user.role == "student":
        return student.user_id == user.pk
    if user.role == "teacher":
        return student.sections.filter(teacher=user).exists()
    return False


def log_access(user, action: str, student_id, allowed: bool, ip: str = "-") -> None:
    level = logging.INFO if allowed else logging.WARNING
    access_logger.log(
        level,
        "ACCESS %s action=%s user=%s role=%s student=%s ip=%s",
        "GRANTED" if allowed else "DENIED",
        action, getattr(user, "username", "anonymous"), getattr(user, "role", "-"),
        student_id or "-", ip,
    )
