from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from users.forms import UserCreationForm
from users.models import User

PASSWORD = "StudyPassword!2026"


class UserManagerTests(TestCase):
    def test_normal_user_can_omit_phone_and_password_is_hashed(self):
        user = User.objects.create_user(" Student@Example.COM ", PASSWORD)
        self.assertEqual(user.email, "student@example.com")
        self.assertEqual(user.phone_number, "")
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_email_is_required(self):
        for email in (None, "", "   "):
            with self.subTest(email=email), self.assertRaises(ValueError):
                User.objects.create_user(email, PASSWORD)

    def test_invalid_email_is_rejected(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user("not-an-email", PASSWORD)

    def test_duplicate_email_with_different_case_is_rejected(self):
        User.objects.create_user("student@example.com", PASSWORD)
        with self.assertRaises(ValidationError):
            User.objects.create_user("STUDENT@example.com", PASSWORD)

    def test_phone_is_normalized(self):
        user = User.objects.create_user("student@example.com", PASSWORD, "996700123456")
        self.assertEqual(user.phone_number, "+996700123456")

    def test_supplied_phone_must_have_correct_prefix_and_length(self):
        for phone in ("+77001234567", "996", "+99670012345", "+9967001234567", "+996abcdefghi"):
            with self.subTest(phone=phone), self.assertRaises(ValidationError):
                User.objects.create_user("student@example.com", PASSWORD, phone)

    def test_superuser_requires_phone(self):
        for phone in (None, "", "   "):
            with self.subTest(phone=phone), self.assertRaises(ValueError):
                User.objects.create_superuser("admin@example.com", PASSWORD, phone)

    def test_superuser_is_created_with_correct_flags(self):
        user = User.objects.create_superuser("admin@example.com", PASSWORD, "996700123456")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.phone_number, "+996700123456")
        self.assertTrue(user.check_password(PASSWORD))

    def test_superuser_cannot_have_false_permission_flags(self):
        for flags in ({"is_staff": False}, {"is_superuser": False}):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                User.objects.create_superuser("admin@example.com", PASSWORD, "996700123456", **flags)

    def test_model_validation_requires_phone_only_for_superuser(self):
        user = User(email="student@example.com")
        user.clean()
        user.is_superuser = True
        with self.assertRaises(ValidationError):
            user.clean()

    def test_database_rejects_superuser_without_phone(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="admin@example.com", is_superuser=True)

    def test_admin_creation_form_hashes_password_and_accepts_no_phone(self):
        form = UserCreationForm(data={
            "email": "Student@Example.com",
            "phone_number": "",
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "student@example.com")
        self.assertTrue(user.check_password(PASSWORD))


