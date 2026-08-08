from django.db import models


class Category(models.Model):
    """e.g. Leafy Greens, Root Vegetables, Exotic. Admin-managed."""
    name = models.CharField(max_length=100, unique=True)
    icon_emoji = models.CharField(max_length=8, blank=True, help_text="e.g. 🥬")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """A vegetable/fruit item. Pricing detail lives on ProductVariant below,
    because the same product can be sold multiple ways (e.g. tomato by the
    500g/1kg pack, or ready-to-cook per piece)."""

    class UnitType(models.TextChoices):
        WEIGHT = "weight", "Weight (kg/g)"
        PIECE = "piece", "Piece / Count"

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit_type = models.CharField(max_length=10, choices=UnitType.choices)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_organic = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """
    The actual sellable unit + price, e.g. 'Tomato — 500 g' at ₹32,
    or 'Coconut — 1 piece' at ₹28. This is what gets added to an order.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")

    # For unit_type=WEIGHT: weight_value + weight_unit describe the pack (e.g. 500 g, 1 kg)
    weight_value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_unit = models.CharField(
        max_length=2, choices=[("g", "grams"), ("kg", "kilograms")], null=True, blank=True
    )
    # For unit_type=PIECE: how many pieces this variant represents (usually 1)
    piece_count = models.PositiveIntegerField(null=True, blank=True)

    mrp = models.DecimalField(max_digits=8, decimal_places=2, help_text="Strike-through price")
    price = models.DecimalField(max_digits=8, decimal_places=2, help_text="Selling price")

    stock_qty = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["product", "price"]

    def __str__(self):
        if self.product.unit_type == Product.UnitType.WEIGHT:
            return f"{self.product.name} — {self.weight_value}{self.weight_unit}"
        return f"{self.product.name} — {self.piece_count} pc"

    @property
    def label(self):
        return str(self)
