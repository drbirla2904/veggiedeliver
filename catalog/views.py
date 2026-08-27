from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Category, Product, ProductVariant
from orders.cart import Cart


def home(request):
    categories = Category.objects.filter(is_active=True)
    selected_id = request.GET.get("category")
    products = Product.objects.filter(is_active=True).prefetch_related("variants")
    if selected_id:
        products = products.filter(category_id=selected_id)

    # Cheapest active variant per product, for the card price
    product_cards = []
    for p in products:
        variant = p.variants.filter(is_active=True).order_by("price").first()
        if variant:
            product_cards.append((p, variant))

    return render(request, "catalog/home.html", {
        "categories": categories,
        "selected_id": int(selected_id) if selected_id else None,
        "product_cards": product_cards,
        "cart_count": Cart(request).count(),
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    variants = product.variants.filter(is_active=True)
    related_products = []
    related_queryset = Product.objects.filter(
        category=product.category,
        is_active=True,
    ).exclude(pk=product.pk).prefetch_related("variants")
    for related_product in related_queryset:
        variant = related_product.variants.filter(is_active=True).order_by("price").first()
        if variant:
            related_products.append((related_product, variant))

    # Keep the section useful even when this category has no sibling products.
    if not related_products:
        fallback_queryset = Product.objects.filter(
            is_active=True,
        ).exclude(pk=product.pk).exclude(category=product.category).prefetch_related("variants")[:4]
        for related_product in fallback_queryset:
            variant = related_product.variants.filter(is_active=True).order_by("price").first()
            if variant:
                related_products.append((related_product, variant))

    return render(request, "catalog/product_detail.html", {
        "product": product, "variants": variants,
        "related_products": related_products,
        "cart_count": Cart(request).count(),
    })
