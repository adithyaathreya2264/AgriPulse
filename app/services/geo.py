"""Small geo helpers (no external service): distance and radius search."""

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance between two points in kilometres."""

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )

    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bounding_box(lat, lng, radius_km):
    """
    Square that contains the search circle: used as a cheap database
    pre-filter before the exact haversine check.
    Returns (min_lat, max_lat, min_lng, max_lng).
    """

    d_lat = math.degrees(radius_km / EARTH_RADIUS_KM)

    # Longitude degrees shrink towards the poles
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    d_lng = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat))

    return lat - d_lat, lat + d_lat, lng - d_lng, lng + d_lng


def within_radius(items, lat, lng, radius_km, geo_key="location_geo"):
    """
    Keep items whose `geo_key` {lat, lng} is inside the radius.
    Adds `distance_km` and sorts nearest first.
    """

    nearby = []

    for item in items:
        geo = item.get(geo_key)

        if not geo:
            continue

        distance = haversine_km(lat, lng, geo["lat"], geo["lng"])

        if distance <= radius_km:
            nearby.append({**item, "distance_km": round(distance, 2)})

    return sorted(nearby, key=lambda item: item["distance_km"])
