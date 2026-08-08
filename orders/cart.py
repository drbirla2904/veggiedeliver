"""
Simple session-based cart. Stores {variant_id: quantity} in the session,
so it survives across pages without needing a DB table until checkout.
"""
from catalog.models import ProductVariant

SESSION_KEY = "cart"


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(SESSION_KEY, {})

    def add(self, variant_id, quantity=1):
        variant_id = str(variant_id)
        self.data[variant_id] = self.data.get(variant_id, 0) + quantity
        if self.data[variant_id] <= 0:
            self.data.pop(variant_id, None)
        self.save()

    def set_quantity(self, variant_id, quantity):
        variant_id = str(variant_id)
        if quantity <= 0:
            self.data.pop(variant_id, None)
        else:
            self.data[variant_id] = quantity
        self.save()

    def remove(self, variant_id):
        self.data.pop(str(variant_id), None)
        self.save()

    def clear(self):
        self.data = {}
        self.save()

    def save(self):
        self.session[SESSION_KEY] = self.data
        self.session.modified = True

    def count(self):
        return sum(self.data.values())

    def line_items(self):
        """Returns [(variant, quantity, line_total), ...] for current cart contents.
        Silently drops variants that were deleted/deactivated since being added."""
        items = []
        variants = ProductVariant.objects.filter(
            id__in=[int(v) for v in self.data.keys()], is_active=True
        ).select_related("product")
        variants_by_id = {v.id: v for v in variants}
        for variant_id, qty in self.data.items():
            variant = variants_by_id.get(int(variant_id))
            if variant:
                items.append((variant, qty, variant.price * qty))
        return items

    def subtotal(self):
        return sum(line_total for _, _, line_total in self.line_items())
