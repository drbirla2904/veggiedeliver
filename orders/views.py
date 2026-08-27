from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from catalog.models import ProductVariant
from locations.models import Address
from locations.utils import find_nearest_delivery_member, haversine_km
from accounts.decorators import role_required
from accounts.models import User
from wallet.models import ReferralSettings, WalletTransaction
from .cart import Cart
from .models import GiftItem, Order, OrderItem, DeliveryLocationPing
from .notifications import notify_customer, notify_area_admin
from . import geo_cache

DELIVERY_BONUS_MAP = {
    Order.DeliverySpeed.INSTANT: Decimal("0.00"),
    Order.DeliverySpeed.TWO_TO_FOUR_HOURS: Decimal("5.00"),
    Order.DeliverySpeed.NEXT_DAY_MORNING: Decimal("0.00"),
}


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@require_POST
def add_to_cart(request, variant_id):
    get_object_or_404(ProductVariant, pk=variant_id, is_active=True)
    qty = int(request.POST.get("quantity", 1))
    Cart(request).add(variant_id, qty)
    cart_count = Cart(request).count()
    # If requested via AJAX/fetch, return JSON so the frontend can update inline
    is_xhr = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', '')
    if is_xhr:
        return JsonResponse({"success": True, "message": "Added to cart.", "cart_count": cart_count})

    messages.success(request, "Added to cart.")
    return redirect(request.POST.get("next") or "home")


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@require_POST
def update_cart_item(request, variant_id):
    qty = int(request.POST.get("quantity", 0))
    Cart(request).set_quantity(variant_id, qty)
    if _is_ajax(request):
        cart = Cart(request)
        line_item = next(
            (item for item in cart.line_items() if item[0].id == variant_id),
            None,
        )
        return JsonResponse({
            "success": True,
            "cart_count": cart.count(),
            "subtotal": str(cart.subtotal()),
            "variant_id": variant_id,
            "quantity": qty,
            "line_total": str(line_item[2]) if line_item else None,
        })
    return redirect("cart")


@require_POST
def remove_from_cart(request, variant_id):
    Cart(request).remove(variant_id)
    if _is_ajax(request):
        cart = Cart(request)
        return JsonResponse({
            "success": True,
            "cart_count": cart.count(),
            "subtotal": str(cart.subtotal()),
            "variant_id": variant_id,
            "quantity": 0,
            "line_total": None,
        })
    return redirect("cart")


