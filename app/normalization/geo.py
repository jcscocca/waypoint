from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000


def is_valid_coordinate(latitude: float | None, longitude: float | None) -> bool:
    if latitude is None or longitude is None:
        return False
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    rlat1 = radians(lat1)
    rlat2 = radians(lat2)
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        raise ValueError("Cannot compute centroid for empty points")
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def max_distance_from(lat: float, lon: float, points: list[tuple[float, float]]) -> float:
    if not points:
        return 0
    return max(haversine_m(lat, lon, point[0], point[1]) for point in points)


def snap_to_grid(latitude: float, longitude: float, decimals: int = 3) -> tuple[float, float]:
    return round(latitude, decimals), round(longitude, decimals)
