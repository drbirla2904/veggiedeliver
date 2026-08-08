from decimal import Decimal

from django.db import models
from django.conf import settings


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed", "Placed"
        CONFIRMED = "confirmed", "Confirmed"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery"
        ONLINE = "online", "Online (Razorpay)"
        WALLET = "wallet", "Wallet"

    class DeliverySpeed(models.TextChoices):
        INSTANT = "instant", "Instant"
        THREE_TO_FOUR_HOURS = "3_4_hours", "3-4 hours"
        NEXT_DAY = "next_day", "Next day"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    address = models.ForeignKey(
        "locations.Address", on_delete=models.PROTECT, related_name="orders"
    )
    # Copied from address.area at placement time so an order stays put
    # even if area boundaries are edited later.
    area = models.ForeignKey(
        "locations.Area", on_delete=models.PROTECT, related_name="orders"
    )

    delivery_member = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="deliveries",
        limit_choices_to={"role": "delivery_member"},
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    delivery_speed = models.CharField(max_length=20, choices=DeliverySpeed.choices, default=DeliverySpeed.INSTANT)
    delivery_bonus = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    items_total = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    wallet_amount_used = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=9, decimal_places=2, default=0)

    placed_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-placed_at"]

    def __str__(self):
        return f"Order #{self.id} — {self.customer} ({self.get_status_display()})"

    def recalculate_total(self):
        self.items_total = sum(i.line_total for i in self.items.all())
        self.grand_total = self.items_total + self.delivery_fee - self.wallet_amount_used
        self.save(update_fields=["items_total", "grand_total"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, help_text="Price at time of order")

    @property
    def line_total(self):
        if self.unit_price is None:
            return Decimal('0.00')
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.variant}"


class DeliveryLocationPing(models.Model):
    """
    Live GPS pings from the delivery member's app while an order is
    out for delivery — powers the 'track my order on map' view.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="location_pings")
    latitude = models.FloatField()
    longitude = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
