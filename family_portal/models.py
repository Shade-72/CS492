"""CNS-011: Parent Messaging.

Replaces the Sprint 1 Flask `MessageStore` (manual Fernet encrypt/decrypt
calls on a plain dict) with ordinary Django models -- encryption becomes
transparent because the `body` field itself is an EncryptedTextField
(accounts/fields.py), so no view ever calls encrypt()/decrypt() directly.
"""
from django.conf import settings
from django.db import models

from accounts.fields import EncryptedTextField
from academics.models import Student


class MessageThread(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="message_threads")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_teacher",
        limit_choices_to={"role": "teacher"},
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_parent",
        limit_choices_to={"role": "parent"},
    )
    subject = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def other_participant(self, user):
        return self.parent if user.pk == self.teacher_id else self.teacher


class Message(models.Model):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = EncryptedTextField()  # "Messages stored securely" -- encrypted at rest
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sent_at"]
