from django.test import TestCase
from django.urls import reverse

from locations.models import Area, Address
from orders.models import Order
from .models import User


class DeleteAddressTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="customer1",
			password="password123",
			mobile="9123456789",
		)
		self.other_user = User.objects.create_user(
			username="customer2",
			password="password123",
			mobile="9876543210",
		)
		self.area = Area.objects.create(
			name="Test Area",
			center_lat=12.0,
			center_lng=77.0,
		)
		self.address = Address.objects.create(
			customer=self.user,
			line1="123 Test Street",
			latitude=12.0,
			longitude=77.0,
		)

	def test_customer_can_delete_saved_address(self):
		self.client.force_login(self.user)

		response = self.client.post(reverse("delete_address", args=[self.address.id]))

		self.assertRedirects(response, reverse("profile"))
		self.assertFalse(Address.objects.filter(pk=self.address.id).exists())

	def test_customer_cannot_delete_another_customers_address(self):
		other_address = Address.objects.create(
			customer=self.other_user,
			line1="456 Other Street",
			latitude=12.0,
			longitude=77.0,
		)
		self.client.force_login(self.user)

		response = self.client.post(reverse("delete_address", args=[other_address.id]))

		self.assertEqual(response.status_code, 404)
		self.assertTrue(Address.objects.filter(pk=other_address.id).exists())

	def test_address_used_by_order_cannot_be_deleted(self):
		Order.objects.create(
			customer=self.user,
			address=self.address,
			area=self.area,
		)
		self.client.force_login(self.user)

		response = self.client.post(reverse("delete_address", args=[self.address.id]))

		self.assertRedirects(response, reverse("profile"))
		self.assertTrue(Address.objects.filter(pk=self.address.id).exists())
from django.test import TestCase

# Create your tests here.
