from .cart import Cart


def cart_count(request):
    delivery_area = None
    if request.user.is_authenticated and request.user.is_customer:
        address = request.user.addresses.filter(
            is_default=True, area__isnull=False
        ).select_related("area").first()
        if address is None:
            address = request.user.addresses.filter(
                area__isnull=False
            ).select_related("area").first()
        if address:
            delivery_area = address.area

    return {
        "cart_count": Cart(request).count(),
        "delivery_area": delivery_area,
    }
