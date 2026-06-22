from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median

from app.normalization.geo import centroid, haversine_m, max_distance_from, snap_to_grid
from app.schemas import PlaceClusterData, StopVisitData

CLUSTER_VERSION = "mvp-1"
CLUSTER_METHOD = "pure_python_radius"


def cluster_stop_visits(
    stops: list[StopVisitData],
    cluster_radius_m: float,
    minimum_cluster_visits: int,
    minimum_cluster_total_dwell_minutes: int,
) -> list[PlaceClusterData]:
    unassigned = set(range(len(stops)))
    clusters: list[PlaceClusterData] = []
    while unassigned:
        start_index = min(unassigned)
        seed = stops[start_index]
        members = {
            index
            for index in unassigned
            if haversine_m(
                seed.centroid_latitude,
                seed.centroid_longitude,
                stops[index].centroid_latitude,
                stops[index].centroid_longitude,
            )
            <= cluster_radius_m
        }
        total_dwell = sum(stops[index].duration_minutes for index in members)
        is_recurring = len(members) >= minimum_cluster_visits
        has_enough_dwell = total_dwell >= minimum_cluster_total_dwell_minutes
        if is_recurring or has_enough_dwell:
            member_stops = [stops[index] for index in sorted(members)]
            cluster = _build_cluster(member_stops, cluster_radius_m)
            for member in member_stops:
                member.place_cluster_id = cluster.id
            clusters.append(cluster)
        unassigned -= members
    return clusters


def infer_sensitive_locations(
    clusters: list[PlaceClusterData],
    stops: list[StopVisitData],
) -> None:
    stops_by_cluster: dict[str, list[StopVisitData]] = defaultdict(list)
    for stop in stops:
        if stop.place_cluster_id:
            stops_by_cluster[stop.place_cluster_id].append(stop)

    for cluster in clusters:
        cluster_stops = stops_by_cluster.get(cluster.id, [])
        overnight_stops = [stop for stop in cluster_stops if _is_overnight(stop)]
        overnight_dwell = sum(stop.duration_minutes for stop in overnight_stops)
        overnight_days = {stop.start_time_utc.date() for stop in overnight_stops}
        weekday_daytime_dwell = sum(
            stop.duration_minutes for stop in cluster_stops if _is_weekday_daytime(stop)
        )
        if overnight_dwell >= 360 and len(overnight_days) >= 2:
            cluster.sensitivity_class = "home_candidate"
            cluster.inferred_place_type = "home_like"
        elif weekday_daytime_dwell >= 360 and cluster.visit_count >= 3:
            cluster.sensitivity_class = "work_candidate"
            cluster.inferred_place_type = "work_like"


def _build_cluster(member_stops: list[StopVisitData], cluster_radius_m: float) -> PlaceClusterData:
    coords = [(stop.centroid_latitude, stop.centroid_longitude) for stop in member_stops]
    lat, lon = centroid(coords)
    durations = [stop.duration_minutes for stop in member_stops]
    days = Counter(str(stop.start_time_utc.isoweekday()) for stop in member_stops)
    hours = Counter(str(stop.start_time_utc.hour) for stop in member_stops)
    labels = [stop.display_label for stop in member_stops if stop.display_label]
    display_lat, display_lon = snap_to_grid(lat, lon)
    return PlaceClusterData(
        user_id_hash=member_stops[0].user_id_hash,
        cluster_version=CLUSTER_VERSION,
        cluster_method=CLUSTER_METHOD,
        centroid_latitude=lat,
        centroid_longitude=lon,
        display_latitude=display_lat,
        display_longitude=display_lon,
        cluster_radius_m=min(
            cluster_radius_m,
            max_distance_from(lat, lon, coords),
        ),
        visit_count=len(member_stops),
        total_dwell_minutes=sum(durations),
        median_dwell_minutes=median(durations),
        first_seen_utc=min(stop.start_time_utc for stop in member_stops),
        last_seen_utc=max(stop.end_time_utc for stop in member_stops),
        dominant_days=",".join(day for day, _ in days.most_common(3)),
        dominant_hours=",".join(hour for hour, _ in hours.most_common(4)),
        display_label=labels[0] if labels else "Recurring area",
        label_source="source" if labels else "generated",
    )


def _is_overnight(stop: StopVisitData) -> bool:
    return (
        stop.start_time_utc.hour >= 20
        or stop.end_time_utc.hour <= 6
        or stop.duration_minutes >= 480
    )


def _is_weekday_daytime(stop: StopVisitData) -> bool:
    return stop.start_time_utc.weekday() < 5 and 9 <= stop.start_time_utc.hour <= 17
