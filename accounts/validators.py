"""UMA-002: "Implement password complexity validation".

Ported from the Sprint 1 Flask `validate_password()` function into Django's
password-validator protocol (a class with `validate()` and
`get_help_text()`), so it plugs into AUTH_PASSWORD_VALIDATORS and runs
automatically for Django's own login/registration/admin password forms,
not just a hand-rolled endpoint.
"""
import re

from django.core.exceptions import ValidationError

_COMMON_PASSWORDS = {
    "password", "password1", "12345678", "qwerty123",
    "letmein", "admin123", "welcome1", "iloveyou",
}

_SPECIAL_CHARS = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""


class ComplexityValidator:
    def __init__(self, min_length: int = 10):
        self.min_length = min_length

    def validate(self, password, user=None):
        errors = []

        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long.")
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit.")
        if not re.search(f"[{re.escape(_SPECIAL_CHARS)}]", password):
            errors.append("Password must contain at least one special character.")
        if re.search(r"\s", password):
            errors.append("Password must not contain whitespace.")
        if password.lower() in _COMMON_PASSWORDS:
            errors.append("Password is too common; choose something less guessable.")

        if errors:
            raise ValidationError(errors, code="password_complexity")

    def get_help_text(self):
        return (
            f"Your password must be at least {self.min_length} characters long and include "
            "an uppercase letter, a lowercase letter, a digit, a special character, and no "
            "whitespace."
        )