def cart_page(request):
    cart = Cart(request)
    return render(request, "orders/cart.html", {
        "line_items": cart.line_items(),
        "subtotal": cart.subtotal(),
        "cart_count": cart.count(),
    })


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@login_required
def checkout(request):
    if not request.user.mobile or not request.user.mobile_verified:
        messages.error(request, "Please log in with your verified mobile number before placing an order.")
        return redirect("login")

    cart = Cart(request)
    if not cart.line_items():
        messages.error(request, "Your cart is empty.")
        return redirect("home")

    addresses = request.user.addresses.all()
    settings_row = ReferralSettings.load()
    wallet_balance = request.user.wallet.balance
    subtotal = cart.subtotal()
    max_wallet_usable = min(
        wallet_balance,
        (subtotal * settings_row.max_wallet_usage_percent / 100).quantize(Decimal("0.01")),
    )

    delivery_fee = (
        Decimal("0.00")
        if subtotal >= settings_row.free_delivery_minimum
        else settings_row.delivery_charge
    )

    if request.method == "POST":
        if subtotal < settings_row.minimum_order_amount:
            messages.error(
                request,
                f"Minimum order value is ₹{settings_row.minimum_order_amount}.",
            )
            return redirect("cart")

        address_id = request.POST.get("address_id")
        delivery_speed = request.POST.get("delivery_speed", Order.DeliverySpeed.INSTANT)
        delivery_bonus = DELIVERY_BONUS_MAP.get(delivery_speed, Decimal("0.00"))

        if address_id:
            address = get_object_or_404(Address, pk=address_id, customer=request.user)
        else:
            lat = request.POST.get("latitude")
            lng = request.POST.get("longitude")
            if not lat or not lng:
                messages.error(request, "Please drop a pin on the map for your delivery address.")
                return redirect("checkout")
            address = Address.objects.create(
                customer=request.user,
                label=request.POST.get("label", "Home"),
                line1=request.POST.get("line1", ""),
                landmark=request.POST.get("landmark", ""),
                pincode=request.POST.get("pincode", ""),
                latitude=float(lat),
                longitude=float(lng),
            )

        if address.area is None:
            messages.error(request, "Sorry, we don't deliver to that location yet.")
            return redirect("checkout")

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                address=address,
                area=address.area,
                payment_method=Order.PaymentMethod.COD,
                delivery_speed=delivery_speed,
                delivery_bonus=delivery_bonus,
                delivery_fee=delivery_fee,
            )
            for variant, qty, _ in cart.line_items():
                OrderItem.objects.create(order=order, variant=variant, quantity=qty, unit_price=variant.price)
            order.recalculate_total()

            if max_wallet_usable > 0:
                spend = min(max_wallet_usable, order.grand_total)
                request.user.wallet.debit(spend, reason="order_payment", related_order=order)
                order.wallet_amount_used = spend
                order.save(update_fields=["wallet_amount_used"])
                order.recalculate_total()

            notify_customer(order, Order.Status.PLACED)
            notify_area_admin(order, Order.Status.PLACED)

        cart.clear()
        messages.success(request, "Order placed successfully.")
        if delivery_speed == Order.DeliverySpeed.NEXT_DAY_MORNING:
            messages.success(
                request,
                "🎁 Gift eligibility confirmed. Your gift will be given at delivery.",
                extra_tags="gift",
            )
        return redirect("order_detail", order_id=order.id)

    return render(request, "orders/checkout.html", {
        "addresses": addresses,
        "subtotal": subtotal,
        "wallet_balance": wallet_balance,
        "max_wallet_usable": max_wallet_usable,
        "delivery_fee": delivery_fee,
        "minimum_order_amount": settings_row.minimum_order_amount,
        "free_delivery_minimum": settings_row.free_delivery_minimum,
        "cart_count": cart.count(),
        "map_default_latitude": settings.MAP_DEFAULT_LATITUDE,
        "map_default_longitude": settings.MAP_DEFAULT_LONGITUDE,
        "map_default_zoom": settings.MAP_DEFAULT_ZOOM,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "google_client_id": settings.GOOGLE_CLIENT_ID,
    })


# ---------------------------------------------------------------------------
# Customer order views
# ---------------------------------------------------------------------------

@login_required
def order_history(request):
    available_gift = GiftItem.objects.filter(
        is_active=True,
        stock_quantity__gt=0,
        minimum_order_value__lte=OuterRef("grand_total"),
    )
    orders = request.user.orders.annotate(
        gift_available=Exists(available_gift)
    ).filter(customer=request.user)
    return render(request, "orders/history.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id, customer=request.user)
    last_ping = order.location_pings.first()
    eligible_gifts = GiftItem.objects.none()
    if order.status == Order.Status.DELIVERED and not order.gift_item_id:
        eligible_gifts = GiftItem.objects.filter(
            is_active=True,
            stock_quantity__gt=0,
            minimum_order_value__lte=order.grand_total,
        )
    return render(request, "orders/detail.html", {
        "order": order,
        "last_ping": last_ping,
        "eligible_gifts": eligible_gifts,
        "eligible_gift_count": eligible_gifts.count(),
    })


@login_required
@require_POST
def cancel_order(request, order_id):
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(),
            pk=order_id,
            customer=request.user,
        )
        if order.status not in (Order.Status.PLACED, Order.Status.CONFIRMED):
            messages.error(request, "This order can no longer be cancelled.")
            return redirect("order_detail", order_id=order.id)

        if order.wallet_amount_used > 0:
            wallet = request.user.wallet
            wallet.credit(
                order.wallet_amount_used,
                reason=WalletTransaction.Reason.ADJUSTMENT,
                related_order=order,
            )

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])

    messages.success(request, f"Order #{order.id} cancelled.")
    return redirect("order_detail", order_id=order.id)


