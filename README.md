# Veggie Delivery Platform — Django backend

A working starter for a vegetable-delivery app with area-wise admins,
area-wise delivery members, mobile-OTP customer login, map-aware
addresses/orders, and a referral-only wallet. Everything below has been
run and tested (migrations apply cleanly, referral bonus verified
end-to-end, OTP login API tested with curl).

## Apps

| App | Responsibility |
|---|---|
| `accounts` | Single custom `User` model with a `role` field (`super_admin`, `area_admin`, `delivery_member`, `customer`), mobile-OTP login/signup API, referral code |
| `locations` | `Area` (a delivery zone — name, center point, radius) and `Address` (customer's pinned location, auto-assigned to an `Area` on save) |
| `catalog` | `Category` → `Product` → `ProductVariant`, where a variant is the actual sellable unit — weight-based (e.g. "500 g") or piece-based (e.g. "2 pieces"), each with its own price |
| `orders` | `Order`, `OrderItem`, and `DeliveryLocationPing` (live GPS trail for order tracking) |
| `wallet` | `Wallet` + `WalletTransaction` (bonus-only, no user top-up), `ReferralSettings` (admin-editable bonus %) |

## Key design decisions

**Roles, not separate apps.** One `User` model with a `role` field rather
than separate Django auth backends — simpler migrations, and Django admin
can filter/scope by role in one place (see `accounts/admin.py`).

**Area-wise scoping happens in `get_queryset()`.** A super admin sees
everything. An area admin's Django admin is automatically filtered to
their own `area` — for users, orders, and delivery-member assignment. An
area admin creating a "user" is silently forced into `role=delivery_member`
and their own area, so they can't accidentally create another admin or
poach staff from a different zone.

**Area assignment is automatic, from the pin.** `Area` stores a center
lat/lng + radius (no PostGIS needed to launch). When a customer saves an
`Address`, a `pre_save` signal (`locations/signals.py`) runs a haversine
distance check against all active areas and attaches the closest one that
contains the point. An `Order` copies `address.area` at placement time, so
it stays put even if you redraw zone boundaries later. If your zones stop
being simple circles, swap `Area.center_lat/lng/radius_km` for a
GeoDjango `PolygonField` — the `find_area_for_point()` function in
`locations/utils.py` is the only place that needs to change.

**Weight-wise vs piece-wise pricing.** `Product.unit_type` is `weight` or
`piece`. The actual price lives on `ProductVariant` (e.g. Tomato has a
"500 g @ ₹32" variant and a "1 kg @ ₹58" variant) — admin adds variants
inline under each product in Django admin.

**Wallet is bonus-only by design**, per your spec: there's no "add money"
endpoint. `Wallet.credit()` / `.debit()` are the only ways the balance
moves, and every movement is logged in `WalletTransaction` for an audit
trail. `wallet/signals.py` credits the referrer automatically whenever
one of their referred customers' orders flips to `delivered` — on every
purchase, not just the first, per your requirement — gated by
`ReferralSettings.bonus_percent` and a minimum order value (both editable
in admin, no redeploy needed). A dedupe check stops double-crediting if
the order is saved again after delivery.

**Mobile-OTP auth** (`accounts/services.py`, `views.py`): `POST
/api/auth/otp/request/` generates and "sends" an OTP (wire in
MSG91/Twilio/Fast2SMS inside `generate_and_send_otp` — there's a `TODO`
marking exactly where); `POST /api/auth/otp/verify/` checks it, creates
the customer account on first login, applies a `referral_code` if one was
passed at signup, and returns a DRF auth token.

## Not yet built (natural next steps, in rough priority order)

1. **Razorpay integration** for the `online` payment method (you're already
   using Razorpay elsewhere, so this should drop in cleanly next to COD).
2. **Real SMS gateway wiring** — `accounts/services.py:generate_and_send_otp`
   has a `TODO` marking exactly where to call MSG91/Twilio/Fast2SMS. Right
   now OTPs just get written to the DB — check the OTP list in `/admin/`
   to read the code while testing.
3. **Celery task** to auto-assign the nearest available delivery member to
   a new order (same haversine helper used for area-assignment could do
   this too, scored across on-duty delivery members).
4. **Product images** — `Product.image` field exists; storefront templates
   currently show category emoji as a stand-in, swap in `{{ product.image.url }}`
   once you're uploading real photos.
5. Swap SQLite → Postgres for production; your Contabo VPS + Nginx setup
   should carry over as-is. Set `ALLOWED_HOSTS` to your real domain(s)
   before deploying — it's wide open (`['*']`) for local dev right now.

## What's included — full templated site, not just an API

Every role has real pages, not just Django admin:

- **Customer** (mobile-first, matches the Taazgi demo look): browse by
  category → product detail → cart → checkout (tap-to-pin map via
  Leaflet/OpenStreetMap, no API key needed) → order confirmation → order
  history → live order tracking (polls a JSON endpoint every 8s to move
  the delivery pin) → wallet & referral link → profile.
- **Area admin** (`/area/`): active orders in their zone only, one-click
  delivery-member assignment, a form to add new delivery members (which
  auto-scopes them to the admin's own area).
- **Delivery member** (`/delivery/`): assigned orders, "start delivery" /
  "mark delivered" buttons, and a "share live location" button that uses
  the phone's GPS (`navigator.geolocation.watchPosition`) to post
  location pings the customer's tracking map picks up.
- Login is mobile-OTP end to end, session-based (not just the JSON API) —
  `/login/` → enter mobile → OTP screen → verified session, and the
  referral link format is `/login/?ref=<code>` so a shared link
  auto-applies the referral on signup.

I ran the full request/response cycle for every page above with Django's
test client before shipping this — customer checkout → area-admin
assignment → delivery status updates → live location ping → customer
tracking endpoint — all pass.

## Running it

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then visit `/admin/` to add your first `Area`, some `Category` /
`Product` / `ProductVariant` entries, and to create area admins. Area
admins log into the same `/admin/` and will only see their own area's
data.

Test the OTP flow:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/otp/request/ \
  -H "Content-Type: application/json" -d '{"mobile": "9123456780"}'

# grab the code from the OTP admin list (or your SMS gateway once wired up)
curl -X POST http://127.0.0.1:8000/api/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"mobile": "9123456780", "code": "123456", "first_name": "Test"}'
```
