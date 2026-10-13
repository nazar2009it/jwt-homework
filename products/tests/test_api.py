from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from rest_framework import status
from users.serializers import LoginSerializer
from rest_framework.test import APITestCase

from products.models import Product
from users.models import User


class ProductPermissionsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        password = "StudyPassword!2026"
        cls.owner = User.objects.create_user("owner@example.com", password, birthdate="2000-01-01")
        cls.other = User.objects.create_user("other@example.com", password, birthdate="2000-01-01")
        cls.moderator = User.objects.create_user("moderator@example.com", password, birthdate="2000-01-01", is_staff=True)
        cls.admin = User.objects.create_superuser("admin@example.com", password, "996700123456")
        cls.tokens = {user.pk: str(LoginSerializer.get_token(user).access_token) for user in (cls.owner, cls.other, cls.moderator, cls.admin)}
        cls.own_product = Product.objects.create(title="Товар владельца", price="10.00", owner=cls.owner)
        cls.other_product = Product.objects.create(title="Чужой товар", price="20.00", owner=cls.other)
        cls.moderator_product = Product.objects.create(title="Товар до назначения модератором", price="30.00", owner=cls.moderator)

    def authenticate(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens[user.pk]}")

    def detail(self, product):
        return reverse("products:product-detail", kwargs={"pk": product.pk})

    def test_guest_cannot_access_products(self):
        list_url = reverse("products:product-list")
        detail_url = self.detail(self.other_product)
        for method, url in (("get", list_url), ("post", list_url), ("get", detail_url), ("put", detail_url), ("patch", detail_url), ("delete", detail_url)):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, {"title": "Изменение", "price": "1.00"}, format="json")
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Product.objects.count(), 3)

    def test_normal_user_lists_only_owned_products(self):
        self.authenticate(self.owner)
        response = self.client.get(reverse("products:product-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in response.data}, {self.own_product.pk})

    def test_normal_user_can_create_product(self):
        self.authenticate(self.owner)
        response = self.client.post(reverse("products:product-list"), {"title": "Новый товар", "price": "50.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["owner"], self.owner.pk)

    def test_client_cannot_assign_another_owner_when_creating(self):
        self.authenticate(self.owner)
        response = self.client.post(reverse("products:product-list"), {"title": "Новый товар", "price": "50.00", "owner": self.other.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.get(pk=response.data["id"]).owner_id, self.owner.pk)

    def test_normal_owner_can_read_replace_patch_and_delete_own_product(self):
        self.authenticate(self.owner)
        url = self.detail(self.own_product)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.put(url, {"title": "Замена", "price": "40.00"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.patch(url, {"title": "Изменение"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=self.own_product.pk).exists())

    def test_normal_user_cannot_read_change_or_delete_foreign_product(self):
        self.authenticate(self.owner)
        for method in ("get", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.detail(self.other_product), {"title": "Чужое изменение", "price": "1.00"}, format="json")
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_product.refresh_from_db()
        self.assertEqual(self.other_product.title, "Чужой товар")

    def test_moderator_can_list_all_products(self):
        self.authenticate(self.moderator)
        response = self.client.get(reverse("products:product-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in response.data}, {self.own_product.pk, self.other_product.pk, self.moderator_product.pk})

    def test_moderator_can_read_foreign_product(self):
        self.authenticate(self.moderator)
        self.assertEqual(self.client.get(self.detail(self.other_product)).status_code, status.HTTP_200_OK)

    def test_moderator_can_put_foreign_product(self):
        self.authenticate(self.moderator)
        response = self.client.put(self.detail(self.other_product), {"title": "Исправленный товар", "price": "100.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.other_product.refresh_from_db()
        self.assertEqual(self.other_product.title, "Исправленный товар")

    def test_moderator_can_patch_foreign_product(self):
        self.authenticate(self.moderator)
        response = self.client.patch(self.detail(self.other_product), {"title": "Исправление"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.other_product.refresh_from_db()
        self.assertEqual(self.other_product.title, "Исправление")

    def test_moderator_cannot_transfer_product_ownership(self):
        self.authenticate(self.moderator)
        response = self.client.patch(self.detail(self.other_product), {"owner": self.moderator.pk, "title": "Исправление"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.other_product.refresh_from_db()
        self.assertEqual(self.other_product.owner_id, self.other.pk)

    def test_moderator_can_delete_foreign_product(self):
        self.authenticate(self.moderator)
        response = self.client.delete(self.detail(self.other_product))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=self.other_product.pk).exists())

    def test_moderator_cannot_post_for_self_or_another_owner(self):
        self.authenticate(self.moderator)
        for owner_id in (self.moderator.pk, self.other.pk):
            with self.subTest(owner_id=owner_id):
                response = self.client.post(reverse("products:product-list"), {"title": "Запрещённый товар", "price": "1.00", "owner": owner_id}, format="json")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Product.objects.count(), 3)

    def test_superuser_follows_same_staff_post_restriction(self):
        self.authenticate(self.admin)
        response = self.client.post(reverse("products:product-list"), {"title": "Запрещённый товар", "price": "1.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Product.objects.count(), 3)

    def test_promotion_to_staff_revokes_post_right_even_for_existing_owner(self):
        self.owner.is_staff = True
        self.owner.save(update_fields=["is_staff"])
        self.authenticate(self.owner)
        response = self.client.post(reverse("products:product-list"), {"title": "Запрещённый товар", "price": "1.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.detail(self.other_product)).status_code, status.HTTP_200_OK)

    def test_head_and_options_work_for_moderator(self):
        self.authenticate(self.moderator)
        url = reverse("products:product-list")
        self.assertEqual(self.client.head(url).status_code, status.HTTP_200_OK)
        response = self.client.options(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("POST", response.data.get("actions", {}))

    def test_schema_contains_product_crud_endpoints(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        self.assertTrue({"get", "post"} <= set(schema["paths"]["/api/v1/products/"]))
        self.assertTrue({"get", "put", "patch", "delete"} <= set(schema["paths"]["/api/v1/products/{id}/"]))