@login_required
@require_POST
def spin_gift(request, order_id):
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(),
            pk=order_id,
            customer=request.user,
        )
        if order.status != Order.Status.DELIVERED:
            messages.error(request, "Your gift spin unlocks after delivery.")
            return redirect("order_detail", order_id=order.id)
        if order.gift_item_id:
            messages.info(request, "You have already spun for this order's gift.")
            return redirect("order_detail", order_id=order.id)

        gift = GiftItem.objects.select_for_update().filter(
            is_active=True,
            stock_quantity__gt=0,
            minimum_order_value__lte=order.grand_total,
        ).order_by("?").first()
        if gift is None:
            messages.error(request, "No gifts are available for this order right now.")
            return redirect("order_detail", order_id=order.id)

        gift.stock_quantity -= 1
        gift.save(update_fields=["stock_quantity"])
        order.gift_item = gift
        order.gift_spun_at = timezone.now()
        order.save(update_fields=["gift_item", "gift_spun_at"])

    messages.success(request, f"🎁 Gift received: you won a {gift.name}.", extra_tags="gift")
    return redirect("order_detail", order_id=order.id)


def order_tracking_data(request, order_id):
    """Polled by JS on the order-detail map to move the delivery pin live.
    Checks Redis first (the live, low-latency path) and only falls back to
    the DB's last saved ping if the Redis entry has expired — e.g. between
    a rider's pings, or if their app briefly stopped reporting."""
    order = get_object_or_404(Order, pk=order_id, customer=request.user)

    live = geo_cache.get_order_location(order.id)
    if live:
        return JsonResponse({
            "has_location": True,
            "latitude": live["latitude"],
            "longitude": live["longitude"],
            "status": order.status,
            "source": "live",
        })

    ping = order.location_pings.first()
    if not ping:
        return JsonResponse({"has_location": False})
    return JsonResponse({
        "has_location": True,
        "latitude": ping.latitude,
        "longitude": ping.longitude,
        "recorded_at": ping.recorded_at.isoformat(),
        "status": order.status,
        "source": "last_known",
    })


# ---------------------------------------------------------------------------
# Area admin dashboard
# ---------------------------------------------------------------------------

@role_required(User.Role.AREA_ADMIN)
def area_dashboard(request):
    area = request.user.area
    orders = list(Order.objects.filter(area=area).exclude(status=Order.Status.DELIVERED).select_related("address")[:50])
    delivery_members = list(User.objects.filter(role=User.Role.DELIVERY_MEMBER, area=area))
    rider_locations = geo_cache.get_rider_locations([r.id for r in delivery_members])
    unassigned_orders = [o for o in orders if o.delivery_member_id is None]

    rider_suggestions = []
    for rider in delivery_members:
        coords = rider_locations.get(rider.id)
        if coords and unassigned_orders:
            nearest_order = None
            nearest_distance = None
            for order in unassigned_orders:
                distance = haversine_km(
                    coords["latitude"], coords["longitude"],
                    order.address.latitude, order.address.longitude,
                )
                if nearest_distance is None or distance < nearest_distance:
                    nearest_distance = distance
                    nearest_order = order
            rider_suggestions.append({
                "id": rider.id,
                "name": rider.get_full_name() or rider.mobile,
                "nearest_order_id": nearest_order.id if nearest_order else None,
                "distance_km": round(nearest_distance, 2) if nearest_distance is not None else None,
            })
        else:
            rider_suggestions.append({
                "id": rider.id,
                "name": rider.get_full_name() or rider.mobile,
                "nearest_order_id": None,
                "distance_km": None,
            })

    return render(request, "orders/area_dashboard.html", {
        "area": area,
        "orders": orders,
        "delivery_members": delivery_members,
        "rider_suggestions": rider_suggestions,
    })


