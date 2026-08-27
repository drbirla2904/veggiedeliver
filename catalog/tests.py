from django.test import TestCase

from .models import Category, Product, ProductVariant


class ProductDetailRelatedProductsTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name="Vegetables")
		self.product = Product.objects.create(
			category=category,
			name="Tomato",
			unit_type=Product.UnitType.WEIGHT,
		)
		related_product = Product.objects.create(
			category=category,
			name="Potato",
			unit_type=Product.UnitType.WEIGHT,
		)
		self.related_variant = ProductVariant.objects.create(
			product=related_product,
			weight_value=1,
			weight_unit="kg",
			mrp=40,
			price=35,
		)

	def test_product_detail_shows_related_product_with_add_to_cart_action(self):
		response = self.client.get(f"/product/{self.product.id}/")

		self.assertContains(response, "Potato")
		self.assertContains(response, f"/cart/add/{self.related_variant.id}/")

		cart_response = self.client.post(
			f"/cart/add/{self.related_variant.id}/",
			{"quantity": 1, "next": f"/product/{self.product.id}/"},
		)

		self.assertRedirects(cart_response, f"/product/{self.product.id}/")
		self.assertEqual(self.client.session["cart"][str(self.related_variant.id)], 1)
