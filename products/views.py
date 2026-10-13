from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.validators import validate_product_age

from .models import Product
from .permissions import IsModerator, IsProductOwner
from .serializers import ProductSerializer


@extend_schema(tags=["Товары"])
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.select_related("owner").all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsModerator | IsProductOwner]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()

        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_staff:
            return queryset
        # Ограничиваем и список, и поиск отдельного товара.
        return queryset.filter(owner=user)

    def perform_create(self, serializer):
        birthdate = self.request.auth.get("birthdate") if self.request.auth else None
        validate_product_age(birthdate)
        serializer.save(owner=self.request.user)
