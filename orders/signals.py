from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from .notifications import notify_customer, notify_area_admin, notify_delivery_member


def credit_delivery_bonus_if_due(order):
    from wallet.models import WalletTransaction

    if order.delivery_bonus <= 0:
        return

    already_credited = order.customer.wallet.transactions.filter(
        reason=WalletTransaction.Reason.DELIVERY_BONUS,
        related_order=order,
    ).exists()
    if already_credited:
        return

    order.customer.wallet.credit(
        amount=order.delivery_bonus,
        reason=WalletTransaction.Reason.DELIVERY_BONUS,
        related_order=order,
    )


@receiver(pre_save, sender=Order)
def cache_order_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
    else:
        instance._previous_status = None


@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    # For newly created orders, we notify only after totals and wallet usage
    # are finalized in the checkout flow.
    if created:
        return

    if not kwargs.get('raw', False):
        previous_status = getattr(instance, '_previous_status', None)
        if previous_status != instance.status:
            if instance.status == Order.Status.DELIVERED:
                credit_delivery_bonus_if_due(instance)
            notify_customer(instance, instance.status)
            notify_area_admin(instance, instance.status)
            notify_delivery_member(instance, instance.status)
