"""SIEM-006 + CNS-011 tests. Covers the same ground as the Sprint 1 Flask
tests/test_parent_access.py and tests/test_messaging.py."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from academics.models import ClassSection, Course, Student

from .models import Message, MessageThread

User = get_user_model()
PASSWORD = "C0rrectHorse!Battery"

SENSITIVE_VALUES = ("123-45-6789", "12 Elm St", "Peanut allergy")


class ParentAccessTests(TestCase):
    def setUp(self):
        self.parent = User.objects.create_user("demo_parent", password=PASSWORD, role=User.Role.PARENT)
        self.other_parent = User.objects.create_user("other_parent", password=PASSWORD, role=User.Role.PARENT)
        self.teacher = User.objects.create_user("demo_teacher", password=PASSWORD, role=User.Role.TEACHER)
        self.student_user = User.objects.create_user("demo_student", password=PASSWORD, role=User.Role.STUDENT)

        self.ava = Student.objects.create(
            student_id="S-100", name="Ava Rivera", grade_level=8, user=self.student_user,
            ssn="123-45-6789", home_address="12 Elm St", medical_notes="Peanut allergy",
        )
        self.ava.parents.add(self.parent)
        self.mia = Student.objects.create(student_id="S-200", name="Mia Chen", grade_level=8)
        self.mia.parents.add(self.other_parent)

    def _client_for(self, username):
        client = Client()
        client.login(username=username, password=PASSWORD)
        return client

    def test_parent_lists_only_their_own_children(self):
        response = self._client_for("demo_parent").get(reverse("family_portal:api_children"))
        ids = {c["student_id"] for c in response.json()["children"]}
        self.assertEqual(ids, {"S-100"})

    def test_parent_can_view_own_childs_records(self):
        response = self._client_for("demo_parent").get(
            reverse("family_portal:api_child_records", args=["S-100"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["student"]["name"], "Ava Rivera")

    def test_parent_cannot_view_another_familys_child(self):
        response = self._client_for("demo_parent").get(
            reverse("family_portal:api_child_records", args=["S-200"])
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_and_forbidden_ids_are_indistinguishable(self):
        client = self._client_for("demo_parent")
        forbidden = client.get(reverse("family_portal:api_child_records", args=["S-200"]))
        missing = client.get(reverse("family_portal:api_child_records", args=["S-999"]))
        self.assertEqual(forbidden.status_code, missing.status_code)
        self.assertEqual(forbidden.json(), missing.json())

    def test_sensitive_fields_never_appear_in_api_or_html(self):
        client = self._client_for("demo_parent")
        api_text = client.get(reverse("family_portal:api_child_records", args=["S-100"])).content.decode()
        html_text = client.get(reverse("family_portal:child_records", args=["S-100"])).content.decode()
        for value in SENSITIVE_VALUES:
            self.assertNotIn(value, api_text)
            self.assertNotIn(value, html_text)

    def test_non_parent_roles_cannot_use_parent_portal(self):
        for username in ("demo_teacher", "demo_student"):
            response = self._client_for(username).get(reverse("family_portal:api_children"))
            self.assertEqual(response.status_code, 403)

    def test_unauthenticated_requests_are_rejected(self):
        response = Client().get(reverse("family_portal:api_children"))
        self.assertEqual(response.status_code, 302)


class MessagingTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("demo_teacher", password=PASSWORD, role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user("other_teacher", password=PASSWORD, role=User.Role.TEACHER)
        self.parent = User.objects.create_user("demo_parent", password=PASSWORD, role=User.Role.PARENT)
        self.other_parent = User.objects.create_user("other_parent", password=PASSWORD, role=User.Role.PARENT)

        course = Course.objects.create(name="Math")
        self.section = ClassSection.objects.create(
            course=course, teacher=self.teacher, room="1", day_of_week="MON",
            start_time="09:00", end_time="10:00",
        )
        self.student = Student.objects.create(student_id="S-100", name="Ava Rivera", grade_level=8)
        self.section.students.add(self.student)
        self.student.parents.add(self.parent)

    def _client_for(self, username):
        client = Client()
        client.login(username=username, password=PASSWORD)
        return client

    def _send(self, **overrides):
        payload = {"recipient": str(self.parent.pk), "student_id": str(self.student.pk),
                   "subject": "Math progress", "body": "Ava is doing great."}
        payload.update(overrides)
        import json
        return self._client_for("demo_teacher").post(
            reverse("family_portal:api_send"), data=json.dumps(payload), content_type="application/json"
        )

    def test_teacher_can_message_assigned_students_parent(self):
        response = self._send()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(MessageThread.objects.filter(parent=self.parent, student=self.student).exists())

    def test_teacher_cannot_message_unrelated_parent(self):
        response = self._send(recipient=str(self.other_parent.pk))
        self.assertEqual(response.status_code, 403)

    def test_parent_cannot_start_a_conversation(self):
        response = self._client_for("demo_parent").post(
            reverse("family_portal:api_send"),
            data="{}", content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_parent_can_reply_and_teacher_can_read_it(self):
        thread_id = self._send().json()["thread_id"]
        import json
        reply = self._client_for("demo_parent").post(
            reverse("family_portal:api_reply", args=[thread_id]),
            data=json.dumps({"body": "Thank you!"}), content_type="application/json",
        )
        self.assertEqual(reply.status_code, 201)
        thread = self._client_for("demo_teacher").get(reverse("family_portal:api_thread", args=[thread_id]))
        bodies = [m["body"] for m in thread.json()["messages"]]
        self.assertEqual(bodies, ["Ava is doing great.", "Thank you!"])

    def test_outsiders_cannot_read_a_thread(self):
        thread_id = self._send().json()["thread_id"]
        response = self._client_for("other_parent").get(
            reverse("family_portal:api_thread", args=[thread_id])
        )
        self.assertEqual(response.status_code, 404)

    def test_message_body_is_encrypted_at_rest(self):
        from django.db import connection

        self._send()
        message = Message.objects.first()
        # Same reasoning as accounts/tests.py: .raw() would decrypt the
        # value via from_db_value(), so read the column with a bare cursor.
        with connection.cursor() as cursor:
            cursor.execute("SELECT body FROM family_portal_message WHERE id = %s", [message.pk])
            stored_value = cursor.fetchone()[0]
        self.assertNotIn("great", stored_value)
        self.assertEqual(message.body, "Ava is doing great.")

    def test_output_is_escaped_in_html_thread_view(self):
        thread_id = self._send(body="<script>alert(1)</script>").json()["thread_id"]
        response = self._client_for("demo_parent").get(reverse("family_portal:thread", args=[thread_id]))
        self.assertNotIn("<script>alert(1)</script>", response.content.decode())
        self.assertIn("&lt;script&gt;", response.content.decode())
