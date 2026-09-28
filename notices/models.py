"""CNS-010 (Announcements) and CNS-012 (Critical Notifications)."""
from django.conf import settings
from django.db import models


class Announcement(models.Model):
    title = models.CharField(max_length=150)
    message = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class CriticalNotification(models.Model):
    CHANNEL_CHOICES = [("email", "Email"), ("sms", "SMS"), ("in_app", "In-app")]

    message = models.TextField()
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="in_app")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
