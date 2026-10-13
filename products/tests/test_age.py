import base64
import json
from datetime import date
from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from products.models import Product
from users.models import User
from users.serializers import LoginSerializer

PASSWORD = "StudyPassword!2026"
MINOR_MESSAGE = "Вам должно быть 18 лет, чтобы создать продукт."
MISSING_MESSAGE = "Укажите дату рождения, чтобы создать продукт."


class ProductAgeTests(APITestCase):
    def setUp(self):
        clock = patch("common.validators.timezone.localdate", return_value=date(2026, 10, 13))
        clock.start()
        self.addCleanup(clock.stop)
        self.user = User.objects.create_user("student@example.com", PASSWORD)
        self.url = reverse("products:product-list")
        self.product_data = {"title": "Учебник", "price": "100.00"}

    def authenticate(self, birthdate):
        self.user.birthdate = date.fromisoformat(birthdate) if birthdate else None
        self.user.save(update_fields=["birthdate"])
        token = LoginSerializer.get_token(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return token

    def create(self, **extra):
        return self.client.post(self.url, {**self.product_data, **extra}, format="json")

    def assert_rejected(self, response, message):
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(str(response.data["birthdate"]), message)
        self.assertFalse(Product.objects.exists())

    def test_adult_can_create_product(self):
        self.authenticate("2000-01-01")
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Product.objects.get().owner, self.user)

    def test_exactly_eighteen_can_create_product(self):
        self.authenticate("2008-10-13")
        self.assertEqual(self.create().status_code, 201)

    def test_one_day_before_eighteen_cannot_create(self):
        self.authenticate("2008-10-14")
        self.assert_rejected(self.create(), MINOR_MESSAGE)

    def test_null_birthdate_cannot_create(self):
        self.authenticate(None)
        self.assert_rejected(self.create(), MISSING_MESSAGE)

    def test_absent_birthdate_claim_is_rejected_even_if_database_has_date(self):
        token = self.authenticate("2000-01-01")
        del token["birthdate"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assert_rejected(self.create(), MISSING_MESSAGE)

    def test_empty_birthdate_claim_is_rejected(self):
        token = self.authenticate("2000-01-01")
        token["birthdate"] = ""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assert_rejected(self.create(), MISSING_MESSAGE)

    def test_age_comes_from_token_even_after_database_changes_to_adult(self):
        self.authenticate("2010-01-01")
        self.user.birthdate = date(2000, 1, 1)
        self.user.save(update_fields=["birthdate"])
        self.assert_rejected(self.create(), MINOR_MESSAGE)

    def test_adult_token_is_used_even_after_database_changes_to_minor(self):
        self.authenticate("2000-01-01")
        self.user.birthdate = date(2010, 1, 1)
        self.user.save(update_fields=["birthdate"])
        self.assertEqual(self.create().status_code, 201)

    def test_birthdate_in_product_body_cannot_bypass_age_check(self):
        self.authenticate("2010-01-01")
        self.assert_rejected(self.create(birthdate="1980-01-01"), MINOR_MESSAGE)

    def test_malformed_signed_claim_is_rejected(self):
        token = self.authenticate("2000-01-01")
        token["birthdate"] = "2000-02-30"
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assert_rejected(self.create(), "Некорректная дата рождения в токене.")

    def test_unsigned_payload_change_is_rejected_by_jwt_authentication(self):
        token = self.authenticate("2010-01-01")
        header, payload, signature = str(token).split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        claims["birthdate"] = "1980-01-01"
        changed = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {header}.{changed}.{signature}")
        self.assertEqual(self.create().status_code, 401)
        self.assertFalse(Product.objects.exists())

    def test_age_check_does_not_block_other_crud_methods(self):
        for birthdate in (None, "2010-01-01"):
            with self.subTest(birthdate=birthdate):
                self.authenticate(birthdate)
                product = Product.objects.create(title="Старый товар", price="10.00", owner=self.user)
                url = reverse("products:product-detail", kwargs={"pk": product.pk})
                self.assertEqual(self.client.get(self.url).status_code, 200)
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.put(url, self.product_data, format="json").status_code, 200)
                self.assertEqual(self.client.patch(url, {"title": "Изменение"}, format="json").status_code, 200)
                self.assertEqual(self.client.delete(url).status_code, 204)

    def test_new_login_after_birthdate_edit_issues_updated_claim(self):
        self.authenticate(None)
        self.assert_rejected(self.create(), MISSING_MESSAGE)
        self.user.birthdate = date(2000, 1, 1)
        self.user.save(update_fields=["birthdate"])
        response = self.client.post(reverse("users:login"), {
            "email": self.user.email, "password": PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.create().status_code, 201)
