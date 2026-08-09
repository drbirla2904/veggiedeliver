from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from catalog.models import Category, Product, ProductVariant
from locations.models import Area, Address
from .models import Order


class OrderNotificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="password123",
            mobile="9123456789",
        )
        self.area = Area.objects.create(
            name="Test Area",
            city="Test City",
            center_lat=12.0,
            center_lng=77.0,
            radius_km=5.0,
        )
        self.address = Address.objects.create(
            customer=self.user,
            label="Home",
            line1="123 Test Street",
            landmark="Near Test Park",
            pincode="123456",
            latitude=12.0,
            longitude=77.0,
        )
        self.category = Category.objects.create(name="Vegetables")
        self.product = Product.objects.create(
            category=self.category,
            name="Tomato",
            unit_type=Product.UnitType.WEIGHT,
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            weight_value=1,
            weight_unit="kg",
            mrp=Decimal("130.00"),
            price=Decimal("125.00"),
            stock_qty=10,
            is_active=True,
        )

    @patch("orders.views.notify_area_admin")
    @patch("orders.views.notify_customer")
    def test_checkout_places_order_with_correct_grand_total_message(self, mock_notify_customer, mock_notify_area_admin):
        self.client.force_login(self.user)
        session = self.client.session
        session["cart"] = {str(self.variant.id): 1}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            {
                "address_id": self.address.id,
                "delivery_speed": Order.DeliverySpeed.INSTANT,
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Order.objects.latest("pk")
        self.assertEqual(order.grand_total, Decimal("125.00"))
        mock_notify_customer.assert_called_once_with(order, Order.Status.PLACED)
        mock_notify_area_admin.assert_called_once_with(order, Order.Status.PLACED)

    def test_delivery_bonus_is_credited_on_delivery(self):
        from wallet.models import WalletTransaction

        self.client.force_login(self.user)
        session = self.client.session
        session["cart"] = {str(self.variant.id): 1}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            {
                "address_id": self.address.id,
                "delivery_speed": Order.DeliverySpeed.NEXT_DAY,
            },
        )
        order = Order.objects.latest("pk")
        order.delivery_member = self.user
        order.status = Order.Status.OUT_FOR_DELIVERY
        order.save(update_fields=["delivery_member", "status"])

        self.assertEqual(order.delivery_bonus, Decimal("10.00"))
        order.status = Order.Status.DELIVERED
        order.save(update_fields=["status"])

        self.assertTrue(WalletTransaction.objects.filter(
            related_order=order,
            reason=WalletTransaction.Reason.DELIVERY_BONUS,
        ).exists())
