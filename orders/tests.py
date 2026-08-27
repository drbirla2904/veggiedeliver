from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from catalog.models import Category, Product, ProductVariant
from locations.models import Area, Address
from .models import GiftItem, Order
from .notifications import _format_order_status_message


class OrderNotificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="password123",
            mobile="9123456789",
            mobile_verified=True,
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

    def test_checkout_requires_verified_mobile_account(self):
        self.user.mobile = ""
        self.user.mobile_verified = False
        self.user.save(update_fields=["mobile", "mobile_verified"])
        self.client.force_login(self.user)

        session = self.client.session
        session["cart"] = {str(self.variant.id): 1}
        session.save()

        response = self.client.post(reverse("checkout"), {
            "address_id": self.address.id,
            "delivery_speed": Order.DeliverySpeed.INSTANT,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("login"))
        self.assertFalse(Order.objects.exists())

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
                "delivery_speed": Order.DeliverySpeed.TWO_TO_FOUR_HOURS,
            },
        )
        order = Order.objects.latest("pk")
        order.delivery_member = self.user
        order.status = Order.Status.OUT_FOR_DELIVERY
        order.save(update_fields=["delivery_member", "status"])

        self.assertEqual(order.delivery_bonus, Decimal("5.00"))
        order.status = Order.Status.DELIVERED
        order.save(update_fields=["status"])

        self.assertTrue(WalletTransaction.objects.filter(
            related_order=order,
            reason=WalletTransaction.Reason.DELIVERY_BONUS,
        ).exists())

    def test_order_below_minimum_is_rejected(self):
        from wallet.models import ReferralSettings

        self.client.force_login(self.user)
        session = self.client.session
        session["cart"] = {str(self.variant.id): 1}
        session.save()
        ReferralSettings.objects.create(minimum_order_amount=Decimal("200.00"))

        response = self.client.post(reverse("checkout"), {
            "address_id": self.address.id,
            "delivery_speed": Order.DeliverySpeed.INSTANT,
        })

        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Order.objects.exists())

    def test_customer_can_cancel_before_order_is_out_for_delivery(self):
        self.client.force_login(self.user)
        order = Order.objects.create(
            customer=self.user,
            address=self.address,
            area=self.area,
            status=Order.Status.CONFIRMED,
            wallet_amount_used=Decimal("20.00"),
        )
        starting_balance = self.user.wallet.balance

        response = self.client.post(reverse("cancel_order", args=[order.id]))

        self.assertRedirects(response, reverse("order_detail", args=[order.id]))
        order.refresh_from_db()
        self.user.wallet.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.user.wallet.balance, starting_balance + Decimal("20.00"))

    def test_confirmed_notification_handles_unassigned_order(self):
        order = Order.objects.create(
            customer=self.user,
            address=self.address,
            area=self.area,
            status=Order.Status.CONFIRMED,
        )

        message = _format_order_status_message(order, Order.Status.CONFIRMED)

        self.assertIn("our delivery team", message)

    def test_customer_cannot_cancel_order_out_for_delivery(self):
        self.client.force_login(self.user)
        order = Order.objects.create(
            customer=self.user,
            address=self.address,
            area=self.area,
            status=Order.Status.OUT_FOR_DELIVERY,
        )

        response = self.client.post(reverse("cancel_order", args=[order.id]))

        self.assertRedirects(response, reverse("order_detail", args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.OUT_FOR_DELIVERY)

    def test_eligible_delivered_customer_can_spin_once_for_gift(self):
        self.client.force_login(self.user)
        GiftItem.objects.all().delete()
        order = Order.objects.create(
            customer=self.user,
            address=self.address,
            area=self.area,
            status=Order.Status.DELIVERED,
            grand_total=Decimal("125.00"),
        )
        gift = GiftItem.objects.create(
            name="Tea cup",
            description="A cheerful cup for your next chai break.",
            minimum_order_value=Decimal("100.00"),
            stock_quantity=1,
        )

        response = self.client.post(reverse("spin_gift", args=[order.id]))

        self.assertRedirects(response, reverse("order_detail", args=[order.id]))
        order.refresh_from_db()
        gift.refresh_from_db()
        self.assertEqual(order.gift_item, gift)
        self.assertIsNotNone(order.gift_spun_at)
        self.assertEqual(gift.stock_quantity, 0)

        self.client.post(reverse("spin_gift", args=[order.id]))
        self.assertEqual(GiftItem.objects.get(pk=gift.pk).stock_quantity, 0)

    def test_gift_spin_requires_delivered_eligible_order(self):
        self.client.force_login(self.user)
        order = Order.objects.create(
            customer=self.user,
            address=self.address,
            area=self.area,
            status=Order.Status.CONFIRMED,
            grand_total=Decimal("50.00"),
        )
        GiftItem.objects.create(name="Plate", minimum_order_value=Decimal("100.00"), stock_quantity=2)

        self.client.post(reverse("spin_gift", args=[order.id]))

        order.refresh_from_db()
        self.assertIsNone(order.gift_item_id)

    def test_free_delivery_threshold_is_applied(self):
        from wallet.models import ReferralSettings

        self.client.force_login(self.user)
        session = self.client.session
        session["cart"] = {str(self.variant.id): 1}
        session.save()
        ReferralSettings.objects.create(free_delivery_minimum=Decimal("100.00"))

        self.client.post(reverse("checkout"), {
            "address_id": self.address.id,
            "delivery_speed": Order.DeliverySpeed.INSTANT,
        })

        self.assertEqual(Order.objects.latest("pk").delivery_fee, Decimal("0.00"))

    def test_wallet_balance_is_applied_automatically(self):
        self.client.force_login(self.user)
        self.user.wallet.credit(Decimal("80.00"), reason="adjustment")
        session = self.client.session
        session["cart"] = {str(self.variant.id): 1}
        session.save()

        self.client.post(reverse("checkout"), {
            "address_id": self.address.id,
            "delivery_speed": Order.DeliverySpeed.INSTANT,
        })

        order = Order.objects.latest("pk")
        self.assertEqual(order.wallet_amount_used, Decimal("62.50"))
        self.assertEqual(order.grand_total, Decimal("62.50"))

    def test_referral_bonus_is_paid_once_after_first_delivered_order(self):
        from wallet.models import ReferralSettings, WalletTransaction

        referrer = self.user
        referred = get_user_model().objects.create_user(
            username="referreduser",
            password="password123",
            mobile="9876543210",
            referred_by=referrer,
        )
        referred_address = Address.objects.create(
            customer=referred,
            label="Home",
            line1="456 Referred Street",
            pincode="123456",
            latitude=12.0,
            longitude=77.0,
        )
        ReferralSettings.objects.create(
            bonus_amount=Decimal("25.00"),
            min_order_value_for_bonus=Decimal("99.00"),
        )

        first_order = Order.objects.create(
            customer=referred,
            address=referred_address,
            area=self.area,
            items_total=Decimal("125.00"),
            grand_total=Decimal("125.00"),
        )
        first_order.status = Order.Status.DELIVERED
        first_order.save(update_fields=["status"])

        second_order = Order.objects.create(
            customer=referred,
            address=referred_address,
            area=self.area,
            items_total=Decimal("150.00"),
            grand_total=Decimal("150.00"),
        )
        second_order.status = Order.Status.DELIVERED
        second_order.save(update_fields=["status"])

        referral_rewards = WalletTransaction.objects.filter(
            wallet=referrer.wallet,
            reason=WalletTransaction.Reason.REFERRAL_BONUS,
        )
        self.assertEqual(referral_rewards.count(), 1)
        self.assertEqual(referral_rewards.first().amount, Decimal("25.00"))
