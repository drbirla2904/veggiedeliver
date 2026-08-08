from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTP


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("mobile", "get_full_name", "role", "area", "is_on_duty", "mobile_verified", "created_at")
    list_filter = ("role", "area", "is_on_duty", "mobile_verified")
    search_fields = ("mobile", "first_name", "last_name", "referral_code")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("mobile", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "username", "email")}),
        ("Role & area", {"fields": ("role", "area", "created_by")}),
        ("Referral", {"fields": ("referral_code", "referred_by")}),
        ("Duty status (delivery members)", {
            "fields": ("is_on_duty",),
            "description": "Live GPS position is kept in Redis (see orders/geo_cache.py), not stored here — check the area live map for a rider's current location.",
        }),
        ("Permissions", {"fields": ("is_active", "mobile_verified", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("mobile", "username", "role", "area", "password1", "password2"),
        }),
    )
    readonly_fields = ("referral_code",)

    def get_full_name(self, obj):
        return obj.get_full_name() or "—"
    get_full_name.short_description = "Name"

    def get_queryset(self, request):
        """
        Super admins see everyone. Area admins only see delivery members
        and customers within their own area — this is the core of the
        area-wise admin model.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == User.Role.SUPER_ADMIN:
            return qs
        if request.user.role == User.Role.AREA_ADMIN:
            return qs.filter(area=request.user.area).exclude(role=User.Role.SUPER_ADMIN)
        return qs.none()

    def save_model(self, request, obj, form, change):
        # Area admins can only create delivery members, and only in their own area.
        if not request.user.is_superuser and request.user.role == User.Role.AREA_ADMIN:
            obj.role = User.Role.DELIVERY_MEMBER
            obj.area = request.user.area
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("mobile", "code", "is_used", "attempts", "created_at")
    list_filter = ("is_used",)