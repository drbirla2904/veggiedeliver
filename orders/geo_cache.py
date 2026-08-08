"""
Live rider locations, kept in Redis instead of round-tripping through
Postgres on every ~15s GPS ping. At 100-500 daily customers with several
riders active simultaneously, this is the difference between a handful of
sub-millisecond Redis writes and a steady stream of DB writes/reads
competing with order traffic.

Each rider's position is stored as a Redis hash with a TTL — if a rider's
phone stops reporting (app closed, out of battery), their entry silently
expires instead of leaving a stale marker on the live map forever.
"""
import json
from django_redis import get_redis_connection

RIDER_KEY_PREFIX = "rider_loc:"
ORDER_KEY_PREFIX = "order_loc:"
LOCATION_TTL_SECONDS = 90  # ~6x the expected ping interval


def _client():
    return get_redis_connection("redis")


def set_rider_location(user_id, latitude, longitude):
    _client().setex(
        f"{RIDER_KEY_PREFIX}{user_id}",
        LOCATION_TTL_SECONDS,
        json.dumps({"latitude": latitude, "longitude": longitude}),
    )


def get_rider_location(user_id):
    raw = _client().get(f"{RIDER_KEY_PREFIX}{user_id}")
    return json.loads(raw) if raw else None


def get_rider_locations(user_ids):
    """Bulk fetch — one round trip instead of N, for the area live map."""
    client = _client()
    keys = [f"{RIDER_KEY_PREFIX}{uid}" for uid in user_ids]
    if not keys:
        return {}
    values = client.mget(keys)
    return {
        uid: json.loads(v) for uid, v in zip(user_ids, values) if v
    }


def set_order_location(order_id, latitude, longitude):
    _client().setex(
        f"{ORDER_KEY_PREFIX}{order_id}",
        LOCATION_TTL_SECONDS,
        json.dumps({"latitude": latitude, "longitude": longitude}),
    )


def get_order_location(order_id):
    raw = _client().get(f"{ORDER_KEY_PREFIX}{order_id}")
    return json.loads(raw) if raw else None