from django.contrib import admin
from .models import Area, Address


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "radius_km", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "label", "area", "pincode", "is_default")
    list_filter = ("area",)
    search_fields = ("customer__mobile", "line1", "pincode")
    readonly_fields = ("area",)
