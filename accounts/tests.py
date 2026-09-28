"""UMA-002 tests: password complexity, login, lockout, registration.

Covers the same ground as the original Flask tests/test_validators.py and
tests/test_auth.py, plus TaskID11's FastAPI login tests (successful login,
wrong password, unknown user, missing fields, password hashing) -- now
exercised against the real Django auth stack instead of a stub JWT.
"""
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .validators import ComplexityValidator

User = get_user_model()
PASSWORD = "C0rrectHorse!Battery"


class ComplexityValidatorTests(TestCase):
    def setUp(self):
        self.validator = ComplexityValidator(min_length=10)

    def test_strong_password_passes(self):
        self.validator.validate(PASSWORD)  # should not raise

    def test_too_short_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("Ab1!")
        self.assertTrue(any("10 characters" in m for m in ctx.exception.messages))

    def test_missing_uppercase_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("lowercase1!lowercase")
        self.assertTrue(any("uppercase" in m for m in ctx.exception.messages))

    def test_missing_special_char_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("NoSpecialChar1234")
        self.assertTrue(any("special character" in m for m in ctx.exception.messages))

    def test_common_password_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("welcome1")
        self.assertTrue(any("common" in m for m in ctx.exception.messages))

    def test_whitespace_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("Val1d Pass!word")
        self.assertTrue(any("whitespace" in m for m in ctx.exception.messages))


class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("alex", password=PASSWORD, role=User.Role.TEACHER)
        self.client = Client()

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_successful_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {"username": "alex", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_wrong_password_rejected(self):
        response = self.client.post(reverse("accounts:login"), {"username": "alex", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")

    def test_unknown_username_rejected(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "nobody", "password": PASSWORD}
        )
        self.assertContains(response, "Invalid username or password.")

    def test_missing_fields_rejected(self):
        response = self.client.post(reverse("accounts:login"), {"username": "alex"})
        self.assertContains(response, "required")

    def test_password_is_hashed_not_stored_plaintext(self):
        self.assertNotEqual(self.user.password, PASSWORD)
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_lockout_after_max_failed_attempts(self):
        from django.conf import settings

        for _ in range(settings.MAX_FAILED_ATTEMPTS):
            self.client.post(reverse("accounts:login"), {"username": "alex", "password": "wrong"})
        response = self.client.post(
            reverse("accounts:login"), {"username": "alex", "password": PASSWORD}
        )
        self.assertContains(response, "temporarily locked")

    def test_logout_requires_post_and_clears_session(self):
        self.client.login(username="alex", password=PASSWORD)
        self.client.post(reverse("accounts:logout"))
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertNotEqual(response.status_code, 200)  # redirected to login


class ApiAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user("demo_teacher", password=PASSWORD, role=User.Role.TEACHER)
        self.client = Client()

    def test_api_login_success(self):
        response = self.client.post(
            reverse("accounts:api_login"),
            data=json.dumps({"username": "demo_teacher", "password": PASSWORD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_api_login_wrong_password(self):
        response = self.client.post(
            reverse("accounts:api_login"),
            data=json.dumps({"username": "demo_teacher", "password": "nope"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_register_rejects_weak_password(self):
        response = self.client.post(
            reverse("accounts:api_register"),
            data=json.dumps({"username": "new_user", "password": "weak"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())

    def test_api_register_accepts_strong_password(self):
        response = self.client.post(
            reverse("accounts:api_register"),
            data=json.dumps({"username": "brand_new_user", "password": PASSWORD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="brand_new_user").exists())

    def test_api_register_rejects_duplicate_username(self):
        response = self.client.post(
            reverse("accounts:api_register"),
            data=json.dumps({"username": "demo_teacher", "password": PASSWORD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)


class EncryptedFieldTests(TestCase):
    def test_phone_number_is_encrypted_at_rest(self):
        from django.db import connection

        user = User.objects.create_user("has_phone", password=PASSWORD, phone_number="555-0100")
        # .raw() would run the field's from_db_value() and decrypt it right
        # back, defeating the point of this test -- go around the ORM
        # entirely with a plain cursor to see what's actually on disk.
        with connection.cursor() as cursor:
            cursor.execute("SELECT phone_number FROM accounts_user WHERE id = %s", [user.pk])
            stored_value = cursor.fetchone()[0]
        self.assertNotEqual(stored_value, "555-0100")
        user.refresh_from_db()
        self.assertEqual(user.phone_number, "555-0100")
