from __future__ import annotations

import json
from typing import Any

from app.normalization.geo import is_valid_coordinate
from app.parsers.base import (
    SourceParser,
    confidence_to_score,
    parse_datetime,
    stable_record_hash,
)
from app.schemas import LocationObservation, ParseResult, SourceStop


def google_e7_to_decimal(value: int | str | float | None) -> float | None:
    if value is None or value == "":
        return None
    return round(float(value) / 10_000_000, 7)


class GoogleTimelineParser(SourceParser):
    source_type = "google_timeline"

    def can_parse(self, payload: bytes, filename: str) -> bool:
        if not filename.lower().endswith(".json"):
            return False
        preview = payload[:2000].decode("utf-8", errors="ignore")
        return any(key in preview for key in ("timelineObjects", "locations", "latitudeE7"))

    def parse_bytes(self, payload: bytes, filename: str) -> ParseResult:
        data = json.loads(payload.decode("utf-8"))
        if isinstance(data, dict) and isinstance(data.get("timelineObjects"), list):
            return self._parse_timeline_objects(data["timelineObjects"])
        if isinstance(data, dict) and isinstance(data.get("locations"), list):
            return self._parse_records_locations(data["locations"])
        observations = list(self._extract_recursive_points(data))
        return ParseResult(
            source_type=self.source_type,
            detected_schema="google_on_device_timeline",
            parser_version=self.parser_version,
            observations=observations,
        )

    def _parse_timeline_objects(self, objects: list[dict[str, Any]]) -> ParseResult:
        observations: list[LocationObservation] = []
        source_stops: list[SourceStop] = []
        for item in objects:
            if "placeVisit" in item:
                stop = self._parse_place_visit(item["placeVisit"])
                if stop is not None:
                    source_stops.append(stop)
            if "activitySegment" in item:
                observations.extend(self._parse_activity_segment(item["activitySegment"]))
        return ParseResult(
            source_type=self.source_type,
            detected_schema="google_semantic_location_history",
            parser_version=self.parser_version,
            observations=observations,
            source_stops=source_stops,
        )

    def _parse_place_visit(self, place_visit: dict[str, Any]) -> SourceStop | None:
        location = place_visit.get("location") or {}
        latitude = google_e7_to_decimal(place_visit.get("centerLatE7"))
        longitude = google_e7_to_decimal(place_visit.get("centerLngE7"))
        if latitude is None:
            latitude = google_e7_to_decimal(location.get("latitudeE7") or location.get("latE7"))
        if longitude is None:
            longitude = google_e7_to_decimal(
                location.get("longitudeE7") or location.get("lngE7") or location.get("lonE7")
            )
        duration = place_visit.get("duration") or {}
        start = parse_datetime(duration.get("startTimestamp") or duration.get("startTimestampMs"))
        end = parse_datetime(duration.get("endTimestamp") or duration.get("endTimestampMs"))
        if start is None or end is None or not is_valid_coordinate(latitude, longitude):
            return None
        return SourceStop(
            source_type=self.source_type,
            source_record_type="placeVisit",
            source_record_hash=stable_record_hash(place_visit),
            start_time_utc=start,
            end_time_utc=end,
            latitude=latitude,
            longitude=longitude,
            accuracy_m=_float_or_none(location.get("accuracyMeters")),
            confidence_score=confidence_to_score(place_visit.get("placeConfidence")),
            display_label=location.get("name") or location.get("address"),
        )

    def _parse_activity_segment(self, segment: dict[str, Any]) -> list[LocationObservation]:
        duration = segment.get("duration") or {}
        start_time = parse_datetime(
            duration.get("startTimestamp") or duration.get("startTimestampMs")
        )
        end_time = parse_datetime(duration.get("endTimestamp") or duration.get("endTimestampMs"))
        activity_type = segment.get("activityType")
        confidence_score = confidence_to_score(segment.get("confidence"))
        rows: list[LocationObservation] = []
        for key, observed_at in (("startLocation", start_time), ("endLocation", end_time)):
            location = segment.get(key) or {}
            latitude, longitude = _extract_google_coordinate(location)
            if is_valid_coordinate(latitude, longitude):
                rows.append(
                    LocationObservation(
                        source_type=self.source_type,
                        source_record_type="activitySegment",
                        source_record_hash=stable_record_hash({"segment": segment, "point": key}),
                        observed_at_utc=observed_at,
                        start_time_utc=start_time,
                        end_time_utc=end_time,
                        latitude=latitude,
                        longitude=longitude,
                        activity_type=activity_type,
                        confidence_score=confidence_score,
                    )
                )
        return rows

    def _parse_records_locations(self, locations: list[dict[str, Any]]) -> ParseResult:
        observations = []
        for row in locations:
            latitude, longitude = _extract_google_coordinate(row)
            if not is_valid_coordinate(latitude, longitude):
                continue
            activity_type, confidence = _extract_activity(row)
            observations.append(
                LocationObservation(
                    source_type=self.source_type,
                    source_record_type="location",
                    source_record_hash=stable_record_hash(row),
                    observed_at_utc=parse_datetime(row.get("timestamp") or row.get("timestampMs")),
                    latitude=latitude,
                    longitude=longitude,
                    accuracy_m=_float_or_none(row.get("accuracy") or row.get("accuracyMeters")),
                    activity_type=activity_type,
                    confidence_score=confidence,
                )
            )
        return ParseResult(
            source_type=self.source_type,
            detected_schema="google_records_locations",
            parser_version=self.parser_version,
            observations=observations,
        )

    def _extract_recursive_points(self, value: Any) -> list[LocationObservation]:
        observations: list[LocationObservation] = []
        if isinstance(value, dict):
            latitude, longitude = _extract_google_coordinate(value)
            timestamp = (
                value.get("timestamp")
                or value.get("timestampMs")
                or value.get("time")
                or value.get("startTime")
            )
            observed_at = parse_datetime(timestamp)
            if observed_at is not None and is_valid_coordinate(latitude, longitude):
                observations.append(
                    LocationObservation(
                        source_type=self.source_type,
                        source_record_type="detected_point",
                        source_record_hash=stable_record_hash(value),
                        observed_at_utc=observed_at,
                        latitude=latitude,
                        longitude=longitude,
                        accuracy_m=_float_or_none(
                            value.get("accuracy") or value.get("accuracyMeters")
                        ),
                    )
                )
            for child in value.values():
                observations.extend(self._extract_recursive_points(child))
        elif isinstance(value, list):
            for child in value:
                observations.extend(self._extract_recursive_points(child))
        return observations


def _extract_google_coordinate(record: dict[str, Any]) -> tuple[float | None, float | None]:
    latitude = google_e7_to_decimal(record.get("latitudeE7") or record.get("latE7"))
    longitude = google_e7_to_decimal(
        record.get("longitudeE7") or record.get("lngE7") or record.get("lonE7")
    )
    if latitude is None and "latitude" in record:
        latitude = _float_or_none(record.get("latitude"))
    if longitude is None and "longitude" in record:
        longitude = _float_or_none(record.get("longitude"))
    return latitude, longitude


def _extract_activity(record: dict[str, Any]) -> tuple[str | None, float | None]:
    activities = record.get("activity")
    if not isinstance(activities, list):
        return None, None
    for candidate in activities:
        nested = candidate.get("activity") if isinstance(candidate, dict) else None
        if isinstance(nested, list) and nested:
            best = max(nested, key=lambda item: item.get("confidence", 0))
            return best.get("type"), _float_or_none(best.get("confidence"))
    return None, None


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
