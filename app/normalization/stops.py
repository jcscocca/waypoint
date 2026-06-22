from __future__ import annotations

from statistics import median

from app.normalization.geo import centroid, haversine_m, is_valid_coordinate, max_distance_from
from app.schemas import LocationObservation, SourceStop, StopVisitData


def source_stop_to_stop_visit(
    source_stop: SourceStop,
    import_id: str,
    user_id_hash: str,
) -> StopVisitData:
    duration_minutes = (source_stop.end_time_utc - source_stop.start_time_utc).total_seconds() / 60
    return StopVisitData(
        import_id=import_id,
        user_id_hash=user_id_hash,
        start_time_utc=source_stop.start_time_utc,
        end_time_utc=source_stop.end_time_utc,
        duration_minutes=duration_minutes,
        local_date=source_stop.start_time_utc.date(),
        local_day_of_week=source_stop.start_time_utc.isoweekday(),
        local_hour_start=source_stop.start_time_utc.hour,
        centroid_latitude=source_stop.latitude,
        centroid_longitude=source_stop.longitude,
        accuracy_median_m=source_stop.accuracy_m,
        source_basis=source_stop.source_record_type,
        point_count_used=1,
        confidence_score=source_stop.confidence_score,
        display_label=source_stop.display_label,
    )


def detect_stops_from_observations(
    observations: list[LocationObservation],
    import_id: str,
    user_id_hash: str,
    minimum_stop_duration_minutes: int,
    stop_radius_m: float,
) -> list[StopVisitData]:
    points = _dedupe_and_filter_points(observations)
    stops: list[StopVisitData] = []
    index = 0
    while index < len(points):
        anchor = points[index]
        cluster = [anchor]
        last_inside_index = index
        for candidate_index in range(index + 1, len(points)):
            candidate = points[candidate_index]
            distance = haversine_m(
                anchor.latitude,
                anchor.longitude,
                candidate.latitude,
                candidate.longitude,
            )
            if distance <= stop_radius_m:
                cluster.append(candidate)
                last_inside_index = candidate_index
                continue
            break
        if len(cluster) >= 2:
            start = cluster[0].observed_at_utc
            end = cluster[-1].observed_at_utc
            duration_minutes = (end - start).total_seconds() / 60
            if duration_minutes >= minimum_stop_duration_minutes:
                coords = [(point.latitude, point.longitude) for point in cluster]
                lat, lon = centroid(coords)
                accuracies = [point.accuracy_m for point in cluster if point.accuracy_m is not None]
                stops.append(
                    StopVisitData(
                        import_id=import_id,
                        user_id_hash=user_id_hash,
                        start_time_utc=start,
                        end_time_utc=end,
                        duration_minutes=duration_minutes,
                        local_date=start.date(),
                        local_day_of_week=start.isoweekday(),
                        local_hour_start=start.hour,
                        centroid_latitude=lat,
                        centroid_longitude=lon,
                        radius_m=max_distance_from(lat, lon, coords),
                        accuracy_median_m=median(accuracies) if accuracies else None,
                        source_basis="point_stream",
                        point_count_used=len(cluster),
                    )
                )
                index = last_inside_index + 1
                continue
        index += 1
    return stops


def _dedupe_and_filter_points(observations: list[LocationObservation]) -> list[LocationObservation]:
    valid = [
        observation
        for observation in observations
        if observation.observed_at_utc is not None
        and is_valid_coordinate(observation.latitude, observation.longitude)
    ]
    valid.sort(key=lambda point: point.observed_at_utc)
    deduped: list[LocationObservation] = []
    seen: set[tuple[str, float, float] | str] = set()
    for point in valid:
        key: tuple[str, float, float] | str
        if point.source_record_hash:
            key = point.source_record_hash
        else:
            key = (
                point.observed_at_utc.isoformat(),
                round(point.latitude, 7),
                round(point.longitude, 7),
            )
        if key in seen:
            continue
        seen.add(key)
        if deduped and _speed_mps(deduped[-1], point) > 120:
            continue
        deduped.append(point)
    return deduped


def _speed_mps(first: LocationObservation, second: LocationObservation) -> float:
    elapsed = (second.observed_at_utc - first.observed_at_utc).total_seconds()
    if elapsed <= 0:
        return 0
    return haversine_m(first.latitude, first.longitude, second.latitude, second.longitude) / elapsed
