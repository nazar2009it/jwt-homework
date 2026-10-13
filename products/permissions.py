from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsModerator(BasePermission):
    """Сотрудник может читать, изменять и удалять товары. POST запрещён."""

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.is_staff
            and request.method in SAFE_METHODS + ("PUT", "PATCH", "DELETE")
        )

    def has_object_permission(self, request, view, obj):
        # Владение товаром не требуется: модератор работает и с чужими товарами.
        return self.has_permission(request, view)


class IsProductOwner(BasePermission):
    """Обычный пользователь создаёт товары и управляет только своими."""

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and not request.user.is_staff
            and request.method in SAFE_METHODS + ("POST", "PUT", "PATCH", "DELETE")
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view) and obj.owner_id == request.user.pk
