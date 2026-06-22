from datetime import UTC, datetime

from app.normalization.stops import detect_stops_from_observations
from app.schemas import LocationObservation


def obs(timestamp: str, lat: float, lon: float) -> LocationObservation:
    return LocationObservation(
        source_type="csv",
        source_record_type="point",
        source_record_hash=f"{timestamp}:{lat}:{lon}",
        observed_at_utc=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
        latitude=lat,
        longitude=lon,
    )


def test_detect_stops_from_points_with_minimum_dwell_time():
    observations = [
        obs("2024-01-02T08:00:00Z", 47.609500, -122.333100),
        obs("2024-01-02T08:05:00Z", 47.609530, -122.333080),
        obs("2024-01-02T08:12:00Z", 47.609540, -122.333070),
        obs("2024-01-02T08:25:00Z", 47.620600, -122.320900),
    ]

    stops = detect_stops_from_observations(
        observations,
        import_id="import-1",
        user_id_hash="user-hash",
        minimum_stop_duration_minutes=10,
        stop_radius_m=75,
    )

    assert len(stops) == 1
    assert stops[0].duration_minutes == 12
    assert stops[0].point_count_used == 3
    assert stops[0].centroid_latitude > 47.6095
    assert stops[0].start_time_utc == datetime(2024, 1, 2, 8, 0, tzinfo=UTC)
