from django.contrib import admin
from .models import Order, OrderItem, DeliveryLocationPing
from accounts.models import User


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("line_total",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "area", "status", "delivery_member", "grand_total", "placed_at")
    list_filter = ("status", "area", "payment_method")
    search_fields = ("customer__mobile", "id")
    inlines = [OrderItemInline]
    autocomplete_fields = ["customer", "address", "delivery_member"]

    def get_queryset(self, request):
        """Area admins only see orders placed within their own area."""
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == User.Role.SUPER_ADMIN:
            return qs
        if request.user.role == User.Role.AREA_ADMIN:
            return qs.filter(area=request.user.area)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Area admins can only assign delivery members from their own area.
        if db_field.name == "delivery_member" and not request.user.is_superuser:
            kwargs["queryset"] = User.objects.filter(
                role=User.Role.DELIVERY_MEMBER, area=request.user.area
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(DeliveryLocationPing)
