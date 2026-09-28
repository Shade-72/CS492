"""Field-level encryption for UMA-003 ("Encrypt Data Storage").

Consolidates two separate attempts in the original repo: Keiana Henry's
sqlite3 script (SENSITIVE_FIELDS = ["email", "phone_number", "address"] +
Fernet helpers) and Carmen O'Brien's SQLAlchemy `Student` model with
`name_encrypted` / `parent_encrypted` columns (TaskID16). Here it's one
transparent Django model field instead of two bespoke, incompatible copies.

Values are Fernet-encrypted before being written to the database and
decrypted automatically when read back through the ORM, so model code
never calls encrypt/decrypt itself.

Note: an encrypted field cannot be used in an equality lookup (Fernet
ciphertext includes a random IV, so the same plaintext encrypts to a
different value every time) or exposed through Django's admin list_display
sorting. That's fine for the fields this app encrypts (SSN, address,
medical notes, phone number, message bodies) since none of those need to be
queried by value. Login continues to use the ordinary (unencrypted)
`username` field for that reason.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet() -> Fernet:
    return Fernet(settings.FIELD_ENCRYPTION_KEY)


class EncryptedTextField(models.TextField):
    """A TextField whose value is Fernet-encrypted at rest."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return _fernet().encrypt(str(value).encode("utf-8")).decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Tolerate rows written before encryption was turned on, or
            # written under a since-rotated key, rather than crashing reads.
            return value


class EncryptedCharField(EncryptedTextField):
    """Same as EncryptedTextField, but documents an intended plaintext
    length. Ciphertext is always longer than the plaintext, so this is
    still stored as a TEXT column -- `max_length` is for form validation
    only and is not enforced by the database.
    """

    def __init__(self, *args, max_length: int = 255, **kwargs):
        self.max_length = max_length
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        from django import forms

        defaults = {"max_length": self.max_length, "widget": forms.TextInput}
        defaults.update(kwargs)
        # Skip TextField.formfield()'s Textarea default.
        return super(models.TextField, self).formfield(**defaults)
