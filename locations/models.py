from django.db import models


class Area(models.Model):
    """
    A delivery zone (e.g. 'Kolar Road', 'MP Nagar'). Orders, area-admins and
    delivery members are all scoped to an Area. Keeping this as a simple
    named zone + optional polygon/radius means you don't need PostGIS to
    launch — upgrade to a GeoDjango polygon field later if zones get complex.
    """
    name = models.CharField(max_length=100, unique=True)
    city = models.CharField(max_length=100, default="Bhopal")

    # Center point + radius is enough to auto-detect "which area is this order in"
    # without full polygon geometry. lat/lng in decimal degrees.
    center_lat = models.FloatField()
    center_lng = models.FloatField()
    radius_km = models.FloatField(default=3.0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.city}"


class Address(models.Model):
    """A customer's saved delivery address, pinned on the map."""
    customer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="addresses"
    )
    label = models.CharField(max_length=30, default="Home")  # Home / Work / Other
    line1 = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)
    pincode = models.CharField(max_length=6, blank=True)

    latitude = models.FloatField()
    longitude = models.FloatField()

    # Auto-assigned on save by matching against Area centers — see signals.py
    area = models.ForeignKey(
        Area, null=True, blank=True, on_delete=models.SET_NULL, related_name="addresses"
    )

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} — {self.customer}"
