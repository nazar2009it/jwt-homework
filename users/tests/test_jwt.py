from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from users.models import User
from users.serializers import LoginSerializer

PASSWORD = "StudyPassword!2026"


class JWTTests(APITestCase):
    def register(self, **extra):
        return self.client.post(reverse("users:register"), {
            "email": "student@example.com",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            **extra,
        }, format="json")

    def test_registration_puts_birthdate_in_both_tokens(self):
        response = self.register(birthdate="2000-01-02")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["user"]["birthdate"], "2000-01-02")
        self.assertEqual(User.objects.get().birthdate.isoformat(), "2000-01-02")
        self.assertEqual(AccessToken(response.data["access"])["birthdate"], "2000-01-02")
        self.assertEqual(RefreshToken(response.data["refresh"])["birthdate"], "2000-01-02")

    def test_login_puts_existing_birthdate_in_both_tokens(self):
        user = User.objects.create_user("student@example.com", PASSWORD, birthdate="2000-01-02")
        response = self.client.post(reverse("users:login"), {
            "email": user.email, "password": PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        for name, token_class in (("access", AccessToken), ("refresh", RefreshToken)):
            self.assertEqual(token_class(response.data[name])["birthdate"], "2000-01-02")

    def test_null_birthdate_is_allowed_at_registration(self):
        response = self.register(birthdate=None)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(AccessToken(response.data["access"])["birthdate"])

    def test_registration_rejects_future_birthdate(self):
        birthday = (timezone.localdate() + timedelta(days=1)).isoformat()
        response = self.register(birthdate=birthday)
        self.assertEqual(response.status_code, 400)
        self.assertIn("birthdate", response.data)
        self.assertFalse(User.objects.exists())

    def test_registration_rejects_invalid_birthdate(self):
        response = self.register(birthdate="2000-02-30")
        self.assertEqual(response.status_code, 400)
        self.assertIn("birthdate", response.data)

    def test_refresh_retains_birthdate_and_authenticates(self):
        registered = self.register(birthdate="2000-01-02")
        response = self.client.post(reverse("users:token-refresh"), {
            "refresh": registered.data["refresh"],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(AccessToken(response.data["access"])["birthdate"], "2000-01-02")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.get(reverse("users:me")).status_code, 200)

    def test_access_token_cannot_be_used_to_refresh(self):
        registered = self.register()
        response = self.client.post(reverse("users:token-refresh"), {
            "refresh": registered.data["access"],
        }, format="json")
        self.assertEqual(response.status_code, 401)

    def test_refresh_token_cannot_authenticate_api(self):
        registered = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {registered.data['refresh']}")
        self.assertEqual(self.client.get(reverse("users:me")).status_code, 401)

    def test_expired_access_token_is_rejected(self):
        user = User.objects.create_user("student@example.com", PASSWORD)
        token = LoginSerializer.get_token(user).access_token
        token.set_exp(lifetime=timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get(reverse("users:me")).status_code, 401)

    def test_old_token_header_scheme_is_rejected(self):
        registered = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {registered.data['access']}")
        self.assertEqual(self.client.get(reverse("users:me")).status_code, 401)

    def test_birthdate_cannot_be_changed_through_me(self):
        registered = self.register(birthdate="2000-01-02")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {registered.data['access']}")
        response = self.client.patch(reverse("users:me"), {"birthdate": "1980-01-01"}, format="json")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(User.objects.get().birthdate.isoformat(), "2000-01-02")
