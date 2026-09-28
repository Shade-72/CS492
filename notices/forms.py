from django import forms

from .models import Announcement, CriticalNotification


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "message"]


class CriticalNotificationForm(forms.ModelForm):
    class Meta:
        model = CriticalNotification
        fields = ["message", "channel"]
