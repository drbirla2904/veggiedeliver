from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Address
from .utils import find_area_for_point


@receiver(pre_save, sender=Address)
def assign_area_to_address(sender, instance, **kwargs):
    """Auto-detect which delivery area an address falls in, from its pin."""
    if instance.latitude is not None and instance.longitude is not None:
        instance.area = find_area_for_point(instance.latitude, instance.longitude)
