from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from accounts.models import User
from orders.models import Order
from .models import Wallet, ReferralSettings


@receiver(post_save, sender=User)
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance)


@receiver(post_save, sender=Order)
def credit_referrer_on_delivery(sender, instance, created, **kwargs):
    """
    Credit a fixed referral bonus when a referred customer's first qualifying
    order is delivered.
    """
    if created or instance.status != Order.Status.DELIVERED:
        return

    customer = instance.customer
    referrer = customer.referred_by
    if referrer is None:
        return

    settings_row = ReferralSettings.load()
    if instance.items_total < settings_row.min_order_value_for_bonus:
        return

    # Check all delivered referral rewards for this customer, not just this order.
    already_credited = referrer.wallet.transactions.filter(
        reason="referral_bonus", related_order__customer=customer
    ).exists()
    if already_credited:
        return

    referrer.wallet.credit(
        amount=settings_row.bonus_amount,
        reason="referral_bonus",
        related_order=instance,
    )
