from decimal import Decimal
from django.db import models
from django.conf import settings


class Wallet(models.Model):
    """
    One wallet per user. Balance is ONLY ever credited by referral bonuses
    (never top-up by the user), and can be spent against an order total.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.user} — ₹{self.balance}"

    def credit(self, amount, reason, related_order=None):
        self.balance += amount
        self.save(update_fields=["balance"])
        WalletTransaction.objects.create(
            wallet=self, type=WalletTransaction.Type.CREDIT,
            amount=amount, reason=reason, related_order=related_order,
        )

    def debit(self, amount, reason, related_order=None):
        if amount > self.balance:
            raise ValueError("Insufficient wallet balance.")
        self.balance -= amount
        self.save(update_fields=["balance"])
        WalletTransaction.objects.create(
            wallet=self, type=WalletTransaction.Type.DEBIT,
            amount=amount, reason=reason, related_order=related_order,
        )


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Reason(models.TextChoices):
        REFERRAL_BONUS = "referral_bonus", "Referral Bonus"
        ORDER_PAYMENT = "order_payment", "Used on Order"
        DELIVERY_BONUS = "delivery_bonus", "Delivery Bonus"
        ADJUSTMENT = "adjustment", "Manual Adjustment"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=10, choices=Type.choices)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    reason = models.CharField(max_length=20, choices=Reason.choices)
    related_order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="wallet_transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.type == self.Type.CREDIT else "-"
        return f"{sign}₹{self.amount} ({self.get_reason_display()})"


class ReferralSettings(models.Model):
    """
    Singleton row admin edits to control the referral bonus —
    avoids hardcoding the amount in code.
    """
    bonus_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("50.00"),
        help_text="Fixed rupee amount credited once when a referred customer's first order is delivered."
    )
    min_order_value_for_bonus = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("99.00"))
    max_wallet_usage_percent = models.DecimalField(
        max_digits=4, decimal_places=1, default=Decimal("50.0"),
        help_text="Max % of an order's value that can be paid from wallet balance."
    )

    class Meta:
        verbose_name = "Referral Settings"
        verbose_name_plural = "Referral Settings"

    def __str__(self):
        return "Referral Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
