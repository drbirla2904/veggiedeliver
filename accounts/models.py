import random
import string
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


mobile_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message="Enter a valid 10-digit Indian mobile number."
)


def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class User(AbstractUser):
    """
    Single custom user model for every role in the system.
    username is kept (Django needs it internally) but login happens via mobile number.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        AREA_ADMIN = "area_admin", "Area Admin"
        DELIVERY_MEMBER = "delivery_member", "Delivery Member"
        CUSTOMER = "customer", "Customer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    mobile = models.CharField(max_length=10, unique=True, validators=[mobile_validator])
    mobile_verified = models.BooleanField(default=False)

    # Area assignment — meaningful for AREA_ADMIN and DELIVERY_MEMBER.
    # A super_admin creates area_admins; an area_admin creates delivery_members
    # scoped to their own area (enforced in admin.py / views, not here).
    area = models.ForeignKey(
        "locations.Area", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="staff"
    )

    # Referral system
    referral_code = models.CharField(max_length=8, unique=True, default=generate_referral_code)
    referred_by = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="referrals"
    )

    created_by = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_users",
        help_text="Which admin/area-admin created this account (null for self-registered customers)."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Live status — meaningful for DELIVERY_MEMBER, drives nearest-rider assignment.
    is_on_duty = models.BooleanField(default=False)
    last_latitude = models.FloatField(null=True, blank=True)
    last_longitude = models.FloatField(null=True, blank=True)
    last_location_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.mobile} ({self.get_role_display()})"

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_delivery_member(self):
        return self.role == self.Role.DELIVERY_MEMBER

    @property
    def is_area_admin(self):
        return self.role == self.Role.AREA_ADMIN


class OTP(models.Model):
    """
    Mobile-number OTP for login/registration. Plug an SMS gateway
    (e.g. MSG91, Twilio) into send_otp() in accounts/services.py.
    """
    mobile = models.CharField(max_length=10, validators=[mobile_validator])
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(
        default=0, help_text="Failed verification attempts against this code."
    )

    class Meta:
        indexes = [models.Index(fields=["mobile", "code"])]

    def __str__(self):
        return f"OTP {self.code} for {self.mobile}"