from datetime import UTC, datetime, timedelta

from app.normalization.clusters import cluster_stop_visits, infer_sensitive_locations
from app.schemas import StopVisitData


def stop(stop_id: str, start_hour: int, lat: float, lon: float, duration: int) -> StopVisitData:
    start = datetime(2024, 1, 1 + int(stop_id[-1]), start_hour, 0, tzinfo=UTC)
    return StopVisitData(
        id=stop_id,
        import_id="import-1",
        user_id_hash="user-hash",
        start_time_utc=start,
        end_time_utc=start + timedelta(minutes=duration),
        duration_minutes=duration,
        centroid_latitude=lat,
        centroid_longitude=lon,
        source_basis="place_visit",
    )


def test_cluster_stop_visits_requires_recurring_thresholds():
    stops = [
        stop("stop-1", 9, 47.60950, -122.33310, 30),
        stop("stop-2", 10, 47.60955, -122.33315, 20),
        stop("stop-3", 11, 47.60960, -122.33320, 25),
        stop("stop-4", 12, 47.62060, -122.32090, 240),
    ]

    clusters = cluster_stop_visits(
        stops,
        cluster_radius_m=100,
        minimum_cluster_visits=3,
        minimum_cluster_total_dwell_minutes=60,
    )

    assert len(clusters) == 2
    assert clusters[0].visit_count == 3
    assert clusters[0].total_dwell_minutes == 75
    assert stops[0].place_cluster_id == clusters[0].id


def test_infer_sensitive_locations_marks_overnight_home_like_cluster():
    stops = [
        stop("stop-1", 21, 47.60950, -122.33310, 540),
        stop("stop-2", 22, 47.60955, -122.33315, 480),
        stop("stop-3", 23, 47.60960, -122.33320, 420),
    ]
    clusters = cluster_stop_visits(stops, 100, 3, 60)

    infer_sensitive_locations(clusters, stops)

    assert clusters[0].sensitivity_class == "home_candidate"
    assert clusters[0].inferred_place_type == "home_like"
