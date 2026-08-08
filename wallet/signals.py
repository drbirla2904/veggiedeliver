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
    Every time an order flips to 'delivered', if the customer was referred,
    credit the referrer's wallet with a % of that order's value.
    Runs on every purchase by the referred user, not just their first.
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

    # Guard against double-crediting if this save fires again for the same order.
    already_credited = referrer.wallet.transactions.filter(
        reason="referral_bonus", related_order=instance
    ).exists()
    if already_credited:
        return

    bonus = (instance.items_total * settings_row.bonus_percent / 100).quantize(instance.items_total)
    referrer.wallet.credit(
        amount=bonus,
        reason="referral_bonus",
        related_order=instance,
    )
