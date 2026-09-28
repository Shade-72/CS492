"""CNS-010 + CNS-012 tests."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Announcement, CriticalNotification

User = get_user_model()
PASSWORD = "C0rrectHorse!Battery"


class AnnouncementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", password=PASSWORD, role=User.Role.ADMIN)
        self.teacher = User.objects.create_user("teacher1", password=PASSWORD, role=User.Role.TEACHER)
        self.student = User.objects.create_user("student1", password=PASSWORD, role=User.Role.STUDENT)
        self.announcement = Announcement.objects.create(title="Welcome", message="Hi all", created_by=self.admin)

    def _client_for(self, username):
        client = Client()
        client.login(username=username, password=PASSWORD)
        return client

    def test_any_authenticated_role_can_view_announcements(self):
        for username in ("admin1", "teacher1", "student1"):
            response = self._client_for(username).get(reverse("notices:announcement_list"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Welcome")

    def test_anonymous_cannot_view_announcements(self):
        response = Client().get(reverse("notices:announcement_list"))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_create_announcement(self):
        response = self._client_for("admin1").post(reverse("notices:announcement_create"), {
            "title": "Snow day", "message": "School is closed.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Announcement.objects.filter(title="Snow day").exists())

    def test_teacher_cannot_create_announcement(self):
        response = self._client_for("teacher1").post(reverse("notices:announcement_create"), {
            "title": "Snow day", "message": "School is closed.",
        })
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_edit_or_delete_announcement(self):
        client = self._client_for("student1")
        self.assertEqual(
            client.post(reverse("notices:announcement_edit", args=[self.announcement.pk]),
                        {"title": "x", "message": "y"}).status_code,
            403,
        )
        self.assertEqual(
            client.post(reverse("notices:announcement_delete", args=[self.announcement.pk])).status_code,
            403,
        )
        self.assertTrue(Announcement.objects.filter(pk=self.announcement.pk).exists())

    def test_admin_can_delete_announcement(self):
        response = self._client_for("admin1").post(
            reverse("notices:announcement_delete", args=[self.announcement.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Announcement.objects.filter(pk=self.announcement.pk).exists())


class CriticalNotificationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", password=PASSWORD, role=User.Role.ADMIN)
        self.teacher = User.objects.create_user("teacher1", password=PASSWORD, role=User.Role.TEACHER)

    def _client_for(self, username):
        client = Client()
        client.login(username=username, password=PASSWORD)
        return client

    def test_admin_can_send_critical_notification(self):
        response = self._client_for("admin1").post(reverse("notices:critical_notification_create"), {
            "message": "Lockdown drill at 2pm.", "channel": "sms",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CriticalNotification.objects.filter(message="Lockdown drill at 2pm.").exists())

    def test_non_admin_cannot_send_critical_notification(self):
        response = self._client_for("teacher1").post(reverse("notices:critical_notification_create"), {
            "message": "Lockdown drill at 2pm.", "channel": "sms",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CriticalNotification.objects.exists())

    def test_denial_is_logged(self):
        with self.assertLogs("accounts.access", level="WARNING") as logs:
            self._client_for("teacher1").post(reverse("notices:critical_notification_create"), {
                "message": "x", "channel": "sms",
            })
        self.assertIn("ACCESS DENIED", logs.output[0])
