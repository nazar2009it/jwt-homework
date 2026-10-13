from types import SimpleNamespace

from django.test import SimpleTestCase

from products.permissions import IsModerator, IsProductOwner


class ModeratorPermissionTests(SimpleTestCase):
    def request(self, method, authenticated=True, staff=True):
        return SimpleNamespace(
            method=method,
            user=SimpleNamespace(is_authenticated=authenticated, is_staff=staff, pk=1),
        )

    def test_moderator_can_read_change_and_delete_foreign_product(self):
        permission = IsModerator()
        product = SimpleNamespace(owner_id=2)
        for method in ("GET", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                request = self.request(method)
                self.assertTrue(permission.has_permission(request, None))
                self.assertTrue(permission.has_object_permission(request, None, product))

    def test_moderator_post_is_rejected(self):
        permission = IsModerator()
        request = self.request("POST")
        self.assertFalse(permission.has_permission(request, None))
        self.assertFalse(permission.has_object_permission(request, None, SimpleNamespace(owner_id=1)))

    def test_staff_and_authentication_are_both_required(self):
        for authenticated, staff in ((False, False), (False, True), (True, False)):
            with self.subTest(authenticated=authenticated, staff=staff):
                self.assertFalse(IsModerator().has_permission(self.request("GET", authenticated, staff), None))

    def test_staff_cannot_use_owner_permission_to_bypass_post_ban(self):
        request = self.request("POST")
        self.assertFalse(IsProductOwner().has_permission(request, None))
        self.assertFalse((IsModerator | IsProductOwner)().has_permission(request, None))
