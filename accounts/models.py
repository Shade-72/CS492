"""UMA-001 (Role-Based User Accounts) and part of UMA-003.

Replaces three separate, incompatible user models found in the original
repo: the Flask `UserStore`/`User` dataclass (Sprint 1), Carmen O'Brien's
SQLAlchemy `User`/`Role` tables (TaskID4), and Keiana Henry's raw sqlite3
`users`/`roles` tables. Django's own auth system (permissions, the admin
site, `login()`/`logout()`, password hashing) replaces all three.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from .fields import EncryptedCharField


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)

    # UMA-003 / Keiana Henry's SENSITIVE_FIELDS list: phone number and home
    # address are encrypted at rest. (Email is left as Django's ordinary
    # EmailField: it's used for password-reset lookups and admin display,
    # neither of which works against Fernet ciphertext -- see fields.py.)
    phone_number = EncryptedCharField(max_length=32, blank=True, default="")

    def is_role(self, *roles: str) -> bool:
        return self.role in roles

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.username
