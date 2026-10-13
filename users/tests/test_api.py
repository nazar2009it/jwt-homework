from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework.test import APITestCase
from users.models import User

PASSWORD = "StudyPassword!2026"


class AuthenticationTests(APITestCase):
    def registration_data(self, **extra):
        return {
            "email": "student@example.com",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            **extra,
        }

    def register(self, **extra):
        return self.client.post(reverse("users:register"), self.registration_data(**extra), format="json")

    def test_registration_without_phone_returns_token_and_safe_user_data(self):
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["user"]["phone_number"], "")
        self.assertNotIn("password", response.data["user"])
        self.assertNotIn("password_confirm", response.data["user"])
        token = AccessToken(response.data["access"])
        user = User.objects.get(pk=token["user_id"])
        self.assertEqual(user.email, "student@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertIsNone(token["birthdate"])
        self.assertIsNone(RefreshToken(response.data["refresh"])["birthdate"])

    def test_registration_with_valid_phone(self):
        response = self.register(phone_number="996700123456")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["user"]["phone_number"], "+996700123456")

    def test_registration_with_blank_phone(self):
        self.assertEqual(self.register(phone_number="").status_code, status.HTTP_201_CREATED)

    def test_invalid_phone_is_rejected_without_creating_user(self):
        for phone in ("+77001234567", "996", "+99670012345", "+996abcdefghi", None):
            with self.subTest(phone=phone):
                response = self.register(phone_number=phone)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("phone_number", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_password_confirmation_must_match(self):
        response = self.register(password_confirm="DifferentPassword!2026")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_weak_password_is_rejected(self):
        response = self.register(password="123", password_confirm="123")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_requires_email_and_password_fields(self):
        response = self.client.post(reverse("users:register"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue({"email", "password", "password_confirm"} <= set(response.data))

    def test_duplicate_email_is_rejected_regardless_of_case(self):
        self.register()
        response = self.register(email="STUDENT@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_public_registration_cannot_grant_admin_permissions(self):
        response = self.register(is_superuser=True, is_staff=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get()
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_login_uses_email_and_returns_new_jwt_pair(self):
        registered = self.register()
        response = self.client.post(reverse("users:login"), {
            "email": "STUDENT@EXAMPLE.COM", "password": PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotEqual(response.data["access"], registered.data["access"])
        self.assertEqual(str(AccessToken(response.data["access"])["user_id"]), str(registered.data["user"]["id"]))
        self.assertNotIn("password", response.data["user"])

    def test_wrong_credentials_are_rejected(self):
        self.register()
        for email, password in (("student@example.com", "wrong"), ("missing@example.com", PASSWORD)):
            with self.subTest(email=email):
                response = self.client.post(reverse("users:login"), {
                    "email": email, "password": password,
                }, format="json")
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_log_in(self):
        User.objects.create_user("student@example.com", PASSWORD, is_active=False)
        response = self.client.post(reverse("users:login"), {
            "email": "student@example.com", "password": PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get(reverse("users:me")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_authenticates_me_request(self):
        registered = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {registered.data['access']}")
        response = self.client.get(reverse("users:me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "student@example.com")

    def test_swagger_schema_and_static_assets_are_available(self):
        self.assertEqual(self.client.get("/swagger/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/api/schema/").status_code, status.HTTP_200_OK)
        from django.contrib.staticfiles import finders
        self.assertIsNotNone(finders.find("drf_spectacular_sidecar/swagger-ui-dist/swagger-ui-bundle.js"))

    def test_schema_describes_registration_and_login_json_fields(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        schemas = schema["components"]["schemas"]
        for path, expected in (
            ("/api/v1/auth/register/", {"email", "password", "password_confirm"}),
            ("/api/v1/auth/login/", {"email", "password"}),
        ):
            body = schema["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]
            component = schemas[body["$ref"].rsplit("/", 1)[-1]]
            self.assertTrue(expected <= set(component["required"]))
            self.assertNotIn("phone_number", component["required"])
            self.assertTrue(component["properties"]["password"]["writeOnly"])

    def test_admin_accepts_email_login_and_user_pages_render(self):
        User.objects.create_superuser("admin@example.com", PASSWORD, "996700123456")
        self.assertTrue(self.client.login(username="admin@example.com", password=PASSWORD))
        for url in ("/admin/users/user/", "/admin/users/user/add/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
