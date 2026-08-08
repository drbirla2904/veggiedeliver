import math


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance between two points, in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def find_area_for_point(lat, lng):
    """
    Return the closest Area whose service radius contains (lat, lng),
    or None if the point falls outside every active area.
    Used to auto-assign an Address (and therefore every Order placed
    against it) to the right area-admin's territory.
    """
    from .models import Area

    best_area, best_distance = None, None
    for area in Area.objects.filter(is_active=True):
        distance = haversine_km(lat, lng, area.center_lat, area.center_lng)
        if distance <= area.radius_km and (best_distance is None or distance < best_distance):
            best_area, best_distance = area, distance
    return best_area


def find_nearest_delivery_member(area, lat, lng, exclude_ids=None):
    """
    Among on-duty delivery members in this area, return the one closest to
    (lat, lng) — used to auto-assign a new order to the nearest available
    rider instead of an area admin picking manually.

    Live positions come from Redis (see orders/geo_cache.py), not a DB
    column — a rider whose last ping has aged out of Redis (phone off,
    app closed) simply has no entry and is skipped, so "stale" riders
    are excluded automatically without a manual freshness check here.
    """
    from accounts.models import User
    from orders.geo_cache import get_rider_locations

    candidates = User.objects.filter(
        role=User.Role.DELIVERY_MEMBER, area=area, is_on_duty=True,
    )
    if exclude_ids:
        candidates = candidates.exclude(id__in=exclude_ids)
    candidate_ids = list(candidates.values_list("id", flat=True))

    positions = get_rider_locations(candidate_ids)
    if not positions:
        return None, None

    best_id, best_distance = None, None
    for rider_id, pos in positions.items():
        distance = haversine_km(lat, lng, pos["latitude"], pos["longitude"])
        if best_distance is None or distance < best_distance:
            best_id, best_distance = rider_id, distance

    best_member = User.objects.filter(id=best_id).first() if best_id else None
    return best_member, best_distance