@role_required(User.Role.AREA_ADMIN)
@require_POST
def assign_delivery_member(request, order_id):
    order = get_object_or_404(Order, pk=order_id, area=request.user.area)
    member_id = request.POST.get("delivery_member_id")
    member = get_object_or_404(User, pk=member_id, role=User.Role.DELIVERY_MEMBER, area=request.user.area)
    order.delivery_member = member
    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["delivery_member", "status"])
    messages.success(request, f"Order #{order.id} assigned to {member.get_full_name() or member.mobile}.")
    return redirect("area_dashboard")


@role_required(User.Role.AREA_ADMIN)
@require_POST
def auto_assign_delivery_member(request, order_id):
    """Finds the nearest on-duty, recently-active delivery member in the
    order's area and assigns them — no manual dropdown needed."""
    order = get_object_or_404(Order, pk=order_id, area=request.user.area)
    member, distance_km = find_nearest_delivery_member(
        order.area, order.address.latitude, order.address.longitude
    )
    if not member:
        messages.error(request, "No on-duty delivery member with a recent location was found nearby. Assign manually instead.")
        return redirect("area_dashboard")

    order.delivery_member = member
    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["delivery_member", "status"])
    messages.success(
        request,
        f"Order #{order.id} auto-assigned to {member.get_full_name() or member.mobile} "
        f"(~{distance_km:.1f} km away)."
    )
    return redirect("area_dashboard")


@role_required(User.Role.AREA_ADMIN)
def create_delivery_member(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile", "").strip()
        name = request.POST.get("first_name", "").strip()
        if User.objects.filter(mobile=mobile).exists():
            messages.error(request, "A user with that mobile number already exists.")
        else:
            User.objects.create_user(
                username=mobile, mobile=mobile, first_name=name,
                role=User.Role.DELIVERY_MEMBER, area=request.user.area,
                created_by=request.user, mobile_verified=True,
            )
            messages.success(request, f"Delivery member {name} added.")
            return redirect("area_dashboard")
    return render(request, "orders/create_delivery_member.html")


@role_required(User.Role.AREA_ADMIN)
def area_live_map(request):
    """A map of every on-duty rider and every active order in this area,
    for the admin to eyeball coverage — not just a text list."""
    return render(request, "orders/area_live_map.html", {"area": request.user.area})


@role_required(User.Role.AREA_ADMIN)
def area_live_map_data(request):
    """JSON feed the live-map page polls: rider positions + active order pins.
    Rider positions are a single bulk Redis fetch (see geo_cache.py) rather
    than N individual DB rows — cheap even with 50+ riders on the map."""
    area = request.user.area
    all_delivery_members = list(User.objects.filter(role=User.Role.DELIVERY_MEMBER, area=area))
    positions = geo_cache.get_rider_locations([r.id for r in all_delivery_members])

    orders = Order.objects.filter(area=area).exclude(
        status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]
    ).select_related("address")

    riders_payload = []
    for r in all_delivery_members:
        pos = positions.get(r.id)
        if not pos:
            continue  # no recent Redis ping — don't show a stale/unknown dot
        riders_payload.append({
            "id": r.id,
            "name": r.get_full_name() or r.mobile,
            "latitude": pos["latitude"],
            "longitude": pos["longitude"],
            "on_duty": r.is_on_duty,
        })

    return JsonResponse({
        "riders": riders_payload,
        "orders": [
            {
                "id": o.id,
                "status": o.status,
                "latitude": o.address.latitude,
                "longitude": o.address.longitude,
                "delivery_member_id": o.delivery_member_id,
            }
            for o in orders
        ],
    })


# ---------------------------------------------------------------------------
# Delivery member dashboard
# ---------------------------------------------------------------------------

