from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "title", "description", "price", "owner", "created_at")
        # Владелец назначается сервером, а не из данных клиента.
        read_only_fields = ("id", "owner", "created_at")
