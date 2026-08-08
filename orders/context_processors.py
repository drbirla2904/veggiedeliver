from .cart import Cart


def cart_count(request):
    return {"cart_count": Cart(request).count()}
