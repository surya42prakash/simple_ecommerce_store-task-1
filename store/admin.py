from django.contrib import admin

from .models import Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active", "is_featured", "updated_at")
    list_editable = ("price", "stock", "is_active", "is_featured")
    list_filter = ("is_active", "is_featured", "category")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 25


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "unit_price", "quantity", "line_subtotal", "product")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Staff may change only the status; historical data stays untouched."""

    list_display = ("order_number", "user", "customer_name", "total", "status", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("order_number", "customer_name", "email", "phone", "user__username")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = (
        "order_number", "user", "customer_name", "email", "phone", "address",
        "city", "state", "postal_code", "total", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "unit_price", "quantity", "line_subtotal")
    search_fields = ("order__order_number", "product_name")
    readonly_fields = ("order", "product", "product_name", "unit_price", "quantity", "line_subtotal")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