@role_required(User.Role.DELIVERY_MEMBER)
def delivery_dashboard(request):
    orders = list(Order.objects.filter(
        delivery_member=request.user
    ).exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).select_related("address"))

    rider_location = geo_cache.get_rider_location(request.user.id)
    if rider_location:
        for order in orders:
            order.distance_from_rider = haversine_km(
                rider_location["latitude"], rider_location["longitude"],
                order.address.latitude, order.address.longitude,
            )
        orders.sort(key=lambda o: o.distance_from_rider)
    else:
        for order in orders:
            order.distance_from_rider = None

    return render(request, "orders/delivery_dashboard.html", {
        "orders": orders,
        "rider_location": rider_location,
    })


@role_required(User.Role.DELIVERY_MEMBER)
@require_POST
def toggle_duty(request):
    """Rider flips themself on/off duty — only on-duty riders with a
    recent location are eligible for nearest-rider auto-assignment."""
    request.user.is_on_duty = not request.user.is_on_duty
    request.user.save(update_fields=["is_on_duty"])
    messages.success(request, f"You are now {'on' if request.user.is_on_duty else 'off'} duty.")
    return redirect("delivery_dashboard")


@role_required(User.Role.DELIVERY_MEMBER)
@require_POST
def update_my_location(request):
    """Called periodically by JS while a rider is on duty (independent of
    any specific order) so the area-admin map and auto-assign always have
    a fresh position to work with. Writes to Redis, not the DB — at
    several riders pinging every ~15-20s, this is the difference between
    a handful of sub-ms Redis writes and a steady stream of DB writes
    competing with order traffic."""
    lat = request.POST.get("latitude")
    lng = request.POST.get("longitude")
    if lat and lng:
        geo_cache.set_rider_location(request.user.id, float(lat), float(lng))
    return JsonResponse({"ok": True})


@role_required(User.Role.DELIVERY_MEMBER)
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id, delivery_member=request.user)
    new_status = request.POST.get("status")
    if new_status in dict(Order.Status.choices):
        order.status = new_status
        if new_status == Order.Status.DELIVERED:
            from django.utils import timezone
            order.delivered_at = timezone.now()
            order.save(update_fields=["status", "delivered_at"])
            if order.delivery_bonus > 0:
                already_credited = order.customer.wallet.transactions.filter(
                    reason=WalletTransaction.Reason.DELIVERY_BONUS,
                    related_order=order,
                ).exists()
                if not already_credited:
                    order.customer.wallet.credit(
                        amount=order.delivery_bonus,
                        reason=WalletTransaction.Reason.DELIVERY_BONUS,
                        related_order=order,
                    )
        else:
            order.save(update_fields=["status"])
        messages.success(request, f"Order #{order.id} marked {order.get_status_display()}.")
    return redirect("delivery_dashboard")


@role_required(User.Role.DELIVERY_MEMBER)
@require_POST
def ping_location(request, order_id):
    """Called by JS geolocation on the delivery member's phone while an
    order is out for delivery. Every ping updates the Redis live position
    (what the customer's tracking map actually polls). A DB row is only
    written at most once a minute — enough for a delivery history trail
    without turning frequent GPS updates into a stream of DB writes."""
    from django.utils import timezone
    from datetime import timedelta

    order = get_object_or_404(Order, pk=order_id, delivery_member=request.user)
    lat = request.POST.get("latitude")
    lng = request.POST.get("longitude")
    if lat and lng:
        lat, lng = float(lat), float(lng)
        geo_cache.set_order_location(order.id, lat, lng)
        geo_cache.set_rider_location(request.user.id, lat, lng)

        last_db_ping = order.location_pings.first()
        throttle_cutoff = timezone.now() - timedelta(seconds=60)
        if not last_db_ping or last_db_ping.recorded_at < throttle_cutoff:
            DeliveryLocationPing.objects.create(order=order, latitude=lat, longitude=lng)
    return JsonResponse({"ok": True})