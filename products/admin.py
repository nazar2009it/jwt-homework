from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "owner", "created_at")
    search_fields = ("title", "owner__email")
    readonly_fields = ("owner", "created_at")

    def has_add_permission(self, request):
        # Создание выполняет обычный пользователь через API.
        return False
